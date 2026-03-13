"""Unit tests for the converter module — MHT parsing and resource extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from md_convert import MHTConvertError
from md_convert.converter import (
    ParsedMHT,
    Resource,
    convert_html_to_markdown,
    convert_mht,
    extract_resources,
    parse_mht,
    rewrite_html_references,
)
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


class TestRewriteHtmlReferences:
    """Tests for rewrite_html_references()."""

    def test_rewrites_img_src(self) -> None:
        html = '<html><body><img src="image1.png"></body></html>'
        rewrite_map = {"image1.png": "assets/image1.png"}
        result = rewrite_html_references(html, rewrite_map)
        assert 'src="assets/image1.png"' in result

    def test_rewrites_cid_reference(self) -> None:
        html = '<html><body><img src="cid:img001@example"></body></html>'
        rewrite_map = {"cid:img001@example": "assets/image1.png"}
        result = rewrite_html_references(html, rewrite_map)
        assert 'src="assets/image1.png"' in result

    def test_rewrites_link_href(self) -> None:
        html = '<html><head><link href="style.css" rel="stylesheet"></head></html>'
        rewrite_map = {"style.css": "assets/style.css"}
        result = rewrite_html_references(html, rewrite_map)
        assert 'href="assets/style.css"' in result

    def test_leaves_unmatched_references_unchanged(self) -> None:
        html = '<html><body><img src="unknown.png"></body></html>'
        rewrite_map = {"other.png": "assets/other.png"}
        result = rewrite_html_references(html, rewrite_map)
        assert 'src="unknown.png"' in result

    def test_rewrites_absolute_url(self) -> None:
        html = '<html><body><img src="http://example.com/images/logo.gif"></body></html>'
        rewrite_map = {
            "http://example.com/images/logo.gif": "assets/logo.gif"
        }
        result = rewrite_html_references(html, rewrite_map)
        assert 'src="assets/logo.gif"' in result

    def test_rewrites_multiple_images(self) -> None:
        html = '<html><body><img src="a.png"><img src="b.jpg"></body></html>'
        rewrite_map = {
            "a.png": "assets/a.png",
            "b.jpg": "assets/b.jpg",
        }
        result = rewrite_html_references(html, rewrite_map)
        assert 'src="assets/a.png"' in result
        assert 'src="assets/b.jpg"' in result

    def test_empty_rewrite_map(self) -> None:
        html = '<html><body><img src="image.png"></body></html>'
        result = rewrite_html_references(html, {})
        assert 'src="image.png"' in result

    def test_no_matching_elements(self) -> None:
        html = "<html><body><p>No images here</p></body></html>"
        rewrite_map = {"image.png": "assets/image.png"}
        result = rewrite_html_references(html, rewrite_map)
        assert "No images here" in result


class TestConvertHtmlToMarkdown:
    """Tests for convert_html_to_markdown()."""

    def test_converts_paragraph(self) -> None:
        html = "<html><body><p>Hello world</p></body></html>"
        result = convert_html_to_markdown(html)
        assert "Hello world" in result

    def test_atx_headings(self) -> None:
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        result = convert_html_to_markdown(html)
        assert "# Title" in result
        assert "## Subtitle" in result

    def test_dash_bullets(self) -> None:
        html = "<ul><li>one</li><li>two</li></ul>"
        result = convert_html_to_markdown(html)
        assert "- one" in result
        assert "- two" in result

    def test_strips_script_tags(self) -> None:
        html = '<html><body><p>Keep</p><script>alert("x")</script></body></html>'
        result = convert_html_to_markdown(html)
        assert "Keep" in result
        assert "alert" not in result
        assert "script" not in result

    def test_strips_style_tags(self) -> None:
        html = "<html><body><p>Keep</p><style>body{color:red}</style></body></html>"
        result = convert_html_to_markdown(html)
        assert "Keep" in result
        assert "color:red" not in result

    def test_preserves_image_references(self) -> None:
        html = '<img src="assets/photo.png" alt="A photo">'
        result = convert_html_to_markdown(html)
        assert "assets/photo.png" in result
        assert "A photo" in result

    def test_converts_links(self) -> None:
        html = '<a href="https://example.com">Click</a>'
        result = convert_html_to_markdown(html)
        assert "[Click](https://example.com)" in result

    def test_empty_html(self) -> None:
        result = convert_html_to_markdown("")
        assert result.strip() == ""


class TestConvertMHT:
    """Tests for convert_mht() public API."""

    def test_full_pipeline(self, mht_with_image: bytes, tmp_path: Path) -> None:
        mht_file = tmp_path / "test.mht"
        mht_file.write_bytes(mht_with_image)
        assets = tmp_path / "assets"

        markdown = convert_mht(mht_file, assets)

        assert "image1.png" in markdown
        assert (assets / "image1.png").exists()

    def test_simple_html_only(self, simple_mht: bytes, tmp_path: Path) -> None:
        mht_file = tmp_path / "simple.mht"
        mht_file.write_bytes(simple_mht)
        assets = tmp_path / "assets"

        markdown = convert_mht(mht_file, assets)

        assert "Hello" in markdown
        assert not assets.exists()

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.mht"
        with pytest.raises(MHTConvertError, match="File not found"):
            convert_mht(missing, tmp_path / "assets")

    def test_invalid_mime_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.mht"
        bad_file.write_bytes(b"Content-Type: text/plain\r\n\r\nNot MHT")
        with pytest.raises(MHTConvertError, match="Expected multipart/related"):
            convert_mht(bad_file, tmp_path / "assets")

    def test_no_html_root_raises(self, tmp_path: Path) -> None:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("related")
        msg.attach(MIMEText("plain text only", "plain", "utf-8"))
        no_html = tmp_path / "nohtml.mht"
        no_html.write_bytes(msg.as_bytes())

        with pytest.raises(MHTConvertError, match="No HTML root part"):
            convert_mht(no_html, tmp_path / "assets")

    def test_skips_undecodable_resource(self, tmp_path: Path) -> None:
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("related")
        msg.attach(MIMEText("<html><body><p>OK</p></body></html>", "html", "utf-8"))
        bad_part = MIMEBase("image", "png")
        bad_part.set_payload(b"\x89PNG not-valid-base64 !!!")
        bad_part["Content-Transfer-Encoding"] = "base64"
        bad_part["Content-Location"] = "broken.png"
        msg.attach(bad_part)

        mht_file = tmp_path / "undecodable.mht"
        mht_file.write_bytes(msg.as_bytes())

        markdown = convert_mht(mht_file, tmp_path / "assets")
        assert "OK" in markdown
