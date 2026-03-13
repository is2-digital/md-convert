"""Unit tests for the converter module — MHT parsing and resource extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from md_convert import MHTConvertError
from md_convert.converter import ParsedMHT, Resource, extract_resources, parse_mht
from conftest import build_mht


class TestParseMHT:
    """Tests for parse_mht()."""

    def test_parses_simple_mht(self, simple_mht: bytes) -> None:
        result = parse_mht(simple_mht)
        assert isinstance(result, ParsedMHT)
        assert "<p>Hello</p>" in result.root_html
        assert result.resources == {}

    def test_extracts_resource_by_content_location(
        self, mht_with_image: bytes
    ) -> None:
        result = parse_mht(mht_with_image)
        assert "image1.png" in result.resources
        res = result.resources["image1.png"]
        assert res.content_type == "image/png"
        assert b"PNG" in res.payload

    def test_extracts_resource_by_content_id(
        self, mht_with_image: bytes
    ) -> None:
        result = parse_mht(mht_with_image)
        assert "cid:img001@example" in result.resources
        res = result.resources["cid:img001@example"]
        assert res.content_type == "image/png"

    def test_rejects_non_multipart(self) -> None:
        plain = b"Content-Type: text/plain\r\n\r\nNot an MHT file"
        with pytest.raises(MHTConvertError, match="Expected multipart/related"):
            parse_mht(plain)

    def test_rejects_no_html_root(self) -> None:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("related")
        msg.attach(MIMEText("just plain text", "plain", "utf-8"))
        with pytest.raises(MHTConvertError, match="No HTML root part"):
            parse_mht(msg.as_bytes())

    def test_rejects_empty_multipart(self) -> None:
        # Craft a multipart/related with no parts
        raw = (
            b"MIME-Version: 1.0\r\n"
            b'Content-Type: multipart/related; boundary="=boundary="\r\n'
            b"\r\n"
            b"--=boundary=--\r\n"
        )
        with pytest.raises(MHTConvertError, match="no MIME parts"):
            parse_mht(raw)

    def test_multiple_resources(self) -> None:
        data = build_mht(
            html="<html><body>multi</body></html>",
            resources=[
                {
                    "content_type": "image/png",
                    "payload": b"img1",
                    "content_location": "a.png",
                    "content_id": None,
                },
                {
                    "content_type": "image/jpeg",
                    "payload": b"img2",
                    "content_location": "b.jpg",
                    "content_id": "<id2@ex>",
                },
            ],
        )
        result = parse_mht(data)
        assert "a.png" in result.resources
        assert "b.jpg" in result.resources
        assert "cid:id2@ex" in result.resources
        assert len(result.resources) == 3  # a.png, b.jpg, cid:id2@ex

    def test_resource_dataclass_fields(self, mht_with_image: bytes) -> None:
        result = parse_mht(mht_with_image)
        res = result.resources["image1.png"]
        assert isinstance(res, Resource)
        assert res.content_location == "image1.png"
        assert res.content_id == "<img001@example>"


class TestExtractResources:
    """Tests for extract_resources()."""

    def test_writes_resource_to_disk(
        self, mht_with_image: bytes, tmp_path: Path
    ) -> None:
        parsed = parse_mht(mht_with_image)
        assets = tmp_path / "assets"
        rewrite_map = extract_resources(parsed, assets)

        written = assets / "image1.png"
        assert written.exists()
        assert b"PNG" in written.read_bytes()
        assert "image1.png" in rewrite_map
        assert rewrite_map["image1.png"] == str(assets / "image1.png")

    def test_cid_and_location_share_one_file(
        self, mht_with_image: bytes, tmp_path: Path
    ) -> None:
        parsed = parse_mht(mht_with_image)
        assets = tmp_path / "assets"
        rewrite_map = extract_resources(parsed, assets)

        # Both keys should map to the same file
        assert rewrite_map["image1.png"] == rewrite_map["cid:img001@example"]
        # Only one file written
        assert len(list(assets.iterdir())) == 1

    def test_empty_resources_returns_empty_map(self, tmp_path: Path) -> None:
        parsed = ParsedMHT(root_html="<html></html>", resources={})
        assets = tmp_path / "assets"
        rewrite_map = extract_resources(parsed, assets)

        assert rewrite_map == {}
        assert not assets.exists()

    def test_creates_assets_dir(
        self, mht_with_image: bytes, tmp_path: Path
    ) -> None:
        assets = tmp_path / "nested" / "assets"
        extract_resources(parse_mht(mht_with_image), assets)
        assert assets.is_dir()

    def test_filename_collision_different_content(
        self, tmp_path: Path
    ) -> None:
        data = build_mht(
            html="<html><body>collision</body></html>",
            resources=[
                {
                    "content_type": "image/png",
                    "payload": b"first",
                    "content_location": "img.png",
                    "content_id": None,
                },
                {
                    "content_type": "image/png",
                    "payload": b"second",
                    "content_location": "http://example.com/path/img.png",
                    "content_id": None,
                },
            ],
        )
        parsed = parse_mht(data)
        assets = tmp_path / "assets"
        rewrite_map = extract_resources(parsed, assets)

        files = sorted(f.name for f in assets.iterdir())
        assert "img.png" in files
        assert "img_1.png" in files
        assert (assets / "img.png").read_bytes() == b"first"
        assert (assets / "img_1.png").read_bytes() == b"second"

    def test_multiple_resources_all_written(self, tmp_path: Path) -> None:
        data = build_mht(
            html="<html><body>multi</body></html>",
            resources=[
                {
                    "content_type": "image/png",
                    "payload": b"img1",
                    "content_location": "a.png",
                    "content_id": None,
                },
                {
                    "content_type": "image/jpeg",
                    "payload": b"img2",
                    "content_location": "b.jpg",
                    "content_id": None,
                },
            ],
        )
        parsed = parse_mht(data)
        assets = tmp_path / "assets"
        rewrite_map = extract_resources(parsed, assets)

        assert (assets / "a.png").read_bytes() == b"img1"
        assert (assets / "b.jpg").read_bytes() == b"img2"
        assert "a.png" in rewrite_map
        assert "b.jpg" in rewrite_map

    def test_url_content_location_extracts_filename(
        self, tmp_path: Path
    ) -> None:
        data = build_mht(
            html="<html><body>url</body></html>",
            resources=[
                {
                    "content_type": "image/gif",
                    "payload": b"GIF89a",
                    "content_location": "http://example.com/images/logo.gif",
                    "content_id": None,
                },
            ],
        )
        parsed = parse_mht(data)
        assets = tmp_path / "assets"
        extract_resources(parsed, assets)

        assert (assets / "logo.gif").exists()
