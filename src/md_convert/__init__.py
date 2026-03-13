"""md-convert: CLI utility that converts MHT/MHTML files into Markdown with extracted assets."""

__version__ = "0.1.0"


class MHTConvertError(Exception):
    """Raised for user-facing errors during MHT conversion."""
