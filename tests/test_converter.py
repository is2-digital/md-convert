"""Unit tests for the converter module — MHT parsing."""

from __future__ import annotations

import pytest

from md_convert import MHTConvertError
from md_convert.converter import ParsedMHT, Resource, parse_mht
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
