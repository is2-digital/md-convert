"""MHT/MHTML parsing, resource extraction, and Markdown conversion."""

from __future__ import annotations

import codecs
import email
import email.policy
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify

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
            try:
                root_html = part.get_content()
            except LookupError:
                # Handle unknown charsets like "unicode" (MS Word/Outlook)
                raw = part.get_payload(decode=True)
                charset = part.get_param("charset", "utf-8")
                fallbacks = [charset, "utf-16", "utf-8", "latin-1"]
                for enc in fallbacks:
                    try:
                        codecs.lookup(enc)
                        root_html = raw.decode(enc)
                        break
                    except (LookupError, UnicodeDecodeError):
                        continue
                if root_html is None:
                    root_html = raw.decode("latin-1")
            continue

        try:
            payload = part.get_content()
        except Exception:
            label = content_location or content_id or part_type
            logger.warning("Skipping undecodable resource: %s", label)
            continue
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


_TITLE_CLASS_MAP = {
    "first-level-title": "h1",
    "second-level-title": "h2",
    "third-level-title": "h3",
}


def _is_layout_table(table):
    """Detect tables used for layout rather than data."""
    rows = table.find_all("tr", recursive=False)
    tbody = table.find("tbody", recursive=False)
    if tbody:
        rows = tbody.find_all("tr", recursive=False)
    if len(rows) == 1:
        cells = rows[0].find_all(["td", "th"], recursive=False)
        if len(cells) == 1:
            return True
    # Tables with no <th> and containing block-level content are likely layout
    if not table.find("th"):
        for td in table.find_all("td"):
            if td.find(["p", "div", "h1", "h2", "h3", "h4", "table", "ul", "ol"]):
                return True
    return False


def _clean_html_for_markdown(html: str) -> str:
    """Pre-process Word/Outlook HTML for better Markdown conversion."""
    # Strip MSO conditional comments: <!--[if ...]>...<![endif]-->
    html = re.sub(r"<!--\[if[^]]*\]>.*?<!\[endif\]-->", "", html, flags=re.DOTALL)
    html = re.sub(r"<!--\[if[^]]*\]>.*?<!\[endif\]-->", "", html, flags=re.DOTALL)

    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, and XML tags
    for tag in soup.find_all(["script", "style", "xml", "o:p"]):
        tag.decompose()

    # Convert title-class paragraphs to proper heading tags
    for css_class, heading_tag in _TITLE_CLASS_MAP.items():
        for p in soup.find_all("p", class_=css_class):
            p.name = heading_tag
            if p.attrs.get("class"):
                del p.attrs["class"]

    # Unwrap layout tables — replace with their inner content
    changed = True
    while changed:
        changed = False
        for table in soup.find_all("table"):
            if _is_layout_table(table):
                table.unwrap()
                changed = True
    # Also unwrap leftover tbody/tr/td that no longer sit inside a table
    for tag_name in ["tbody", "tr", "td"]:
        for tag in soup.find_all(tag_name):
            if not tag.find_parent("table"):
                tag.unwrap()

    return str(soup)


def convert_html_to_markdown(html: str) -> str:
    """Convert HTML to Markdown using markdownify.

    Uses ATX-style headings (``# H1``), dash bullets (``-``), and strips
    ``<script>`` and ``<style>`` tags before conversion.

    Args:
        html: HTML string to convert.

    Returns:
        Markdown string.
    """
    cleaned = _clean_html_for_markdown(html)
    md = markdownify(
        cleaned,
        heading_style="ATX",
        bullets="-",
    )
    # Collapse excessive blank lines (3+ → 2)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md


def convert_mht(input_path: Path, assets_dir: Path) -> str:
    """Convert an MHT/MHTML file to Markdown with extracted assets.

    Orchestrates the full pipeline: parse MHT, extract resources,
    rewrite HTML references, and convert to Markdown.

    Args:
        input_path: Path to the MHT/MHTML file.
        assets_dir: Directory to extract resource assets into.

    Returns:
        Markdown string.

    Raises:
        MHTConvertError: If the file does not exist, is not valid
            multipart/related MIME, or contains no HTML root part.
    """
    if not input_path.is_file():
        raise MHTConvertError(f"File not found: {input_path}")

    data = input_path.read_bytes()
    parsed = parse_mht(data)
    rewrite_map = extract_resources(parsed, assets_dir)
    html = rewrite_html_references(parsed.root_html, rewrite_map)
    return convert_html_to_markdown(html)
