# 🌳 TreeForge

> Forge your project structure from any folder tree — instantly.

Copy-paste a folder tree from a README, GitHub, or your terminal and TreeForge turns it into:
- 📁 **Real folders & files** on disk (with smart starter content)
- 📜 **A standalone Python script** you can share or run anywhere
- 📦 **A ZIP archive** ready to extract

---

## Installation

```bash
git clone https://github.com/yourname/treeforge
cd treeforge
pip install -r requirements.txt
pip install -e .
```

---

## Usage

### Web UI (recommended)
```bash
streamlit run ui/app.py
```

### CLI

```bash
# Preview what would be created (dry run)
treeforge preview tree.txt

# Create the structure on disk
treeforge generate tree.txt -o ./projects

# Generate a standalone Python script
treeforge script tree.txt --name myproject -s create_structure.py

# Read from stdin
cat tree.txt | treeforge generate -
```

### Python API

```python
from treeforge import parse_tree, generate, write_script

raw = """
myapp/
├── README.md
├── src/
│   └── main.py
└── tests/
    └── test_main.py
"""

paths  = parse_tree(raw)
result = generate(paths, base_dir="./output")
print(result.summary())

# Or generate a standalone script
script = write_script(paths, project_name="myapp")
```

---

## Project Structure

```
treeforge/
├── treeforge/
│   ├── parser.py        # Parse tree text → list of paths
│   ├── generator.py     # Create folders/files on disk
│   ├── script_writer.py # Generate standalone Python script
│   └── cli.py           # CLI entry point
├── ui/
│   └── app.py           # Streamlit web UI
└── tests/
    ├── test_parser.py
    └── test_generator.py
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Supported Tree Formats

- Unicode box-drawing (`├──` `└──` `│`)
- Plain indentation (spaces or tabs)
- Mixed / messy input
- Inline `# comments` — preserved as file docstrings

---

Built with Python 🐍 and Streamlit ⚡
