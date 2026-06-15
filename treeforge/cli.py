"""
treeforge/cli.py
----------------
Command-line interface for TreeForge.

Commands
--------
treeforge generate <input>          Create structure on disk right now
treeforge script   <input>          Write a standalone Python script
treeforge preview  <input>          Dry-run: show what would be created

<input> can be:
  - A path to a .txt / .md file containing the tree
  - "-" to read from stdin
  - Omitted (GUI prompts you to paste)

Options
-------
  -o, --output DIR     Where to create the structure (default: .)
  -s, --script FILE    Path to save the generated script (default: create_structure.py)
  --overwrite          Overwrite existing files
  --name NAME          Project name (used in script header)

Examples
--------
  treeforge generate tree.txt -o ./projects
  treeforge script   tree.txt -s build.py --name sentineliq
  treeforge preview  tree.txt
  cat tree.txt | treeforge generate -
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from treeforge.parser import parse_tree, summary
from treeforge.generator import generate
from treeforge.script_writer import write_script


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_input(source: str | None) -> str:
    """Read tree text from a file path, stdin ("-"), or interactive prompt."""
    if source is None or source == "":
        print("Paste your folder tree below, then press Ctrl+D (or Ctrl+Z on Windows):\n")
        return sys.stdin.read()
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.exists():
        print(f"❌ File not found: {source}", file=sys.stderr)
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def _detect_project_name(paths) -> str:
    """Guess the project name from the first directory in the tree."""
    for p in paths:
        if p.is_dir:
            return p.name
    return "project"


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_generate(args: argparse.Namespace) -> None:
    raw   = _read_input(args.input)
    paths = parse_tree(raw)

    if not paths:
        print("❌ No paths found. Is the input a valid folder tree?", file=sys.stderr)
        sys.exit(1)

    print(f"\n🌳 TreeForge  ·  {summary(paths)}")
    result = generate(
        paths,
        base_dir=args.output,
        overwrite=args.overwrite,
        dry_run=False,
    )
    print(result.summary())


def cmd_preview(args: argparse.Namespace) -> None:
    raw   = _read_input(args.input)
    paths = parse_tree(raw)

    if not paths:
        print("❌ No paths found.", file=sys.stderr)
        sys.exit(1)

    print(f"\n🌳 TreeForge DRY RUN  ·  {summary(paths)}\n")
    result = generate(
        paths,
        base_dir=args.output,
        overwrite=args.overwrite,
        dry_run=True,
    )

    print("Would create directories:")
    for d in result.created_dirs:
        print(f"  📁 {d}")
    print("\nWould create files:")
    for f in result.created_files:
        print(f"  📄 {f}")
    print(f"\n{result.summary()}")


def cmd_script(args: argparse.Namespace) -> None:
    raw   = _read_input(args.input)
    paths = parse_tree(raw)

    if not paths:
        print("❌ No paths found.", file=sys.stderr)
        sys.exit(1)

    name   = args.name or _detect_project_name(paths)
    out    = args.script or "create_structure.py"
    script = write_script(paths, project_name=name, output_path=out)

    print(f"\n🌳 TreeForge  ·  {summary(paths)}")
    print(f"✅ Script written to: {Path(out).resolve()}")
    print(f"   Run it with: python {out}\n")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="treeforge",
        description="🌳 TreeForge — forge project structures from a folder tree",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Shared options
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("input", nargs="?", help="Tree file path or '-' for stdin")
    shared.add_argument("-o", "--output", default=".", metavar="DIR",
                        help="Destination directory (default: current directory)")
    shared.add_argument("--overwrite", action="store_true",
                        help="Overwrite existing files")

    # generate
    p_gen = sub.add_parser("generate", parents=[shared],
                            help="Create the folder structure on disk")
    p_gen.set_defaults(func=cmd_generate)

    # preview
    p_pre = sub.add_parser("preview", parents=[shared],
                            help="Dry-run: show what would be created")
    p_pre.set_defaults(func=cmd_preview)

    # script
    p_scr = sub.add_parser("script", parents=[shared],
                            help="Generate a standalone Python script")
    p_scr.add_argument("-s", "--script", default="create_structure.py",
                       metavar="FILE", help="Output script path")
    p_scr.add_argument("--name", metavar="NAME",
                       help="Project name for script header")
    p_scr.set_defaults(func=cmd_script)

    return parser


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
