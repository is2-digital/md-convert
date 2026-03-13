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

## 2026-03-12 — Implement MHT parsing (mdc-f9h)

Created `src/md_convert/converter.py` with:
- `Resource` dataclass: holds content_type, payload, content_location, content_id
- `ParsedMHT` dataclass: holds root_html and resources dict
- `parse_mht(data: bytes)` function: parses MHT via `email.message_from_bytes()`, validates multipart/related, identifies root HTML part, builds resource map keyed by Content-Location and Content-ID (cid: scheme)

Created test infrastructure:
- `tests/conftest.py`: `build_mht()` factory and fixtures (`simple_mht`, `mht_with_image`)
- `tests/test_converter.py`: 8 tests covering happy path, resource extraction, error cases

Verification: All 8 tests pass.
