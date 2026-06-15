"""
TreeForge 🌳
Forge your project structure from a folder tree.
"""

__version__ = "0.1.0"
__author__  = "TreeForge"

from treeforge.parser       import parse_tree, ParsedPath, summary
from treeforge.generator    import generate, GenerationResult
from treeforge.script_writer import write_script

__all__ = [
    "parse_tree",
    "ParsedPath",
    "summary",
    "generate",
    "GenerationResult",
    "write_script",
]
