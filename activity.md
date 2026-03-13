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

## 2026-03-12 — Implement resource extraction (mdc-p43)

Added `extract_resources()` to `src/md_convert/converter.py`:
- Writes decoded resource payloads to an assets directory
- Deduplicates by Resource identity (Content-Location and cid: keys sharing the same resource produce one file)
- Handles filename collisions via `_1`, `_2`, … suffixes
- Derives filenames from Content-Location URLs (strips path/query)
- Returns a rewrite map: original URL -> written file path
- Logs warnings for unwritable resources

Added 7 tests in `TestExtractResources` covering: write to disk, cid/location dedup, empty resources, directory creation, filename collisions, multiple resources, URL-based filename extraction.

Verification: All 15 tests pass.

## 2026-03-12 — Implement HTML reference rewriting (mdc-blx)

Added `rewrite_html_references()` to `src/md_convert/converter.py`:
- Parses HTML with BeautifulSoup4 (`html.parser`)
- Rewrites `img[src]` attributes using the rewrite map
- Rewrites `link[href]` attributes using the rewrite map
- Handles Content-Location URLs, `cid:` references, and absolute URLs
- Leaves unmatched references unchanged

Added 8 tests in `TestRewriteHtmlReferences` covering: img src rewrite, cid reference, link href, unmatched references, absolute URLs, multiple images, empty map, no matching elements.

Verification: All 23 tests pass.

## 2026-03-12 — Implement Markdown conversion (mdc-5tg)

Added `convert_html_to_markdown()` to `src/md_convert/converter.py`:
- Strips `<script>` and `<style>` tags via BeautifulSoup before conversion
- Converts HTML to Markdown using `markdownify` with ATX headings and dash bullets
- Preserves image references and links in Markdown output

Added 8 tests in `TestConvertHtmlToMarkdown` covering: paragraphs, ATX headings, dash bullets, script stripping, style stripping, image preservation, links, empty HTML.

Verification: All 31 tests pass.

## 2026-03-12 — Implement convert_mht public API (mdc-0n5)

Added `convert_mht(input_path, assets_dir)` to `src/md_convert/converter.py`:
- Orchestrates the full pipeline: parse MHT -> extract resources -> rewrite HTML references -> convert to Markdown
- Validates input file existence, raises `MHTConvertError` for missing files
- Delegates MIME validation and HTML root checks to `parse_mht()`
- Skips undecodable resources with logger warning (try/except in `parse_mht` around `get_content()`)

Added 6 tests in `TestConvertMHT` covering: full pipeline, HTML-only input, missing file, invalid MIME, no HTML root, undecodable resource skipping.

Verification: All 37 tests pass.

## 2026-03-12 — Close Phase 2: Core Converter (mdc-fr9)

Final code review of the converter module (parent task with all 5 children completed):
- MHT parsing, resource extraction, HTML rewriting, Markdown conversion all implemented
- Full pipeline orchestrated via `convert_mht()` public API
- Error handling via `MHTConvertError`, undecodable resource skipping with warnings
- All 37 tests pass across 5 test classes
- No issues found; parent task closed.

## 2026-03-12 — Implement cli.py argparse entry point (mdc-199)

Created `src/md_convert/cli.py` with:
- `build_parser()`: constructs ArgumentParser with positional `input` (Path), `-o/--output` (Path, default stdout), `-a/--assets-folder` (Path, default `assets`)
- `main(argv=None)`: parses args, calls `convert_mht()`, writes to file or stdout, handles `MHTConvertError` with stderr message and exit code 1
- Creates parent directories for output file if needed

Updated `docs/application.md` with CLI module documentation.

Verification: Help output correct, error handling works (missing file prints error to stderr), all 37 existing tests pass.

## 2026-03-12 — Create test fixtures in conftest.py (mdc-zg1)

Added three new pytest fixtures to `tests/conftest.py`:
- `images_mht`: HTML with two images referenced by Content-Location (PNG + JPEG)
- `cid_mht`: HTML with two images referenced via `cid:` URIs (PNG + GIF)
- `malformed_mht`: Plain text bytes (not valid multipart/related MIME)

These supplement the existing `simple_mht` and `mht_with_image` fixtures for comprehensive test coverage.

Verification: All 37 existing tests pass. Smoke-tested all new fixtures produce correct MIME structures.

## 2026-03-12 — Write test_cli.py (mdc-ci4)

Created `tests/test_cli.py` with 15 tests in two classes:
- `TestBuildParser` (7 tests): input required, defaults, short/long flags for output and assets-folder, all flags combined
- `TestMainEndToEnd` (8 tests): stdout output, file output, parent dir creation, asset extraction, custom assets folder, invalid file error exit, missing file error exit, markdown image reference in output

Verification: All 52 tests pass (37 converter + 15 CLI).

## 2026-03-12 — Update README.md with usage instructions (mdc-2lm)

Updated `README.md` with:
- Project overview and requirements
- Installation instructions (clone, venv, pip install)
- CLI usage with options table (input, --output, --assets-folder)
- Three usage examples (stdout, file output, custom assets folder)
- "How It Works" section explaining the 4-step pipeline
- Development section with test commands

Verification: All 52 tests pass.
