"""MHT/MHTML parsing, resource extraction, and Markdown conversion."""

from __future__ import annotations

import email
import email.policy
import logging
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from md_convert import MHTConvertError

logger = logging.getLogger(__name__)


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


def _safe_filename(location: str) -> str:
    """Derive a safe filename from a Content-Location URL or cid reference."""
    parsed = urlparse(unquote(location))
    path = parsed.path if parsed.path else location
    name = PurePosixPath(path).name
    # Strip anything that isn't filename-safe
    name = name.replace("\x00", "")
    return name if name else "resource"


def _dedupe_filename(name: str, used: set[str]) -> str:
    """Return *name* if unused, otherwise append _1, _2, … until unique."""
    if name not in used:
        return name
    stem = PurePosixPath(name).stem
    suffix = PurePosixPath(name).suffix
    counter = 1
    while True:
        candidate = f"{stem}_{counter}{suffix}"
        if candidate not in used:
            return candidate
        counter += 1


def extract_resources(
    parsed: ParsedMHT,
    assets_dir: Path,
) -> dict[str, str]:
    """Write resource payloads to *assets_dir* and return a URL rewrite map.

    Args:
        parsed: The result of ``parse_mht()``.
        assets_dir: Directory to write extracted files into (created if needed).

    Returns:
        Mapping from original reference URL (Content-Location or ``cid:…``)
        to the relative file path within *assets_dir*
        (e.g. ``"assets/image1.png"``).
    """
    if not parsed.resources:
        return {}

    assets_dir.mkdir(parents=True, exist_ok=True)

    rewrite_map: dict[str, str] = {}
    # Track which Resource objects have already been written so that
    # multiple keys pointing to the same resource share one file.
    written: dict[int, str] = {}  # id(Resource) -> relative path
    used_filenames: set[str] = set()

    for key, resource in parsed.resources.items():
        rid = id(resource)
        if rid in written:
            rewrite_map[key] = written[rid]
            continue

        # Derive filename from Content-Location when available
        raw_name = _safe_filename(
            resource.content_location or key
        )
        filename = _dedupe_filename(raw_name, used_filenames)
        used_filenames.add(filename)

        dest = assets_dir / filename
        try:
            dest.write_bytes(resource.payload)
        except OSError as exc:
            logger.warning("Skipping resource %s: %s", key, exc)
            continue

        rel_path = str(assets_dir / filename)
        rewrite_map[key] = rel_path
        written[rid] = rel_path

    return rewrite_map


def rewrite_html_references(
    html: str,
    rewrite_map: dict[str, str],
) -> str:
    """Replace resource references in HTML using the rewrite map.

    Rewrites ``src`` attributes on ``<img>`` tags and ``href`` attributes
    on ``<link>`` tags when they match a key in *rewrite_map*.

    Args:
        html: The root HTML string from the MHT file.
        rewrite_map: Mapping from original reference URLs to local asset paths,
            as returned by :func:`extract_resources`.

    Returns:
        Modified HTML string with references rewritten to local paths.
    """
    soup = BeautifulSoup(html, "html.parser")

    for img in soup.find_all("img", src=True):
        src = img["src"]
        if src in rewrite_map:
            img["src"] = rewrite_map[src]

    for link in soup.find_all("link", href=True):
        href = link["href"]
        if href in rewrite_map:
            link["href"] = rewrite_map[href]

    return str(soup)
