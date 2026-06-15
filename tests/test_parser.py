"""
tests/test_parser.py
Unit tests for treeforge.parser
"""

import pytest
from treeforge.parser import parse_tree, split_dirs_and_files, summary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_TREE = """
myapp/
├── README.md
├── src/
│   ├── __init__.py
│   └── main.py
└── tests/
    └── test_main.py
"""

FULL_TREE = """
sentineliq/
│
├── README.md
├── requirements.txt
├── .env.example
│
├── data/
│   ├── identity_users.csv
│   └── identity_events.csv
│
├── src/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── loader.py
│   └── detection/
│       ├── __init__.py
│       └── rules.py
│
└── tests/
    └── test_rules.py
"""

PLAIN_INDENT_TREE = """
project/
  src/
    main.py
    utils.py
  tests/
    test_main.py
  README.md
"""

TREE_WITH_COMMENTS = """
myapp/
├── loader.py    # Load + validate CSVs
├── schema.py    # Pydantic models
└── config.py    # App configuration
"""


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------

class TestBasicParsing:

    def test_simple_tree_count(self):
        paths = parse_tree(SIMPLE_TREE)
        dirs, files = split_dirs_and_files(paths)
        assert len(dirs) == 3   # myapp, src, tests
        assert len(files) == 4  # README, __init__, main, test_main

    def test_full_paths_are_correct(self):
        paths = parse_tree(SIMPLE_TREE)
        full_paths = [p.full_path for p in paths]
        assert "myapp/" in full_paths
        assert "myapp/src/" in full_paths
        assert "myapp/src/__init__.py" in full_paths
        assert "myapp/src/main.py" in full_paths
        assert "myapp/tests/test_main.py" in full_paths

    def test_dirs_end_with_slash(self):
        paths = parse_tree(SIMPLE_TREE)
        for p in paths:
            if p.is_dir:
                assert p.full_path.endswith("/"), f"{p.full_path} should end with /"

    def test_files_do_not_end_with_slash(self):
        paths = parse_tree(SIMPLE_TREE)
        for p in paths:
            if not p.is_dir:
                assert not p.full_path.endswith("/"), f"{p.full_path} should not end with /"

    def test_is_dir_flag(self):
        paths = parse_tree(SIMPLE_TREE)
        path_map = {p.full_path: p for p in paths}
        assert path_map["myapp/"].is_dir is True
        assert path_map["myapp/src/"].is_dir is True
        assert path_map["myapp/README.md"].is_dir is False
        assert path_map["myapp/src/main.py"].is_dir is False


# ---------------------------------------------------------------------------
# Deep nesting
# ---------------------------------------------------------------------------

class TestDeepNesting:

    def test_nested_paths_resolve_correctly(self):
        paths = parse_tree(FULL_TREE)
        full_paths = [p.full_path for p in paths]
        assert "sentineliq/src/ingestion/" in full_paths
        assert "sentineliq/src/ingestion/__init__.py" in full_paths
        assert "sentineliq/src/ingestion/loader.py" in full_paths
        assert "sentineliq/src/detection/rules.py" in full_paths

    def test_sibling_dirs_dont_bleed(self):
        """Files under detection/ should NOT appear under ingestion/."""
        paths = parse_tree(FULL_TREE)
        path_map = {p.full_path for p in paths}
        assert "sentineliq/src/ingestion/rules.py" not in path_map
        assert "sentineliq/src/detection/loader.py" not in path_map


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

class TestComments:

    def test_comments_are_extracted(self):
        paths = parse_tree(TREE_WITH_COMMENTS)
        path_map = {p.name: p for p in paths}
        assert path_map["loader.py"].comment == "Load + validate CSVs"
        assert path_map["schema.py"].comment == "Pydantic models"
        assert path_map["config.py"].comment == "App configuration"

    def test_comments_not_in_filename(self):
        paths = parse_tree(TREE_WITH_COMMENTS)
        for p in paths:
            assert "#" not in p.name


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_input(self):
        assert parse_tree("") == []

    def test_whitespace_only(self):
        assert parse_tree("   \n\n\t\n  ") == []

    def test_single_file(self):
        paths = parse_tree("README.md\n")
        assert len(paths) == 1
        assert paths[0].name == "README.md"
        assert paths[0].is_dir is False

    def test_plain_indentation(self):
        paths = parse_tree(PLAIN_INDENT_TREE)
        path_map = {p.full_path for p in paths}
        assert "project/src/main.py" in path_map
        assert "project/tests/test_main.py" in path_map
        assert "project/README.md" in path_map

    def test_blank_separator_lines_ignored(self):
        """Lines that are only │ should be skipped."""
        paths_with = parse_tree(FULL_TREE)
        clean = FULL_TREE.replace("│\n", "\n")
        paths_without = parse_tree(clean)
        assert len(paths_with) == len(paths_without)

    def test_depth_is_correct(self):
        paths = parse_tree(SIMPLE_TREE)
        path_map = {p.full_path: p for p in paths}
        assert path_map["myapp/"].depth == 0
        assert path_map["myapp/src/"].depth == 1
        assert path_map["myapp/src/main.py"].depth == 2

    def test_name_property(self):
        paths = parse_tree(SIMPLE_TREE)
        path_map = {p.full_path: p for p in paths}
        assert path_map["myapp/src/"].name == "src"
        assert path_map["myapp/src/main.py"].name == "main.py"

    def test_parent_property(self):
        paths = parse_tree(SIMPLE_TREE)
        path_map = {p.full_path: p for p in paths}
        assert path_map["myapp/src/main.py"].parent == "myapp/src"
        assert path_map["myapp/src/"].parent == "myapp"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class TestSummary:

    def test_summary_format(self):
        paths = parse_tree(SIMPLE_TREE)
        s = summary(paths)
        assert "directories" in s
        assert "files" in s
        assert "3" in s   # 3 dirs
        assert "4" in s   # 4 files
