# Role

You are an expert Python developer working on md-convert, a CLI utility that converts MHT/MHTML files into Markdown with extracted assets.

# Core Context

* md-convert is a Python CLI tool that parses MHT/MHTML files (MIME-bundled web pages) and converts them to clean Markdown.
* Extracts embedded images and resources to a local assets folder with relative links in the output Markdown.
* Uses Python's standard `email` module for MIME parsing, `markdownify` + `beautifulsoup4` for HTML-to-Markdown conversion, and `argparse` for the CLI.
* Packaged with `pyproject.toml` (hatchling build system) and installable via `pip install -e .` inside the project's `.venv/` virtual environment.
* Track work via beads. Run `bd ready` to see what's available.

# Key References

* `docs/application.md` — Full application architecture, pipeline flow, and conventions

# Architecture

```
├── .venv/                         # Python virtual environment (not in git)
├── pyproject.toml              # PEP 621 project metadata, dependencies
├── src/
│   └── md_convert/
│       ├── __init__.py
│       ├── cli.py              # argparse entry point
│       └── converter.py        # MHT parsing, resource extraction, Markdown conversion
└── tests/
    ├── conftest.py             # synthetic MHT fixture factories
    ├── test_converter.py       # unit tests for converter module
    └── test_cli.py             # CLI integration tests
```

# Implementation Guidelines

* Use Python's stdlib `email` module for MIME parsing — no third-party MIME libraries.
* Use `markdownify` for HTML-to-Markdown conversion with BeautifulSoup4 for HTML manipulation.
* Rewrite image/resource references in HTML before Markdown conversion (not after via regex).
* Use `argparse` for CLI — no click/typer dependencies.
* Use `pathlib.Path` for all file path operations.
* Tests use `pytest` with synthetic MHT fixtures built via `email.mime` (no binary fixture files).
* Raise custom `MHTConvertError` for user-facing errors; skip undecodable resources with warnings.
* This project runs directly on the host — no Docker required. See prompt-sandbox.md for dev commands.
