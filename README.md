<img src="logo2.png" alt="pyforker icon" width="600">

**Production-Grade Python Library Extractor & Server Engine**

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
                       +---------------+---------------+
                       |                               |
         +-------------v-----------+     +-------------v-----------+
         |        Git Engine       |     |      Multi-Threaded      |
         |  (Local Cache/Clones)   |     |    HTTP Daemon Server   |
         +-------------+-----------+     +-------------+-----------+
                       |                               |
                       +---------------+---------------+
                                       |
                         +-------------v-------------+
                         |  AST Rewriter & Analyzer  |
                         |   (Dependency Scanning)   |
                         +-------------+-------------+
                                       |
                         +-------------v-------------+
                         |   Storage & File Locks    |
                         |  (pyforker.json Manifest) |
                         +---------------------------+
```
Installation
From Source (Editable Mode)
Clone your repository and install the binary link locally:

Bash
git clone [https://github.com/powerofaisinstudy-debug/pyforker.git](https://github.com/powerofaisinstudy-debug/pyforker.git)
cd pyforker
pip install -e .
Direct Pip Installation
Bash
pip install .
CLI Reference & Usage
1. Extracting a Sub-Module (take)
Pull a single sub-folder out of a target repository, rewrite its namespace imports, and store it locally:

Bash
pyforker take [https://github.com/torvalds/linux.git](https://github.com/torvalds/linux.git) \
  --sub-path tools/testing/kunit \
  --out ./vendor/kunit \
  --rewrite-from kunit \
  --rewrite-to my_app.vendor.kunit
2. Discovering Third-Party Dependencies (deps)
Scan an extracted module to discover external PyPI packages required to run it:

Bash
pyforker deps ./vendor/kunit
Output Example:

Plaintext
--- Discovered Third-Party Dependencies ---
 - requests
 - typing_extensions
-------------------------------------------
3. Syncing Extracted Code Upstream (sync)
Check local pyforker.json manifests and update extracted modules against upstream Git repositories:

Bash
pyforker sync ./vendor/kunit
4. Running the Remote Mirror Server (serve)
Start a multi-threaded HTTP server on a remote server or local machine:

Bash
pyforker serve --host 0.0.0.0 --port 8080
5. Managing Remote Server Aliases (server-add / server-list)
Save and query remote server endpoints inside ~/.pyforker_config.json:

Bash
# Add server alias
pyforker server-add prod-mirror [http://192.168.1.100:8080](http://192.168.1.100:8080)

# List saved servers
pyforker server-list
6. Executing System Diagnostics (self-test)
Validate local environment, AST transformation hooks, file locks, and configuration storage:

Bash
pyforker self-test
Manifest Specification (pyforker.json)
When pyforker take completes an extraction, it generates or updates a local pyforker.json ledger:

JSON
{
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
