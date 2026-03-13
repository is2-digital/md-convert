# md-convert

A CLI utility that converts MHT/MHTML files into clean Markdown, extracting embedded images and resources to a local assets folder with relative links.

## Requirements

- Python >= 3.12

## Installation

```bash
git clone https://github.com/kgoldberg/md-convert.git
cd md-convert
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

## Usage

```bash
md-convert INPUT.mht
```

This parses the MHT file, extracts embedded resources to an `assets/` directory, and writes the Markdown output to `page.md` (same name as input with `.md` extension).

### Options

| Option | Description |
|---|---|
| `INPUT` | Path to the MHT/MHTML file to convert (required) |
| `-o`, `--output FILE` | Write Markdown to a specific file (default: input filename with `.md` extension) |
| `-a`, `--assets-folder DIR` | Directory for extracted assets (default: `assets`) |

### Examples

Convert an MHT file (output written to `page.md`):

```bash
md-convert page.mht
```

Convert to a specific output file:

```bash
md-convert page.mht -o notes/page.md
```

Convert with a custom assets folder:

```bash
md-convert page.mht -o page.md -a images
```

## How It Works

1. **Parse** -- Reads the MHT/MHTML file using Python's `email` module and validates the `multipart/related` MIME structure. Handles non-standard charsets like `unicode` (UTF-16) from Microsoft Word/Outlook.
2. **Extract** -- Writes embedded images and resources to the assets folder, deduplicating files and handling filename collisions.
3. **Rewrite** -- Updates `<img>` and `<link>` references in the HTML to point to the extracted local assets.
4. **Clean** -- Pre-processes Word/Outlook HTML by converting CSS-class headings to proper HTML headings, unwrapping layout tables, and stripping MSO conditional comments.
5. **Convert** -- Transforms the cleaned HTML into Markdown using `markdownify` with ATX-style headings and dash-style bullets.

## Development

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

See [LICENSE](LICENSE) for details.
