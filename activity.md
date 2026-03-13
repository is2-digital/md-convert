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
