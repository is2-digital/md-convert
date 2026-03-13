# md-convert Application Architecture

## Overview

md-convert is a CLI utility that converts MHT/MHTML files into Markdown with extracted assets.

## Tech Stack

- **Python** >= 3.12
- **Build system**: hatchling (PEP 621 via `pyproject.toml`)
- **Dependencies**: markdownify, beautifulsoup4
- **Dev dependencies**: pytest
- **MIME parsing**: Python stdlib `email` module
- **CLI**: argparse

## Project Structure

```
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

## Entry Point

```
md-convert = md_convert.cli:main
```

## CLI Module

The CLI is implemented in `cli.py` using `argparse`.

- **`build_parser()`** — Constructs the `ArgumentParser` with positional `INPUT` and optional `--output`/`--assets-folder` flags.
- **`main(argv=None)`** — Entry point. Parses args, calls `convert_mht()`, writes Markdown to `--output` or stdout. Prints `MHTConvertError` messages to stderr and exits with code 1.

### Usage

```bash
md-convert INPUT.mht                          # output to stdout, assets in ./assets/
md-convert INPUT.mht -o OUTPUT.md             # output to file
md-convert INPUT.mht -o OUTPUT.md -a imgs     # custom assets folder
```

## Converter Module

### Data Classes

- **`Resource`** — Holds a single MIME part: `content_type`, `payload` (bytes), `content_location`, `content_id`.
- **`ParsedMHT`** — Result of parsing: `root_html` (str) and `resources` (dict keyed by Content-Location and `cid:` Content-ID).

### Functions

- **`parse_mht(data: bytes) -> ParsedMHT`** — Parses MHT bytes using `email.message_from_bytes()`, validates multipart/related, extracts root HTML and builds resource map. Raises `MHTConvertError` on invalid input.
- **`extract_resources(parsed: ParsedMHT, assets_dir: Path) -> dict[str, str]`** — Writes decoded resource payloads from `parsed.resources` to `assets_dir`, deduplicating by `Resource` identity so that Content-Location and `cid:` keys sharing the same resource produce one file. Handles filename collisions by appending `_1`, `_2`, … suffixes. Returns a rewrite map from original reference URL to the written file path.
- **`rewrite_html_references(html: str, rewrite_map: dict[str, str]) -> str`** — Parses HTML with BeautifulSoup4 and rewrites `img[src]` and `link[href]` attributes using the rewrite map from `extract_resources()`. Handles Content-Location URLs, `cid:` references, and absolute URLs. Returns the modified HTML string.
- **`convert_html_to_markdown(html: str) -> str`** — Converts HTML to Markdown using `markdownify`. Strips `<script>` and `<style>` tags via BeautifulSoup before conversion. Uses ATX-style headings (`# H1`) and dash bullets (`-`).
- **`convert_mht(input_path: Path, assets_dir: Path) -> str`** — Public API that orchestrates the full pipeline: reads the MHT file, parses it, extracts resources, rewrites HTML references, and converts to Markdown. Raises `MHTConvertError` for missing files, invalid MIME, or missing HTML root. Skips undecodable resources with a warning.

## Development

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
