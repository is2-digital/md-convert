# Activity Log

## 2026-03-12 — Create pyproject.toml (mdc-ys8)

Created `pyproject.toml` with:
- hatchling build system
- Project metadata (name, version, description, python >= 3.12)
- Dependencies: markdownify, beautifulsoup4
- Dev dependencies: pytest
- Entry point: `md-convert = md_convert.cli:main`
- Hatch wheel config pointing to `src/md_convert`
- pytest config with `testpaths = ["tests"]`

Verification: TOML syntax validated with Python's `tomllib`.

## 2026-03-12 — Create src/md_convert/__init__.py (mdc-vah)

Created `src/md_convert/__init__.py` with:
- Package docstring
- `__version__ = "0.1.0"` (matches pyproject.toml)
- `MHTConvertError` exception class for user-facing errors

Verification: Installed package in editable mode, confirmed `__version__` and `MHTConvertError` import correctly.
