"""
tests/test_generator.py
Unit tests for treeforge.generator
"""

import json
import pytest
from pathlib import Path

from treeforge.parser import parse_tree
from treeforge.generator import generate, _default_content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_TREE = """
myapp/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── src/
│   ├── __init__.py
│   └── main.py
├── notebooks/
│   └── explore.ipynb
└── tests/
    └── test_main.py
"""


def run(tmp_path, tree=SIMPLE_TREE, **kwargs):
    paths = parse_tree(tree)
    return generate(paths, base_dir=str(tmp_path), **kwargs)


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

class TestDryRun:

    def test_dry_run_creates_nothing(self, tmp_path):
        result = run(tmp_path, dry_run=True)
        # No actual files or dirs should exist beyond tmp_path itself
        children = list(tmp_path.iterdir())
        assert children == []

    def test_dry_run_still_reports_counts(self, tmp_path):
        result = run(tmp_path, dry_run=True)
        assert len(result.created_dirs) > 0
        assert len(result.created_files) > 0
        assert result.dry_run is True


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------

class TestDirectories:

    def test_directories_are_created(self, tmp_path):
        run(tmp_path)
        assert (tmp_path / "myapp" / "src").is_dir()
        assert (tmp_path / "myapp" / "tests").is_dir()
        assert (tmp_path / "myapp" / "notebooks").is_dir()

    def test_nested_directories_created(self, tmp_path):
        deep = """
        deep/
        ├── a/
        │   └── b/
        │       └── c/
        │           └── file.py
        """
        paths = parse_tree(deep)
        generate(paths, base_dir=str(tmp_path))
        assert (tmp_path / "deep" / "a" / "b" / "c").is_dir()

    def test_result_lists_dirs(self, tmp_path):
        result = run(tmp_path)
        assert any("myapp" in d for d in result.created_dirs)


# ---------------------------------------------------------------------------
# File creation
# ---------------------------------------------------------------------------

class TestFiles:

    def test_files_are_created(self, tmp_path):
        run(tmp_path)
        assert (tmp_path / "myapp" / "README.md").is_file()
        assert (tmp_path / "myapp" / "src" / "__init__.py").is_file()
        assert (tmp_path / "myapp" / "src" / "main.py").is_file()
        assert (tmp_path / "myapp" / "tests" / "test_main.py").is_file()

    def test_no_errors_on_clean_run(self, tmp_path):
        result = run(tmp_path)
        assert result.errors == []

    def test_result_lists_files(self, tmp_path):
        result = run(tmp_path)
        assert any("README.md" in f for f in result.created_files)


# ---------------------------------------------------------------------------
# Default content
# ---------------------------------------------------------------------------

class TestDefaultContent:

    def test_readme_has_heading(self, tmp_path):
        run(tmp_path)
        content = (tmp_path / "myapp" / "README.md").read_text()
        assert content.startswith("#")

    def test_requirements_txt_has_comment(self, tmp_path):
        run(tmp_path)
        content = (tmp_path / "myapp" / "requirements.txt").read_text()
        assert "#" in content

    def test_env_example_has_hint(self, tmp_path):
        run(tmp_path)
        content = (tmp_path / "myapp" / ".env.example").read_text()
        assert "API_KEY" in content or "NEVER" in content

    def test_gitignore_has_pycache(self, tmp_path):
        run(tmp_path)
        content = (tmp_path / "myapp" / ".gitignore").read_text()
        assert "__pycache__" in content

    def test_py_files_have_docstring(self, tmp_path):
        run(tmp_path)
        content = (tmp_path / "myapp" / "src" / "main.py").read_text()
        assert '"""' in content

    def test_notebook_is_valid_json(self, tmp_path):
        run(tmp_path)
        content = (tmp_path / "myapp" / "notebooks" / "explore.ipynb").read_text()
        nb = json.loads(content)
        assert nb["nbformat"] == 4
        assert "cells" in nb

    def test_default_content_helper_readme(self):
        c = _default_content("README.md")
        assert c is not None and c.startswith("#")

    def test_default_content_helper_py(self):
        c = _default_content("main.py")
        assert c is not None and '"""' in c

    def test_default_content_helper_unknown(self):
        c = _default_content("somefile.xyz")
        assert c is None  # unknown → touch


# ---------------------------------------------------------------------------
# Overwrite behaviour
# ---------------------------------------------------------------------------

class TestOverwrite:

    def test_existing_files_skipped_by_default(self, tmp_path):
        run(tmp_path)
        # Manually change a file
        readme = tmp_path / "myapp" / "README.md"
        readme.write_text("CUSTOM CONTENT")

        run(tmp_path)  # run again without overwrite
        assert readme.read_text() == "CUSTOM CONTENT"

    def test_existing_files_overwritten_when_flag_set(self, tmp_path):
        run(tmp_path)
        readme = tmp_path / "myapp" / "README.md"
        readme.write_text("CUSTOM CONTENT")

        run(tmp_path, overwrite=True)
        assert readme.read_text() != "CUSTOM CONTENT"

    def test_skipped_files_reported(self, tmp_path):
        run(tmp_path)
        result2 = run(tmp_path)  # second run — everything should be skipped
        assert len(result2.skipped) > 0


# ---------------------------------------------------------------------------
# GenerationResult
# ---------------------------------------------------------------------------

class TestGenerationResult:

    def test_summary_string_contains_counts(self, tmp_path):
        result = run(tmp_path)
        s = result.summary()
        assert "created" in s.lower()

    def test_all_created_combines_dirs_and_files(self, tmp_path):
        result = run(tmp_path)
        assert len(result.all_created()) == len(result.created_dirs) + len(result.created_files)
