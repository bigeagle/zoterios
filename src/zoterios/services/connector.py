"""Synchronous Zotero Connector API client.

Handles saving items and attachments to Zotero via the Connector HTTP API.
"""

import logging
import random
import re
import string
from datetime import datetime

import httpx

from zoterios.models import ArxivMetadata

logger = logging.getLogger(__name__)


def _generate_item_id() -> str:
    """Generate a random 8-char item ID.

    First character is an uppercase letter; remaining characters are
    alphanumeric (upper + lower + digits).
    """
    first = random.choice(string.ascii_uppercase)
    rest = "".join(random.choices(string.ascii_letters + string.digits, k=7))
    return first + rest


def _process_authors(authors: list[str]) -> list[dict]:
    """Split ``"FirstName LastName"`` strings into Zotero creator dicts."""
    creators: list[dict] = []
    for name in authors:
        parts = name.strip().split()
        if len(parts) >= 2:
            creators.append(
                {
                    "firstName": " ".join(parts[:-1]),
                    "lastName": parts[-1],
                    "creatorType": "author",
                }
            )
        elif parts:
            creators.append(
                {
                    "firstName": "",
                    "lastName": parts[0],
                    "creatorType": "author",
                }
            )
    return creators


def _validate_date(date_str: str) -> str | None:
    """Validate and normalise a date string to ``YYYY-MM-DD``.

    Returns *None* if the string cannot be parsed.
    """
    if not date_str:
        return None
    # Try ISO-style formats
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last-resort regex for YYYY-MM-DD somewhere in the string
    m = re.search(r"\d{4}-\d{2}-\d{2}", date_str)
    if m:
        return m.group(0)
    return None


class ConnectorService:
    """Client for the Zotero Connector HTTP API."""

    def __init__(self, base_url: str = "http://localhost:23119") -> None:
        self.base_url = base_url

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=30.0)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def test_connection(self) -> bool:
        """Ping ``/connector/ping``. Returns *True* if Zotero responds."""
        with self._client() as client:
            try:
                r = client.get("/connector/ping")
                return r.status_code == 200
            except Exception:
                return False

    # ------------------------------------------------------------------
    # Save helpers
    # ------------------------------------------------------------------

    def save_item(
        self,
        item_type: str,
        title: str,
        creators: list[dict],
        abstract_note: str = "",
        url: str = "",
        date: str = "",
        doi: str = "",
        extra: str = "",
        tags: list[str] | None = None,
    ) -> str | None:
        """Save an item via ``/connector/saveItems``.

        Returns the generated *item_id*, or *None* on failure.
        """
        item_id = _generate_item_id()
        item: dict = {
            "itemType": item_type,
            "id": item_id,
            "title": title,
            "creators": creators,
            "abstractNote": abstract_note,
            "url": url,
            "date": date,
            "DOI": doi,
            "extra": extra,
        }
        if tags:
            item["tags"] = [{"tag": t} for t in tags]

        payload = {"items": [item], "uri": url or "http://zoterios.local"}
        with self._client() as client:
            r = client.post(
                "/connector/saveItems",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if r.status_code in (200, 201):
                return item_id
            logger.error("save_item failed: %s %s", r.status_code, r.text)
            return None

    def save_attachment(
        self,
        parent_item_key: str,
        pdf_path: str,
        pdf_url: str,
        filename: str,
        session_id: str,
    ) -> None:
        """Save a PDF attachment via ``/connector/saveAttachment``.

        Uploads the raw PDF bytes with metadata in the ``X-Metadata`` header,
        matching the Zotero Connector protocol.
        """
        import json
        from pathlib import Path

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise RuntimeError(f"PDF file not found: {pdf_path}")
        pdf_content = pdf_file.read_bytes()

        metadata = {
            "parentItemID": parent_item_key,
            "url": pdf_url,
            "title": filename,
            "sessionID": session_id,
        }
        with self._client() as client:
            r = client.post(
                "/connector/saveAttachment",
                content=pdf_content,
                headers={
                    "Content-Type": "application/pdf",
                    "X-Metadata": json.dumps(metadata, ensure_ascii=False),
                },
            )
            if r.status_code not in (200, 201):
                raise RuntimeError(
                    f"Failed to save attachment: {r.status_code} {r.text}"
                )

    # ------------------------------------------------------------------
    # High-level workflows
    # ------------------------------------------------------------------

    def import_pdf(
        self,
        pdf_path: str,
        title: str,
        authors: list[str],
        year: str | None = None,
        item_type: str = "document",
        journal: str | None = None,
        abstract: str | None = None,
        doi: str | None = None,
        url: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Complete workflow: save item + save PDF attachment.

        Returns the generated item ID.
        """
        item_id = _generate_item_id()
        session_id = f"zoterios-import-{item_id}"
        creators = _process_authors(authors)

        item: dict = {
            "itemType": item_type,
            "id": item_id,
            "title": title,
            "creators": creators,
            "abstractNote": abstract or "",
            "url": url or "",
            "DOI": doi or "",
            "date": year or "",
            "publicationTitle": journal or "",
        }
        if tags:
            item["tags"] = [{"tag": t} for t in tags]

        payload = {
            "items": [item],
            "uri": url or "http://zoterios.local",
            "sessionID": session_id,
        }
        with self._client() as client:
            r = client.post(
                "/connector/saveItems",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if r.status_code not in (200, 201):
                raise RuntimeError(f"Failed to save item: {r.status_code} {r.text}")

        # Attach the PDF if a path was provided
        if pdf_path:
            from pathlib import Path

            filename = Path(pdf_path).name
            self.save_attachment(
                parent_item_key=item_id,
                pdf_path=str(pdf_path),
                pdf_url=url or "",
                filename=filename,
                session_id=session_id,
            )

        return item_id

    def find_paper_by_title_and_url(
        self,
        title: str,
        url_fragment: str,
    ) -> str | None:
        """Search for an existing paper by title and URL fragment.

        Returns the item key if found, otherwise *None*.
        """
        with self._client() as client:
            try:
                r = client.get(
                    "/api/users/0/items/top",
                    params={
                        "format": "json",
                        "q": title,
                        "limit": 20,
                    },
                )
                r.raise_for_status()
                items = r.json()
                for item in items:
                    data = item.get("data", {})
                    item_url = data.get("url", "")
                    if url_fragment and url_fragment in item_url:
                        return item.get("key")
                return None
            except Exception:
                return None

    def save_arxiv_paper(
        self,
        arxiv_id: str,
        metadata: ArxivMetadata,
        pdf_path: str | None = None,
    ) -> str:
        """Save an arXiv paper with full metadata to Zotero.

        Returns the generated item ID.
        """
        item_id = _generate_item_id()
        session_id = f"zoterios-arxiv-{arxiv_id}"
        creators = _process_authors(metadata.authors)
        validated_date = _validate_date(metadata.published)

        item: dict = {
            "itemType": "preprint",
            "id": item_id,
            "title": metadata.title,
            "creators": creators,
            "abstractNote": metadata.abstract,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "publisher": "arXiv",
            "archiveID": f"arXiv:{arxiv_id}",
            "DOI": f"10.48550/arXiv.{arxiv_id}",
            "extra": f"arXiv:{arxiv_id}",
        }
        if validated_date:
            item["date"] = validated_date

        if metadata.categories:
            item["tags"] = [{"tag": c} for c in metadata.categories]

        payload = {
            "items": [item],
            "uri": f"https://arxiv.org/abs/{arxiv_id}",
            "sessionID": session_id,
        }
        with self._client() as client:
            r = client.post(
                "/connector/saveItems",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if r.status_code not in (200, 201):
                raise RuntimeError(
                    f"Failed to save arXiv paper: {r.status_code} {r.text}"
                )

        # Attach the PDF if a local path was provided
        if pdf_path:
            from pathlib import Path

            filename = Path(pdf_path).name
            self.save_attachment(
                parent_item_key=item_id,
                pdf_path=str(pdf_path),
                pdf_url=metadata.pdf_url,
                filename=filename,
                session_id=session_id,
            )

        return item_id
