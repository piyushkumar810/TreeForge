"""
treeforge/generator.py
-----------------------
Takes the list of ParsedPath objects from parser.py and creates the
actual folders and files on disk.

Features:
  - Smart default content for common file types
    (.py, README.md, .env.example, requirements.txt, .ipynb, .json, .csv)
  - Dry-run mode (preview without touching the filesystem)
  - Overwrite protection (skip existing files by default)
  - Returns a structured GenerationResult for reporting

Usage:
    from treeforge.parser import parse_tree
    from treeforge.generator import generate

    paths  = parse_tree(raw_text)
    result = generate(paths, base_dir=".")
    print(result.summary())
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from treeforge.parser import ParsedPath


# ---------------------------------------------------------------------------
# Default file content templates
# ---------------------------------------------------------------------------

_NOTEBOOK_TEMPLATE = json.dumps({
    "cells": [],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}, indent=2)


def _default_content(filename: str, comment: str = "") -> Optional[str]:
    """
    Return sensible starter content for well-known file types.
    Returns None for truly empty files (caller will use open(...).close()).
    """
    name = filename.lower()
    hint = f"  # {comment}" if comment else ""

    if name == "readme.md":
        stem = filename  # keep original casing for the heading
        return f"# {Path(stem).stem.replace('-', ' ').replace('_', ' ').title()}\n\nAdd description here.\n"

    if name == "requirements.txt":
        return "# Add your project dependencies here\n# e.g.\n# requests>=2.31.0\n"

    if name in {".env.example", ".env.sample"}:
        return (
            "# Copy this file to .env and fill in real values.\n"
            "# NEVER commit the real .env file.\n\n"
            "# API_KEY=your_api_key_here\n"
        )

    if name == ".gitignore":
        return (
            "__pycache__/\n*.pyc\n*.pyo\n.env\n.venv/\nvenv/\n"
            "dist/\nbuild/\n*.egg-info/\n.DS_Store\n"
        )

    if name.endswith(".ipynb"):
        return _NOTEBOOK_TEMPLATE

    if name.endswith(".json") and name != "package.json":
        return "{}\n"

    if name.endswith(".toml") and "pyproject" in name:
        return "[build-system]\nrequires = [\"setuptools\"]\nbuild-backend = \"setuptools.build_meta\"\n"

    if name == "setup.py":
        return (
            "from setuptools import setup, find_packages\n\n"
            "setup(\n"
            "    name=\"treeforge\",\n"
            "    version=\"0.1.0\",\n"
            "    packages=find_packages(),\n"
            ")\n"
        )

    if name == "dockerfile":
        return "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\n"

    # All .py files get a minimal module docstring
    if name.endswith(".py"):
        module_hint = comment or filename
        return f'"""\n{module_hint}\n"""\n'

    # CSV — just an empty file
    if name.endswith(".csv"):
        return ""

    return None  # signal: create as empty file


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass
class GenerationResult:
    base_dir: str
    created_dirs: List[str]  = field(default_factory=list)
    created_files: List[str] = field(default_factory=list)
    skipped: List[str]       = field(default_factory=list)
    errors: List[str]        = field(default_factory=list)
    dry_run: bool            = False

    def summary(self) -> str:
        mode = "[DRY RUN] " if self.dry_run else ""
        lines = [
            f"{mode}TreeForge generation complete",
            f"  Base : {self.base_dir}",
            f"  Dirs : {len(self.created_dirs)} created",
            f"  Files: {len(self.created_files)} created",
        ]
        if self.skipped:
            lines.append(f"  Skip : {len(self.skipped)} already existed")
        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"    ✗ {e}")
        return "\n".join(lines)

    def all_created(self) -> List[str]:
        return self.created_dirs + self.created_files


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------

def generate(
    paths: List[ParsedPath],
    base_dir: str = ".",
    overwrite: bool = False,
    dry_run: bool = False,
) -> GenerationResult:
    """
    Create the folder/file structure described by *paths* under *base_dir*.

    Parameters
    ----------
    paths     : output of treeforge.parser.parse_tree()
    base_dir  : root directory to create structure inside (default: cwd)
    overwrite : if True, existing files are overwritten; default skips them
    dry_run   : if True, nothing is written — just report what would happen

    Returns
    -------
    GenerationResult with lists of created/skipped/errored paths
    """
    base = Path(base_dir).resolve()
    result = GenerationResult(base_dir=str(base), dry_run=dry_run)

    for parsed in paths:
        target = base / parsed.full_path.rstrip("/")

        try:
            if parsed.is_dir:
                if not dry_run:
                    target.mkdir(parents=True, exist_ok=True)
                result.created_dirs.append(parsed.full_path)

            else:
                # Ensure parent directory exists
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)

                if target.exists() and not overwrite:
                    result.skipped.append(parsed.full_path)
                    continue

                content = _default_content(parsed.name, parsed.comment)

                if not dry_run:
                    if content is None:
                        target.touch()
                    else:
                        target.write_text(content, encoding="utf-8")

                result.created_files.append(parsed.full_path)

        except Exception as exc:
            result.errors.append(f"{parsed.full_path}: {exc}")

    return result
