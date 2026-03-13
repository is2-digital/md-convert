"""Synthetic MHT fixture factories for testing."""

from __future__ import annotations

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pytest


def build_mht(
    html: str = "<html><body><p>Hello</p></body></html>",
    resources: list[dict] | None = None,
) -> bytes:
    """Build a synthetic MHT file as bytes.

    Args:
        html: The root HTML content.
        resources: Optional list of dicts with keys:
            content_type, payload (bytes), content_location, content_id.

    Returns:
        Raw bytes of the multipart/related MIME message.
    """
    msg = MIMEMultipart("related")

    html_part = MIMEText(html, "html", "utf-8")
    msg.attach(html_part)

    for res in resources or []:
        maintype, subtype = res["content_type"].split("/", 1)
        part = MIMEBase(maintype, subtype)
        part.set_payload(res["payload"])
        if res.get("content_location"):
            part["Content-Location"] = res["content_location"]
        if res.get("content_id"):
            part["Content-ID"] = res["content_id"]
        msg.attach(part)

    return msg.as_bytes()


@pytest.fixture
def simple_mht() -> bytes:
    """A minimal MHT file with just an HTML part."""
    return build_mht()


@pytest.fixture
def mht_with_image() -> bytes:
    """An MHT file with an HTML part and an image resource."""
    return build_mht(
        html='<html><body><img src="image1.png"></body></html>',
        resources=[
            {
                "content_type": "image/png",
                "payload": b"\x89PNG fake image data",
                "content_location": "image1.png",
                "content_id": "<img001@example>",
            },
        ],
    )


@pytest.fixture
def images_mht() -> bytes:
    """An MHT file with HTML and two images referenced by Content-Location."""
    return build_mht(
        html=(
            "<html><body>"
            '<img src="image1.png">'
            '<img src="image2.jpg">'
            "</body></html>"
        ),
        resources=[
            {
                "content_type": "image/png",
                "payload": b"\x89PNG first image",
                "content_location": "image1.png",
                "content_id": None,
            },
            {
                "content_type": "image/jpeg",
                "payload": b"\xff\xd8\xff second image",
                "content_location": "image2.jpg",
                "content_id": None,
            },
        ],
    )


@pytest.fixture
def cid_mht() -> bytes:
    """An MHT file with images referenced via cid: URIs."""
    return build_mht(
        html=(
            "<html><body>"
            '<img src="cid:logo@example">'
            '<img src="cid:banner@example">'
            "</body></html>"
        ),
        resources=[
            {
                "content_type": "image/png",
                "payload": b"\x89PNG logo data",
                "content_location": None,
                "content_id": "<logo@example>",
            },
            {
                "content_type": "image/gif",
                "payload": b"GIF89a banner data",
                "content_location": None,
                "content_id": "<banner@example>",
            },
        ],
    )


@pytest.fixture
def malformed_mht() -> bytes:
    """A plain-text message that is not valid multipart/related MIME."""
    return b"This is just plain text, not a valid MHT file."
