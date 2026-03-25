"""Synchronous PDF-to-Markdown service using markitdown."""

import hashlib
from pathlib import Path

from markitdown import MarkItDown

from zoterios.config import get_settings


class PDFService:
    """Convert PDF files to Markdown with MD5-based file caching."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        settings = get_settings()
        base = cache_dir or settings.cache_dir
        self.cache_dir = base / "markitdown"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.parser = MarkItDown()

    def _get_cache_key(self, pdf_path: str) -> str:
        """Compute an MD5 hash of the PDF file content."""
        try:
            with open(pdf_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return hashlib.md5(pdf_path.encode()).hexdigest()

    def _cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.md"

    def parse_pdf(self, pdf_path: str) -> str:
        """Parse a PDF file and return its content as Markdown.

        Results are cached by MD5 hash of the PDF file.
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        cache_key = self._get_cache_key(pdf_path)
        cp = self._cache_path(cache_key)

        if cp.exists():
            return cp.read_text("utf-8")

        result = self.parser.convert(pdf_path)
        content = result.text_content

        try:
            cp.write_text(content, "utf-8")
        except Exception:
            pass

        return content
