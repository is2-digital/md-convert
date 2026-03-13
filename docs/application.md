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

## CLI Usage

```bash
md-convert INPUT.mht --output OUTPUT.md --assets-folder assets
```

## Converter Module

### Data Classes

- **`Resource`** — Holds a single MIME part: `content_type`, `payload` (bytes), `content_location`, `content_id`.
- **`ParsedMHT`** — Result of parsing: `root_html` (str) and `resources` (dict keyed by Content-Location and `cid:` Content-ID).

### Functions

- **`parse_mht(data: bytes) -> ParsedMHT`** — Parses MHT bytes using `email.message_from_bytes()`, validates multipart/related, extracts root HTML and builds resource map. Raises `MHTConvertError` on invalid input.

## Development

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
