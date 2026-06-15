"""
treeforge/parser.py
-------------------
Parses a folder-tree string (copy-pasted from a README or terminal)
into a clean, ordered list of ParsedPath objects.

Supported input styles:
  - Unicode box-drawing  (├── └── │)
  - Plain indentation    (spaces or tabs)
  - Mixed / messy input

Usage:
    from treeforge.parser import parse_tree

    paths = parse_tree(raw_text)
    for p in paths:
        print(p.full_path, "DIR" if p.is_dir else "FILE")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ParsedPath:
    """Represents a single file or directory extracted from a tree string."""

    full_path: str          # e.g. "src/ingestion/loader.py"
    is_dir: bool            # True if it ends with /
    depth: int              # nesting level (root = 0)
    comment: str = ""       # inline comment after  #  (stripped from path)

    @property
    def name(self) -> str:
        """Just the final segment (filename or dir name)."""
        return self.full_path.rstrip("/").split("/")[-1]

    @property
    def parent(self) -> str:
        """Parent directory path (empty string for root-level entries)."""
        parts = self.full_path.rstrip("/").split("/")
        return "/".join(parts[:-1])

    def __repr__(self) -> str:
        kind = "DIR " if self.is_dir else "FILE"
        return f"ParsedPath({kind} {self.full_path!r})"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Characters used in tree drawings that carry no path information
_TREE_CHARS = str.maketrans({
    "├": " ",
    "└": " ",
    "│": " ",
    "─": " ",
    "┬": " ",
    "┤": " ",
    "┼": " ",
})

# Matches a trailing comment:  loader.py  # Load + validate CSVs
_COMMENT_RE = re.compile(r"\s+#\s+(.+)$")


def _strip_tree_chars(line: str) -> str:
    """Remove box-drawing characters, leaving only spaces + the name."""
    return line.translate(_TREE_CHARS)


def _split_comment(name: str) -> tuple[str, str]:
    """
    Separate inline comment from the name.
    '  loader.py  # Load CSVs'  →  ('loader.py', 'Load CSVs')
    """
    m = _COMMENT_RE.search(name)
    if m:
        comment = m.group(1).strip()
        name = name[: m.start()].strip()
    else:
        comment = ""
        name = name.strip()
    return name, comment


def _compute_depth(raw_line: str, stripped_line: str) -> int:
    """
    Measure indentation depth.

    Strategy:
      1. Replace tabs with 4 spaces.
      2. Replace all tree-drawing characters with spaces.
      3. Count leading spaces → that is the raw indent width.
      4. Each level in the standard `tree` output uses 4 characters
         ("│   " or "    " or "├── " or "└── "), so divide by 4.
         We floor-divide so that the file/dir name itself (which follows
         the 4-char prefix) doesn't push the depth up by one.
    """
    normalised = raw_line.expandtabs(4)
    as_spaces  = _strip_tree_chars(normalised)
    leading    = len(as_spaces) - len(as_spaces.lstrip(" "))
    return leading // 4


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_tree(raw: str) -> List[ParsedPath]:
    """
    Parse a folder-tree string and return an ordered list of ParsedPath
    objects with resolved full paths.

    Parameters
    ----------
    raw : str
        The raw tree text (multi-line string).

    Returns
    -------
    List[ParsedPath]
        Ordered list mirroring the original tree, with full relative paths.
    """
    results: List[ParsedPath] = []
    # Stack maps depth → current directory name at that depth
    dir_stack: List[str] = []

    for line in raw.splitlines():
        # Skip blank lines and pure tree-character separator lines
        bare = line.strip()
        if not bare or bare in {"│", "|"}:
            continue

        depth = _compute_depth(line, bare)
        cleaned = _strip_tree_chars(line).strip()
        name, comment = _split_comment(cleaned)

        if not name:
            continue

        is_dir = name.endswith("/")
        name_clean = name.rstrip("/")

        # Truncate the stack to the current depth
        dir_stack = dir_stack[:depth]

        # Build full path
        if is_dir:
            full_path = "/".join(dir_stack + [name_clean]) + "/"
            dir_stack.append(name_clean)
        else:
            full_path = "/".join(dir_stack + [name_clean])

        results.append(ParsedPath(
            full_path=full_path,
            is_dir=is_dir,
            depth=depth,
            comment=comment,
        ))

    return results


def split_dirs_and_files(paths: List[ParsedPath]):
    """Convenience splitter → (dirs, files)."""
    dirs  = [p for p in paths if p.is_dir]
    files = [p for p in paths if not p.is_dir]
    return dirs, files


def summary(paths: List[ParsedPath]) -> str:
    """Return a one-line summary string."""
    dirs, files = split_dirs_and_files(paths)
    return f"{len(dirs)} directories, {len(files)} files"
