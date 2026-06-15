"""
ui/app.py
---------
TreeForge Streamlit web interface.

Run with:
    streamlit run ui/app.py
"""

import io
import os
import sys
import zipfile
import tempfile
from pathlib import Path

import streamlit as st

# Allow importing treeforge from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from treeforge.parser import parse_tree, summary, split_dirs_and_files
from treeforge.generator import generate
from treeforge.script_writer import write_script


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="TreeForge",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* Main header */
    .tf-header { text-align: center; padding: 1.5rem 0 0.5rem; }
    .tf-title  { font-size: 2.8rem; font-weight: 700; letter-spacing: -1px; }
    .tf-sub    { font-size: 1.05rem; color: #666; margin-top: -0.4rem; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 0.75rem 1rem;
    }

    /* Tree preview */
    .tree-preview {
        background: #0d1117;
        color: #c9d1d9;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.82rem;
        line-height: 1.6;
        max-height: 420px;
        overflow-y: auto;
    }
    .tree-dir  { color: #79c0ff; font-weight: 600; }
    .tree-file { color: #c9d1d9; }
    .tree-comment { color: #8b949e; font-style: italic; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.25rem;
        font-weight: 500;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton > button:hover { transform: translateY(-1px); }

    /* Success/info banners */
    .stAlert { border-radius: 10px; }

    /* Footer */
    .tf-footer {
        text-align: center;
        color: #aaa;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="tf-header">
    <div class="tf-title">🌳 TreeForge</div>
    <div class="tf-sub">Forge your project structure from any folder tree</div>
</div>
""", unsafe_allow_html=True)

st.divider()


# ---------------------------------------------------------------------------
# Sidebar — options
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Options")

    project_name = st.text_input(
        "Project name",
        value="",
        placeholder="Auto-detect from tree",
        help="Used as the header in the generated script",
    )

    output_dir = st.text_input(
        "Output directory (generate mode)",
        value=".",
        help="Where to create the structure on disk",
    )

    overwrite = st.toggle("Overwrite existing files", value=False)

    st.divider()
    st.markdown("""
    **How to use**
    1. Paste a folder tree in the text area
    2. Click **Parse** to preview
    3. Choose **Generate** or **Download Script**
    """)

    st.divider()
    st.markdown("""
    **Supported tree styles**
    - `├──` `└──` `│` (Unicode)
    - Plain indentation (spaces / tabs)
    - Mixed / messy input
    - Inline `# comments` are preserved
    """)


# ---------------------------------------------------------------------------
# Example trees
# ---------------------------------------------------------------------------

EXAMPLES = {
    "SentinelIQ (full)": """sentineliq/
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
│   │   ├── loader.py
│   │   └── schema.py
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── rules.py
│   │   └── ml_scorer.py
│   └── output/
│       ├── __init__.py
│       └── report_builder.py
│
├── api/
│   ├── __init__.py
│   └── main.py
│
├── dashboard/
│   └── app.py
│
└── tests/
    ├── test_rules.py
    └── test_ingestion.py""",

    "FastAPI microservice": """myservice/
├── README.md
├── requirements.txt
├── .env.example
├── Dockerfile
├── .gitignore
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── users.py
│   └── services/
│       ├── __init__.py
│       └── user_service.py
│
└── tests/
    ├── conftest.py
    └── test_users.py""",

    "React + Vite app": """my-react-app/
├── README.md
├── package.json
├── vite.config.js
├── index.html
│
├── public/
│   └── favicon.ico
│
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── components/
    │   ├── Navbar.jsx
    │   └── Footer.jsx
    ├── pages/
    │   ├── Home.jsx
    │   └── About.jsx
    └── styles/
        └── global.css""",
}


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("### 📋 Paste your folder tree")

    # Example loader
    ex_col1, ex_col2, ex_col3 = st.columns(3)
    example_choice = None
    if ex_col1.button("📦 SentinelIQ", use_container_width=True):
        example_choice = "SentinelIQ (full)"
    if ex_col2.button("⚡ FastAPI", use_container_width=True):
        example_choice = "FastAPI microservice"
    if ex_col3.button("⚛️ React+Vite", use_container_width=True):
        example_choice = "React + Vite app"

    # Initialise session state
    if "tree_input" not in st.session_state:
        st.session_state.tree_input = ""
    if example_choice:
        st.session_state.tree_input = EXAMPLES[example_choice]

    tree_input = st.text_area(
        label="Tree input",
        value=st.session_state.tree_input,
        height=340,
        placeholder="Paste any folder tree here…\n\nExample:\nmyproject/\n├── README.md\n├── src/\n│   └── main.py\n└── tests/\n    └── test_main.py",
        label_visibility="collapsed",
    )
    st.session_state.tree_input = tree_input

    parse_btn = st.button("🔍 Parse tree", type="primary", use_container_width=True)


# ---------------------------------------------------------------------------
# Parse & display results
# ---------------------------------------------------------------------------

parsed_paths = []

if tree_input.strip():
    parsed_paths = parse_tree(tree_input)

with col_right:
    st.markdown("### 🌲 Structure preview")

    if not parsed_paths:
        st.info("Paste a folder tree on the left and click **Parse tree** to preview it here.")
    else:
        dirs, files = split_dirs_and_files(parsed_paths)

        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Directories", len(dirs))
        m2.metric("Files", len(files))
        m3.metric("Total", len(parsed_paths))

        # Rendered tree
        tree_html_lines = []
        for p in parsed_paths:
            indent = "&nbsp;" * (p.depth * 4)
            if p.is_dir:
                label = f'<span class="tree-dir">📁 {p.name}/</span>'
            else:
                label = f'<span class="tree-file">📄 {p.name}</span>'
            comment_html = (
                f' <span class="tree-comment">← {p.comment}</span>'
                if p.comment else ""
            )
            tree_html_lines.append(f"{indent}{label}{comment_html}")

        tree_html = "<br>".join(tree_html_lines)
        st.markdown(
            f'<div class="tree-preview">{tree_html}</div>',
            unsafe_allow_html=True,
        )

st.divider()


# ---------------------------------------------------------------------------
# Action tabs
# ---------------------------------------------------------------------------

if parsed_paths:
    tab_script, tab_generate, tab_zip = st.tabs([
        "📜 Download Script",
        "⚡ Generate on Disk",
        "📦 Download ZIP",
    ])

    # Detect project name
    auto_name = project_name.strip()
    if not auto_name:
        for p in parsed_paths:
            if p.is_dir:
                auto_name = p.name
                break
        auto_name = auto_name or "project"

    # ── Tab 1: Script ──────────────────────────────────────────────────────
    with tab_script:
        st.markdown("Generate a **standalone Python script** you can run anywhere — no TreeForge needed.")

        script_str = write_script(parsed_paths, project_name=auto_name)

        st.code(script_str, language="python")

        st.download_button(
            label="⬇️ Download create_structure.py",
            data=script_str.encode("utf-8"),
            file_name="create_structure.py",
            mime="text/x-python",
            use_container_width=True,
            type="primary",
        )

        st.info(
            f"Run with: `python create_structure.py`  \n"
            f"Or to a specific path: `python create_structure.py /my/path`"
        )

    # ── Tab 2: Generate on disk ────────────────────────────────────────────
    with tab_generate:
        st.markdown(f"Create the structure **directly on disk** inside `{output_dir}`.")

        if st.button("⚡ Create structure now", type="primary", use_container_width=True):
            with st.spinner("Creating files and folders…"):
                result = generate(
                    parsed_paths,
                    base_dir=output_dir,
                    overwrite=overwrite,
                )

            if result.errors:
                st.error(f"Completed with {len(result.errors)} error(s):")
                for e in result.errors:
                    st.code(e)
            else:
                st.success(f"✅ Done! Created {len(result.created_files)} files in {len(result.created_dirs)} directories.")

            with st.expander("View details"):
                if result.created_dirs:
                    st.markdown("**Directories created:**")
                    for d in result.created_dirs:
                        st.code(d)
                if result.created_files:
                    st.markdown("**Files created:**")
                    for f in result.created_files:
                        st.code(f)
                if result.skipped:
                    st.markdown("**Skipped (already exist):**")
                    for s in result.skipped:
                        st.code(s)

    # ── Tab 3: ZIP download ────────────────────────────────────────────────
    with tab_zip:
        st.markdown("Download the **entire project as a ZIP** — ready to extract anywhere.")

        if st.button("📦 Build ZIP", type="primary", use_container_width=True):
            with st.spinner("Packing files into ZIP…"):
                with tempfile.TemporaryDirectory() as tmpdir:
                    generate(parsed_paths, base_dir=tmpdir, overwrite=True)

                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        for root, dirs_found, files_found in os.walk(tmpdir):
                            for fname in files_found:
                                fpath = os.path.join(root, fname)
                                arcname = os.path.relpath(fpath, tmpdir)
                                zf.write(fpath, arcname)
                    zip_buffer.seek(0)

            zip_name = f"{auto_name}.zip"
            st.success(f"✅ ZIP ready — {len(parsed_paths)} items packed.")
            st.download_button(
                label=f"⬇️ Download {zip_name}",
                data=zip_buffer.getvalue(),
                file_name=zip_name,
                mime="application/zip",
                use_container_width=True,
                type="primary",
            )


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="tf-footer">TreeForge 🌳 · Built with Streamlit</div>',
    unsafe_allow_html=True,
)
