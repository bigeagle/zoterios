"""Synchronous arXiv service using httpx."""

import gzip
import json
import logging
import shutil
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from zoterios.config import get_settings
from zoterios.models import ArxivMetadata
from zoterios.services.pdf import PDFService

logger = logging.getLogger(__name__)


class ArxivService:
    """Fetch arXiv metadata, PDFs, and source packages."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        settings = get_settings()
        base = cache_dir or settings.cache_dir
        self.base_url = "https://arxiv.org"
        self.pdf_cache_dir = base / "arxiv" / "pdf"
        self.metadata_cache_dir = base / "arxiv" / "metadata"
        self.source_cache_dir = base / "arxiv" / "source"
        self.pdf_cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_cache_dir.mkdir(parents=True, exist_ok=True)
        self.source_cache_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_service = PDFService(cache_dir=base)

    def _get_client(self) -> httpx.Client:
        settings = get_settings()
        proxy = settings.https_proxy or settings.http_proxy or None
        return httpx.Client(timeout=60.0, proxy=proxy if proxy else None)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self, arxiv_id: str) -> ArxivMetadata | None:
        """Fetch metadata with 24-hour file-based cache."""
        cache_file = self.metadata_cache_dir / f"{arxiv_id}.json"

        # Check cache
        if cache_file.exists():
            try:
                cached_data = json.loads(cache_file.read_text("utf-8"))
                cached_time = datetime.fromisoformat(
                    cached_data.get("_cached_at", "1970-01-01")
                )
                if datetime.now() - cached_time < timedelta(hours=24):
                    cached_data.pop("_cached_at", None)
                    return ArxivMetadata.model_validate(cached_data)
            except Exception:
                pass

        # Fetch from API
        metadata = self._fetch_metadata(arxiv_id)
        if metadata:
            data = metadata.model_dump()
            data["_cached_at"] = datetime.now().isoformat()
            try:
                cache_file.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), "utf-8"
                )
            except Exception:
                pass
        return metadata

    def _fetch_metadata(self, arxiv_id: str) -> ArxivMetadata | None:
        """Parse arXiv Atom API response."""
        url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
        with self._get_client() as client:
            r = client.get(url)
            r.raise_for_status()

        root = ET.fromstring(r.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            return None

        title_el = entry.find("atom:title", ns)
        authors = entry.findall("atom:author/atom:name", ns) or []
        summary = entry.find("atom:summary", ns)
        published = entry.find("atom:published", ns)
        categories = [
            c.attrib["term"]
            for c in entry.findall("atom:category", ns)
            if "term" in c.attrib
        ]

        pdf_url = f"{self.base_url}/pdf/{arxiv_id}"
        for link in entry.findall("atom:link", ns):
            if (
                link.get("title") == "pdf"
                and link.get("type") == "application/pdf"
                and link.get("href")
            ):
                pdf_url = link.get("href", "")
                break

        return ArxivMetadata(
            arxiv_id=arxiv_id,
            title=(
                title_el.text.strip() if title_el is not None and title_el.text else ""
            ),
            authors=[a.text or "" for a in authors],
            abstract=(
                summary.text.strip() if summary is not None and summary.text else ""
            ),
            published=(
                published.text if published is not None and published.text else ""
            ),
            categories=categories,
            pdf_url=pdf_url,
        )

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    def download_pdf(self, arxiv_id: str) -> Path:
        """Download PDF with caching."""
        meta = self.get_metadata(arxiv_id)
        pdf_url = meta.pdf_url if meta else f"{self.base_url}/pdf/{arxiv_id}"

        pdf_filename = pdf_url.split("/")[-1]
        if not pdf_filename.endswith(".pdf"):
            pdf_filename += ".pdf"

        cache_file = self.pdf_cache_dir / pdf_filename
        if cache_file.exists() and cache_file.stat().st_size > 0:
            return cache_file

        with self._get_client() as client:
            with client.stream("GET", pdf_url) as r:
                r.raise_for_status()
                with open(cache_file, "wb") as f:
                    for chunk in r.iter_bytes(8192):
                        f.write(chunk)
        return cache_file

    def get_markdown(self, arxiv_id: str) -> str:
        """Download PDF and convert to markdown."""
        pdf_path = self.download_pdf(arxiv_id)
        return self.pdf_service.parse_pdf(str(pdf_path))

    # ------------------------------------------------------------------
    # Source
    # ------------------------------------------------------------------

    def download_source(self, arxiv_id: str) -> Path:
        """Download arXiv source (tex) package and extract it.

        arXiv source URL: ``https://arxiv.org/src/<arxiv_id>``
        Usually returns a tar.gz file containing .tex files and images.
        """
        source_dir = self.source_cache_dir / arxiv_id

        # If already extracted, return
        if source_dir.exists() and any(source_dir.iterdir()):
            return source_dir

        source_dir.mkdir(parents=True, exist_ok=True)

        source_url = f"https://arxiv.org/src/{arxiv_id}"
        with self._get_client() as client:
            r = client.get(source_url, follow_redirects=True)
            r.raise_for_status()
            content = r.content

        # Download to a temp file
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Check if it's gzipped
            with gzip.open(tmp_path, "rb") as gz:
                gz.read(1)  # test if valid gzip

            with tarfile.open(tmp_path, "r:gz") as tar:
                tar.extractall(path=source_dir, filter="data")
        except (tarfile.TarError, gzip.BadGzipFile):
            # Not a tar.gz — might be a single tex file
            dest = source_dir / "main.tex"
            shutil.copy2(tmp_path, dest)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        return source_dir

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def clear_cache(self, arxiv_id: str) -> bool:
        """Clear cached files for an arXiv paper."""
        try:
            # Clear PDF
            for f in self.pdf_cache_dir.iterdir():
                if arxiv_id in f.name:
                    f.unlink(missing_ok=True)
            # Clear metadata
            meta_file = self.metadata_cache_dir / f"{arxiv_id}.json"
            meta_file.unlink(missing_ok=True)
            # Clear source
            source_dir = self.source_cache_dir / arxiv_id
            if source_dir.exists():
                shutil.rmtree(source_dir)
            return True
        except Exception:
            return False
