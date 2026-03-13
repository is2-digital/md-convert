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
