"""Command-line interface for md-convert."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from md_convert import MHTConvertError
from md_convert.converter import convert_mht


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="md-convert",
        description="Convert MHT/MHTML files to Markdown with extracted assets.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the MHT/MHTML file to convert",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output Markdown file path (default: input filename with .md extension)",
    )
    parser.add_argument(
        "-a",
        "--assets-folder",
        type=Path,
        default=Path("assets"),
        help="Directory for extracted assets (default: assets)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the md-convert CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        markdown = convert_mht(args.input, args.assets_folder)
    except MHTConvertError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output if args.output is not None else args.input.with_suffix(".md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"{args.input} successfully converted to .md here: {output_path}")
