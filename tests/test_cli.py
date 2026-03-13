"""CLI integration tests for md-convert."""

from __future__ import annotations

from pathlib import Path

import pytest

from md_convert.cli import build_parser, main
from conftest import build_mht


class TestBuildParser:
    """Tests for argument parsing."""

    def test_input_required(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_input_only(self) -> None:
        args = build_parser().parse_args(["test.mht"])
        assert args.input == Path("test.mht")
        assert args.output is None
        assert args.assets_folder == Path("assets")

    def test_output_flag(self) -> None:
        args = build_parser().parse_args(["test.mht", "-o", "out.md"])
        assert args.output == Path("out.md")

    def test_output_long_flag(self) -> None:
        args = build_parser().parse_args(["test.mht", "--output", "out.md"])
        assert args.output == Path("out.md")

    def test_assets_folder_flag(self) -> None:
        args = build_parser().parse_args(["test.mht", "-a", "imgs"])
        assert args.assets_folder == Path("imgs")

    def test_assets_folder_long_flag(self) -> None:
        args = build_parser().parse_args(["test.mht", "--assets-folder", "imgs"])
        assert args.assets_folder == Path("imgs")

    def test_all_flags(self) -> None:
        args = build_parser().parse_args([
            "input.mht", "-o", "output.md", "-a", "media"
        ])
        assert args.input == Path("input.mht")
        assert args.output == Path("output.md")
        assert args.assets_folder == Path("media")


class TestMainEndToEnd:
    """End-to-end tests for the main() entry point."""

    def test_converts_to_default_md_file(
        self, simple_mht: bytes, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mht_file = tmp_path / "test.mht"
        mht_file.write_bytes(simple_mht)

        main([str(mht_file)])

        default_out = tmp_path / "test.md"
        assert default_out.exists()
        assert "Hello" in default_out.read_text()
        captured = capsys.readouterr()
        assert "successfully converted" in captured.out

    def test_converts_to_output_file(
        self, simple_mht: bytes, tmp_path: Path
    ) -> None:
        mht_file = tmp_path / "test.mht"
        mht_file.write_bytes(simple_mht)
        out_file = tmp_path / "result.md"

        main([str(mht_file), "-o", str(out_file)])

        assert out_file.exists()
        assert "Hello" in out_file.read_text()

    def test_creates_output_parent_dirs(
        self, simple_mht: bytes, tmp_path: Path
    ) -> None:
        mht_file = tmp_path / "test.mht"
        mht_file.write_bytes(simple_mht)
        out_file = tmp_path / "nested" / "dir" / "result.md"

        main([str(mht_file), "-o", str(out_file)])

        assert out_file.exists()

    def test_extracts_assets(
        self, mht_with_image: bytes, tmp_path: Path
    ) -> None:
        mht_file = tmp_path / "test.mht"
        mht_file.write_bytes(mht_with_image)
        assets = tmp_path / "assets"

        main([str(mht_file), "-a", str(assets)])

        assert (assets / "image1.png").exists()

    def test_custom_assets_folder(
        self, mht_with_image: bytes, tmp_path: Path
    ) -> None:
        mht_file = tmp_path / "test.mht"
        mht_file.write_bytes(mht_with_image)
        assets = tmp_path / "media"

        main([str(mht_file), "--assets-folder", str(assets)])

        assert (assets / "image1.png").exists()

    def test_invalid_file_exits_with_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bad_file = tmp_path / "bad.mht"
        bad_file.write_bytes(b"Content-Type: text/plain\r\n\r\nNot MHT")

        with pytest.raises(SystemExit) as exc_info:
            main([str(bad_file)])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_missing_file_exits_with_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "nonexistent.mht"

        with pytest.raises(SystemExit) as exc_info:
            main([str(missing)])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "File not found" in captured.err

    def test_output_contains_markdown_image_ref(
        self, mht_with_image: bytes, tmp_path: Path
    ) -> None:
        mht_file = tmp_path / "test.mht"
        mht_file.write_bytes(mht_with_image)

        main([str(mht_file), "-a", str(tmp_path / "assets")])

        default_out = tmp_path / "test.md"
        assert "image1.png" in default_out.read_text()
