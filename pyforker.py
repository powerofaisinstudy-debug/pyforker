#!/usr/bin/env python3
"""
pyforker.py - Production-Grade Single-File Python Library Extractor & Server Engine
Zero-dependency toolkit for selectively extracting sub-modules, inspecting ASTs,
and operating remote library mirror servers.
"""

import sys
import os
import io
import re
import json
import time
import shutil
import hashlib
import logging
import argparse
import urllib.request
import urllib.parse
import urllib.error
import subprocess
import concurrent.futures
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import ast

# Setup logging
logging.basicConfig(level=logging.INFO, format="[pyforker] %(levelname)s: %(message)s")

# Global Paths
CONFIG_FILE = os.path.expanduser("~/.pyforker_config.json")
MANIFEST_NAME = "pyforker.json"

# =====================================================================
# PERSISTENT STORAGE ENGINE
# =====================================================================

class StorageEngine:
    @staticmethod
    def load_config():
        if not os.path.exists(CONFIG_FILE):
            return {"servers": {}, "history": []}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"servers": {}, "history": []}

    @staticmethod
    def save_config(data):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def save_manifest(target_dir, manifest_data):
        path = os.path.join(target_dir, MANIFEST_NAME)
        existing = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing.update(manifest_data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

# =====================================================================
# TRANSACTIONAL FILE LOCKING
# =====================================================================

class FileLock:
    def __init__(self, lock_file, timeout=5):
        self.lock_file = lock_file
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        start_time = time.time()
        while True:
            try:
                self.fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                return self
            except OSError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file}")
                time.sleep(0.05)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd is not None:
            os.close(self.fd)
            try:
                os.remove(self.lock_file)
            except OSError:
                pass

# =====================================================================
# REAL GIT & REPOSITORY CONNECTIONS
# =====================================================================

class GitEngine:
    @staticmethod
    def clone_or_update(repo_url, cache_dir):
        repo_hash = hashlib.sha256(repo_url.encode()).hexdigest()[:12]
        target_path = os.path.join(cache_dir, repo_hash)
        
        if os.path.exists(target_path):
            logging.info(f"Updating local cache for {repo_url}...")
            try:
                subprocess.run(["git", "-C", target_path, "pull"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                logging.warning(f"Failed to pull latest git changes: {e}")
        else:
            logging.info(f"Cloning real remote repository {repo_url}...")
            os.makedirs(cache_dir, exist_ok=True)
            subprocess.run(["git", "clone", "--depth", "1", repo_url, target_path], check=True)
            
        return target_path

    @staticmethod
    def get_commit_hash(repo_path):
        try:
            res = subprocess.run(["git", "-C", repo_path, "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
            return res.stdout.strip()
        except Exception:
            return "unknown_commit"

# =====================================================================
# AST REWRITER & DEPENDENCY RESOLVER
# =====================================================================

class ASTDependencyRewriter(ast.NodeTransformer):
    def __init__(self, root_package, target_package):
        self.root_package = root_package
        self.target_package = target_package
        self.detected_imports = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.detected_imports.add(alias.name.split('.')[0])
        return self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.detected_imports.add(node.module.split('.')[0])
            if node.module == self.root_package or node.module.startswith(self.root_package + "."):
                new_module = node.module.replace(self.root_package, self.target_package, 1)
                return ast.copy_location(ast.ImportFrom(module=new_module, names=node.names, level=node.level), node)
        return self.generic_visit(node)

class ASTAnalyzer:
    @staticmethod
    def process_file(source_file, target_file, old_pkg="", new_pkg=""):
        with open(source_file, "r", encoding="utf-8") as f:
            code = f.read()
            
        try:
            tree = ast.parse(code, filename=source_file)
            rewriter = ASTDependencyRewriter(old_pkg, new_pkg) if old_pkg and new_pkg else ASTDependencyRewriter("", "")
            new_tree = rewriter.visit(tree)
            ast.fix_missing_locations(new_tree)
            
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(ast.unparse(new_tree))
                
            return rewriter.detected_imports
        except Exception as e:
            logging.warning(f"AST unparse skipped for {source_file}, falling back to plain copy. Reason: {e}")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            shutil.copy2(source_file, target_file)
            return set()

# =====================================================================
# REAL MULTI-THREADED HTTP SERVER ENGINE
# =====================================================================

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handles requests in separate threads for scalable remote service."""
    daemon_threads = True

class PyForkerHTTPHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok", "time": time.time(), "engine": "PyForker v2.0"})
        elif parsed.path == "/manifest":
            cfg = StorageEngine.load_config()
            self._send_json(200, {"manifest": cfg.get("history", [])})
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        if parsed.path == "/take":
            repo_url = payload.get("repo_url")
            sub_path = payload.get("sub_path")
            if not repo_url or not sub_path:
                self._send_json(400, {"error": "Missing repo_url or sub_path"})
                return

            cache_dir = os.path.expanduser("~/.pyforker_cache")
            try:
                repo_path = GitEngine.clone_or_update(repo_url, cache_dir)
                source = os.path.join(repo_path, sub_path)
                if not os.path.exists(source):
                    self._send_json(404, {"error": f"Path {sub_path} not found in repo"})
                    return
                
                commit_sha = GitEngine.get_commit_hash(repo_path)
                self._send_json(200, {
                    "status": "success",
                    "commit": commit_sha,
                    "sub_path": sub_path,
                    "message": "Repository extraction target verified on remote server"
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
        else:
            self._send_json(404, {"error": "Endpoint not found"})

# =====================================================================
# CLI COMMAND PROCESSORS (SOLVING DEVELOPER PAIN POINTS)
# =====================================================================

def cmd_take(args):
    """Pulls directly from a local path or git URL and extracts a subfolder cleanly."""
    target_out = os.path.abspath(args.out)
    cache_dir = os.path.expanduser("~/.pyforker_cache")
    
    if args.repo.startswith("http://") or args.repo.startswith("https://") or args.repo.startswith("git@"):
        repo_path = GitEngine.clone_or_update(args.repo, cache_dir)
        commit_hash = GitEngine.get_commit_hash(repo_path)
        source_base = repo_path
    else:
        source_base = os.path.abspath(args.repo)
        commit_hash = "local_filesystem"

    source_dir = os.path.join(source_base, args.sub_path) if args.sub_path else source_base

    if not os.path.exists(source_dir):
        logging.error(f"Source sub-path does not exist: {source_dir}")
        sys.exit(1)

    logging.info(f"Extracting sub-module '{args.sub_path or '.'}' into '{target_out}'...")

    detected_deps = set()
    file_count = 0

    with FileLock(os.path.join(os.getcwd(), ".pyforker.lock")):
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".py"):
                    src_file = os.path.join(root, file)
                    rel_file = os.path.relpath(src_file, source_dir)
                    dst_file = os.path.join(target_out, rel_file)
                    
                    deps = ASTAnalyzer.process_file(src_file, dst_file, args.rewrite_from, args.rewrite_to)
                    detected_deps.update(deps)
                    file_count += 1
                else:
                    src_file = os.path.join(root, file)
                    rel_file = os.path.relpath(src_file, source_dir)
                    dst_file = os.path.join(target_out, rel_file)
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)

    manifest_entry = {
        args.out: {
            "source_repo": args.repo,
            "sub_path": args.sub_path or "",
            "commit": commit_hash,
            "files_extracted": file_count,
            "extracted_at": time.time(),
            "detected_imports": list(detected_deps)
        }
    }
    StorageEngine.save_manifest(target_out, manifest_entry)
    logging.info(f"Successfully extracted {file_count} files to '{target_out}'. Ledger saved to {MANIFEST_NAME}.")

def cmd_deps(args):
    """Pain Point Solved: Scans an extracted module to discover external third-party dependencies."""
    target_dir = os.path.abspath(args.path)
    if not os.path.exists(target_dir):
        logging.error(f"Path does not exist: {target_dir}")
        sys.exit(1)

    all_imports = set()
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                all_imports.add(alias.name.split(".")[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                all_imports.add(node.module.split(".")[0])
                except Exception:
                    pass

    std_lib = sys.stdlib_module_names if hasattr(sys, "stdlib_module_names") else set()
    third_party = sorted([imp for imp in all_imports if imp not in std_lib and not imp.startswith("_")])

    print("\n--- Discovered Third-Party Dependencies ---")
    if third_party:
        for dep in third_party:
            print(f" - {dep}")
    else:
        print(" No external third-party packages detected.")
    print("-------------------------------------------\n")

def cmd_sync(args):
    """Pain Point Solved: Syncs local extracted sub-modules against updated upstream repos."""
    manifest_path = os.path.join(args.path, MANIFEST_NAME)
    if not os.path.exists(manifest_path):
        logging.error(f"No {MANIFEST_NAME} found in {args.path}. Cannot sync.")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for target, meta in data.items():
        repo = meta.get("source_repo")
        sub_path = meta.get("sub_path")
        if repo and repo.startswith("http"):
            logging.info(f"Syncing target '{target}' with {repo}...")
            cache_dir = os.path.expanduser("~/.pyforker_cache")
            repo_path = GitEngine.clone_or_update(repo, cache_dir)
            
            src_dir = os.path.join(repo_path, sub_path) if sub_path else repo_path
            dst_dir = os.path.abspath(args.path)

            for root, _, files in os.walk(src_dir):
                for file in files:
                    if file.endswith(".py"):
                        src_f = os.path.join(root, file)
                        rel_f = os.path.relpath(src_f, src_dir)
                        dst_f = os.path.join(dst_dir, rel_f)
                        ASTAnalyzer.process_file(src_f, dst_f)
            
            meta["commit"] = GitEngine.get_commit_hash(repo_path)
            meta["synced_at"] = time.time()

    StorageEngine.save_manifest(args.path, data)
    logging.info("Sync complete!")

def cmd_server_add(args):
    """Pain Point Solved: Save and manage multiple remote PyForker instances for team networks."""
    cfg = StorageEngine.load_config()
    cfg["servers"][args.name] = {"url": args.url, "added_at": time.time()}
    StorageEngine.save_config(cfg)
    logging.info(f"Saved remote server alias '{args.name}' -> {args.url}")

def cmd_server_list(args):
    """Lists saved server configurations."""
    cfg = StorageEngine.load_config()
    servers = cfg.get("servers", {})
    print("\n--- Configured Remote PyForker Servers ---")
    if not servers:
        print(" No remote servers configured. Add one with 'server-add'.")
    else:
        for name, info in servers.items():
            print(f" - [{name}] {info['url']}")
    print("------------------------------------------\n")

def cmd_serve(args):
    """Starts a real multi-threaded PyForker HTTP server daemon."""
    server_address = (args.host, args.port)
    httpd = ThreadedHTTPServer(server_address, PyForkerHTTPHandler)
    logging.info(f"Starting PyForker Server on http://{args.host}:{args.port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down server...")
        httpd.server_close()

def cmd_self_test(args):
    """Executes full diagnostic test suite over internal AST and storage subsystems."""
    print("Running PyForker Diagnostic Suite...")
    
    # 1. Test Storage
    cfg = StorageEngine.load_config()
    assert isinstance(cfg, dict), "Storage engine failed to return dict"
    print(" [PASS] Storage Engine")

    # 2. Test File Locking
    lock_file = ".test.lock"
    with FileLock(lock_file):
        assert os.path.exists(lock_file), "Lock file creation failed"
    assert not os.path.exists(lock_file), "Lock file cleanup failed"
    print(" [PASS] Transactional File Locking")

    # 3. Test AST Engine
    test_code = "from original import module\nimport os"
    tree = ast.parse(test_code)
    rewriter = ASTDependencyRewriter("original", "refactored")
    new_tree = rewriter.visit(tree)
    output = ast.unparse(new_tree)
    assert "from refactored import module" in output, "AST rewrite failed"
    print(" [PASS] AST Dependency Rewriting Engine")

    print("\nAll diagnostics passed successfully!")

# =====================================================================
# MAIN ENTRY POINT
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="pyforker - Production-Grade Single-File Python Library Extractor & Server Engine"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command: take
    p_take = subparsers.add_parser("take", help="Extract sub-module from local path or remote Git URL")
    p_take.add_argument("repo", help="Git repository URL or local directory path")
    p_take.add_argument("--sub-path", help="Relative sub-path inside repo to extract", default="")
    p_take.add_argument("--out", help="Target output directory", required=True)
    p_take.add_argument("--rewrite-from", help="Original package name to rewrite in imports", default="")
    p_take.add_argument("--rewrite-to", help="Target package name to rewrite in imports", default="")
    p_take.set_defaults(func=cmd_take)

    # Command: deps
    p_deps = subparsers.add_parser("deps", help="Scan extracted module to list third-party dependencies")
    p_deps.add_argument("path", help="Path to extracted python code directory")
    p_deps.set_defaults(func=cmd_deps)

    # Command: sync
    p_sync = subparsers.add_parser("sync", help="Sync extracted module with updated upstream git repository")
    p_sync.add_argument("path", help="Path to directory containing pyforker.json manifest")
    p_sync.set_defaults(func=cmd_sync)

    # Command: server-add
    p_sadd = subparsers.add_parser("server-add", help="Save a remote PyForker server alias")
    p_sadd.add_argument("name", help="Server alias name (e.g., prod-server)")
    p_sadd.add_argument("url", help="Server URL (e.g., http://192.168.1.50:8080)")
    p_sadd.set_defaults(func=cmd_server_add)

    # Command: server-list
    p_slist = subparsers.add_parser("server-list", help="List saved PyForker server aliases")
    p_slist.set_defaults(func=cmd_server_list)

    # Command: serve
    p_serve = subparsers.add_parser("serve", help="Launch multi-threaded PyForker HTTP server daemon")
    p_serve.add_argument("--host", default="0.0.0.0", help="Binding host address")
    p_serve.add_argument("--port", type=int, default=8080, help="Binding port")
    p_serve.set_defaults(func=cmd_serve)

    # Command: self-test
    p_test = subparsers.add_parser("self-test", help="Run local diagnostic test suite")
    p_test.set_defaults(func=cmd_self_test)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()