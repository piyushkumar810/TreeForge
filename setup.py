from setuptools import setup, find_packages

setup(
    name="treeforge",
    version="0.1.0",
    description="Forge project structures from any folder tree",
    author="TreeForge",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "streamlit>=1.32.0",
    ],
    entry_points={
        "console_scripts": [
            "treeforge=treeforge.cli:main",
        ],
    },
)
