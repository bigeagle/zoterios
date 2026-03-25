"""Synchronous Zotero Local API client."""

import httpx


class ZoteroService:
    """Client for the Zotero local HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:23119",
        user_id: int = 0,
    ) -> None:
        self.base_url = base_url
        self.user_id = user_id

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=30.0)

    def test_connection(self) -> bool:
        """Ping Zotero local API. Returns True if running."""
        with self._client() as client:
            try:
                r = client.get(
                    f"/api/users/{self.user_id}/items/top",
                    timeout=5.0,
                )
                return r.status_code == 200
            except Exception:
                return False

    def get_papers(
        self,
        limit: int = 100,
        q: str | None = None,
        tag: str | None = None,
    ) -> list[dict]:
        """Fetch top-level items sorted by dateAdded desc."""
        params: dict = {
            "format": "json",
            "limit": limit,
            "sort": "dateAdded",
            "direction": "desc",
        }
        if q:
            params["q"] = q
        if tag:
            params["tag"] = tag
        with self._client() as client:
            r = client.get(
                f"/api/users/{self.user_id}/items/top",
                params=params,
            )
            r.raise_for_status()
            return r.json()

    def get_paper_by_key(self, key: str) -> dict:
        """Fetch a single item by Zotero key."""
        with self._client() as client:
            r = client.get(f"/api/users/{self.user_id}/items/{key}")
            r.raise_for_status()
            return r.json()

    def get_pdf_attachments(self, item_key: str) -> list[dict]:
        """Get PDF attachments for an item."""
        with self._client() as client:
            r = client.get(
                f"/api/users/{self.user_id}/items/{item_key}/children",
            )
            r.raise_for_status()
            children = r.json()
            return [
                c
                for c in children
                if c.get("data", {}).get("itemType") == "attachment"
                and c.get("data", {}).get("contentType") == "application/pdf"
            ]

    def get_pdf_file_path(self, attachment_key: str) -> str | None:
        """Get local file path of a PDF attachment via 302 redirect."""
        with self._client() as client:
            r = client.get(
                f"/api/users/{self.user_id}/items/{attachment_key}/file",
                follow_redirects=False,
            )
            if r.status_code == 302:
                return r.headers.get("location")
            return None

    def get_papers_with_pdfs(
        self,
        limit: int = 100,
        q: str | None = None,
        tag: str | None = None,
    ) -> list[dict]:
        """Get papers enriched with PDF path info."""
        papers = self.get_papers(limit, q, tag)
        result = []
        for paper in papers:
            key = paper.get("key")
            if key:
                pdfs = self.get_pdf_attachments(key)
                if pdfs:
                    paper["pdf_attachments"] = pdfs
                    pdf_path = self.get_pdf_file_path(pdfs[0]["key"])
                    if pdf_path:
                        paper["pdf_path"] = pdf_path
                result.append(paper)
        return result
