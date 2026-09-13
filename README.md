

<p align="center">
  <img src="logo2.PNG" alt="pyforker logo" width="600"/>
</p>


**Production-Grade Single-File Python Library Extractor & Server Engine**


[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20external-success.svg)](#)

`pyforker` is a lightweight, zero-dependency engine designed to selectively extract sub-modules from massive Python codebases or remote Git repositories. It automatically rewrites AST import graphs, resolves vendor dependencies, tracks upstream sync ledgers, and runs multi-threaded HTTP server daemons to mirror code snippets across networks.



---

## Key Features

* **Zero External Dependencies:** Built entirely on standard Python modules (`ast`, `urllib`, `subprocess`, `concurrent.futures`, `http.server`).
* **Sub-Module Slicing (`take`):** Extract specific folders from remote Git repositories without pulling unnecessary weight into your project.
* **AST Import Rewriting:** Dynamically rewrites import statements during extraction so isolated sub-modules map directly into your local package tree.
* **Dependency Discovery (`deps`):** AST-level scanning detects third-party PyPI requirements versus Python standard library imports.
* **Upstream Synchronization (`sync`):** Keeps track of commit SHAs in local `pyforker.json` manifests to pull updates from upstream sources seamlessly.
* **Multi-Threaded Server Engine (`serve`):** Built-in daemon allows remote extraction and repository mirroring over network endpoints.
* **Transactional File Safety:** Uses OS-level file locking (`O_CREAT | O_EXCL`) to ensure multi-threaded and concurrent CLI ops avoid race conditions.

---

## Architecture Overview

```text
               +-------------------------------------------------+
               |                    CLI Entry                    |
               |         (pyforker take / deps / sync / serve)   |
               +-----------------------+-------------------------+
                                       |
                     +-----------------+-----------------+
                     |                                   |
         +-----------v-----------+           +-----------v-----------+
         |     Git Engine        |           |   Multi-Threaded      |
         | (Local Cache/Clones)  |           |   HTTP Daemon Server  |
         +-----------+-----------+           +-----------+-----------+
                     |                                   |
                     +-----------------+-----------------+
                                       |
                         +-------------v-------------+
                         |  AST Rewriter & Analyzer  |
                         |   (Dependency Scanning)   |
                         +-------------+-------------+
                                       |
                         +-------------v-------------+
                         |  Storage & File Locks     |
                         |  (pyforker.json Manifest) |
                         +---------------------------+
InstallationFrom Source (Editable Mode)Clone your repository and install the binary link locally:Bashgit clone [https://github.com/your-username/pyforker.git](https://github.com/your-username/pyforker.git)
cd pyforker
pip install -e .
Direct Pip InstallationBashpip install .
CLI Reference & Usage1. Extracting a Sub-Module (take)Pull a single sub-folder out of a target repository, rewrite its namespace imports, and store it locally:Bashpyforker take [https://github.com/torvalds/linux.git](https://github.com/torvalds/linux.git) \
  --sub-path tools/testing/kunit \
  --out ./vendor/kunit \
  --rewrite-from kunit \
  --rewrite-to my_app.vendor.kunit
2. Discovering Third-Party Dependencies (deps)Scan an extracted module to discover external PyPI packages required to run it:Bashpyforker deps ./vendor/kunit
Output Example:Plaintext--- Discovered Third-Party Dependencies ---
 - requests
 - typing_extensions
-------------------------------------------
3. Syncing Extracted Code Upstream (sync)Check local pyforker.json manifests and update extracted modules against upstream Git repositories:Bashpyforker sync ./vendor/kunit
4. Running the Remote Mirror Server (serve)Start a multi-threaded HTTP server on a remote server or local machine:Bashpyforker serve --host 0.0.0.0 --port 8080
5. Managing Remote Server Aliases (server-add / server-list)Save and query remote server endpoints inside ~/.pyforker_config.json:Bash# Add server alias
pyforker server-add prod-mirror [http://192.168.1.100:8080](http://192.168.1.100:8080)

# List saved servers
pyforker server-list
6. Executing System Diagnostics (self-test)Validate local environment, AST transformation hooks, file locks, and configuration storage:Bashpyforker self-test
Manifest Specification (pyforker.json)When pyforker take completes an extraction, it generates or updates a local pyforker.json ledger:JSON{
  "./vendor/kunit": {
    "source_repo": "[https://github.com/torvalds/linux.git](https://github.com/torvalds/linux.git)",
    "sub_path": "tools/testing/kunit",
    "commit": "a1b2c3d4e5f67890",
    "files_extracted": 14,
    "extracted_at": 1773724800.0,
    "detected_imports": [
      "sys",
      "os",
      "requests"
    ]
  }
}
Programmatic Python APIYou can import pyforker as an internal module inside your Python pipelines:Pythonfrom pyforker import ASTAnalyzer, GitEngine, FileLock

# Clone or update a repository into local cache
repo_path = GitEngine.clone_or_update(
    "[https://github.com/example/repo.git](https://github.com/example/repo.git)", 
    "~/.pyforker_cache"
)

# Rewrite AST imports programmatically
detected_deps = ASTAnalyzer.process_file(
    source_file="path/to/source.py",
    target_file="path/to/output.py",
    old_pkg="original_pkg",
    new_pkg="my_app.vendor"
)

print(f"Discovered dependencies: {detected_deps}")
HTTP REST API SpecificationWhen running pyforker serve, the server exposes the following endpoints:EndpointMethodParameters / BodyDescription/healthGETNoneReturns engine status and uptime./manifestGETNoneReturns history ledger stored in host configuration./takePOST{"repo_url": "...", "sub_path": "..."}Triggers background clone and path verification.Running Unit TestsRun the integrated self-test suite directly:Bashpython3 pyforker.py self-test
