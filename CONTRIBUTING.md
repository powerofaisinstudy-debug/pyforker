# Contributing to pyforker

Thank you for your interest in contributing to **pyforker**! We welcome bug reports, feature proposals, documentation improvements, and pull requests.

---

##  How Can You Contribute?

* **Report Bugs:** Open an issue on GitHub detailing the problem, your environment, and steps to reproduce.
* **Propose Features:** Submit an issue describing new AST refactoring utilities, CLI features, or performance improvements.
* **Submit Pull Requests:** Pick up an open issue or improve existing code/docs.

---

##  Development Setup

1. **Fork and Clone the Repository**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/pyforker.git](https://github.com/YOUR_USERNAME/pyforker.git)
   cd pyforker
Create a Virtual Environment

Bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
Install Dependencies & Build Tools

Bash
python -m pip install --upgrade build twine pytest
 Testing Guidelines
Before opening a pull request, ensure all tests pass and your changes don't break zero-dependency core behavior:

Bash
# Run test suite
pytest
Zero Dependencies: Keep core logic rely strictly on Python standard library modules (e.g., ast, urllib, subprocess).

Code Formatting: Follow PEP 8 guidelines for clean, readable code.

 Submitting a Pull Request (PR)
Create a descriptive branch for your feature or fix:

Bash
git checkout -b feat/your-feature-name
Commit your changes with clear, concise commit messages:

Bash
git commit -m "feat(ast): add import graph rewriting utility"
Push to your fork and submit a Pull Request to main.

Describe your changes clearly in the PR description and link any relevant open issues.

Issues for Beginners
If you are looking for a place to start, check out issues tagged with:

good first issue — Great for first-time contributors.

help wanted — Key features or optimizations where community help is appreciated.

Thank you for helping make pyforker better!
