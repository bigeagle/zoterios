"""Pydantic data models for zoterios."""

from pydantic import BaseModel, Field


class ArxivMetadata(BaseModel):
    """Metadata for an arXiv paper."""

    arxiv_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    published: str = ""
    categories: list[str] = Field(default_factory=list)
    pdf_url: str


class Paper(BaseModel):
    """Normalized representation of a Zotero library paper."""

    id: str
    title: str
    authors: str = ""
    year: str | None = None
    journal: str | None = None
    abstract: str | None = None
    doi: str | None = None
    url: str | None = None
    tags: list[str] = Field(default_factory=list)
    pdf_path: str | None = None
    has_pdf: bool = False
