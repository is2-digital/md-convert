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
