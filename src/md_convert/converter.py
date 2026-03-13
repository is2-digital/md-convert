"""MHT/MHTML parsing, resource extraction, and Markdown conversion."""

from __future__ import annotations

import email
import email.policy
from dataclasses import dataclass, field
from pathlib import Path

from md_convert import MHTConvertError


@dataclass
class Resource:
    """A single MIME part extracted from an MHT file."""

    content_type: str
    payload: bytes
    content_location: str | None = None
    content_id: str | None = None


@dataclass
class ParsedMHT:
    """Result of parsing an MHT file."""

    root_html: str
    resources: dict[str, Resource] = field(default_factory=dict)


def parse_mht(data: bytes) -> ParsedMHT:
    """Parse MHT/MHTML bytes into root HTML and a resource map.

    Args:
        data: Raw bytes of the MHT file.

    Returns:
        ParsedMHT with root HTML content and resources keyed by
        Content-Location and Content-ID.

    Raises:
        MHTConvertError: If the data is not valid multipart/related MIME
            or contains no HTML root part.
    """
    msg = email.message_from_bytes(data, policy=email.policy.default)

    content_type = msg.get_content_type()
    if content_type != "multipart/related":
        raise MHTConvertError(
            f"Expected multipart/related, got {content_type}"
        )

    parts = list(msg.iter_parts())
    if not parts:
        raise MHTConvertError("MHT file contains no MIME parts")

    root_html: str | None = None
    resources: dict[str, Resource] = {}

    for part in parts:
        part_type = part.get_content_type()
        content_location = part.get("Content-Location")
        content_id = part.get("Content-ID")

        if root_html is None and part_type == "text/html":
            root_html = part.get_content()
            continue

        payload = part.get_content()
        if isinstance(payload, str):
            payload = payload.encode("utf-8")

        resource = Resource(
            content_type=part_type,
            payload=payload,
            content_location=content_location,
            content_id=content_id,
        )

        if content_location:
            resources[content_location] = resource
        if content_id:
            # Strip angle brackets from Content-ID: <id> -> id
            cid = content_id.strip("<>")
            resources[f"cid:{cid}"] = resource

    if root_html is None:
        raise MHTConvertError("No HTML root part found in MHT file")

    return ParsedMHT(root_html=root_html, resources=resources)
