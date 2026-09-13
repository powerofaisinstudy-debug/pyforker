#!/usr/bin/env python3
import os
from setuptools import setup

# Read long description from README.md if present
long_description = ""
if os.path.exists("README.md"):
    with open("README.md", "r", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="pyforker",
    version="2.5.0",
    description="Zero-dependency toolkit for selectively extracting sub-modules and running mirror servers.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sundaram Gupta",
    py_modules=["pyforker"],
    python_requires=">=3.8",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "pyforker = pyforker:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Code Generators",
    ],
)