"""Papers commands — list, get, pdf, markdown, import-pdf."""

import json
from pathlib import Path
from urllib.parse import unquote

import click

from zoterios.services.zotero import ZoteroService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_authors(creators: list[dict]) -> str:
    """Format a list of Zotero creator dicts into a readable string."""
    names: list[str] = []
    for c in creators:
        if "name" in c:
            names.append(c["name"])
        else:
            first = c.get("firstName", "")
            last = c.get("lastName", "")
            names.append(f"{first} {last}".strip())
    return ", ".join(names)


def _extract_year(date: str | None) -> str:
    """Extract a 4-digit year from a Zotero date string."""
    if not date:
        return ""
    return date[:4]


def _format_tags(tags: list[dict]) -> str:
    """Format Zotero tag dicts into a comma-separated string."""
    return ", ".join(t.get("tag", "") for t in tags if t.get("tag"))


def _resolve_pdf_path(svc: ZoteroService, item_key: str) -> str:
    """Resolve the local file path for the first PDF attachment of an item."""
    pdfs = svc.get_pdf_attachments(item_key)
    if not pdfs:
        raise click.ClickException(f"No PDF attachment found for item {item_key}")
    file_url = svc.get_pdf_file_path(pdfs[0]["key"])
    if not file_url:
        raise click.ClickException(f"Cannot resolve PDF file path for item {item_key}")
    return unquote(file_url.removeprefix("file://"))


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


@click.group()
def papers() -> None:
    """Manage papers in the local Zotero library."""


# ---------------------------------------------------------------------------
# papers list
# ---------------------------------------------------------------------------


@papers.command("list")
@click.option("--query", "-q", default=None, help="Search query")
@click.option("--tag", "-t", default=None, help="Filter by tag")
@click.option(
    "--limit", "-n", default=20, show_default=True, help="Max number of results"
)
@click.pass_context
def list_papers(
    ctx: click.Context, query: str | None, tag: str | None, limit: int
) -> None:
    """List papers in the Zotero library."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]
    svc = ZoteroService(base_url=settings.base_url)

    try:
        items = svc.get_papers(limit=limit, q=query, tag=tag)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc

    if output_json:
        click.echo(json.dumps(items, indent=2, ensure_ascii=False))
        return

    if not items:
        click.echo("No papers found.")
        return

    for item in items:
        key = item.get("key", "")
        data = item.get("data", {})
        title = data.get("title", "(untitled)")
        authors = _format_authors(data.get("creators", []))
        year = _extract_year(data.get("date"))
        journal = data.get("publicationTitle", "")
        meta_parts = [p for p in (authors, year, journal) if p]
        meta = " · ".join(meta_parts)
        click.echo(f"[{key}] {title}")
        if meta:
            click.echo(f"     {meta}")


# ---------------------------------------------------------------------------
# papers get
# ---------------------------------------------------------------------------


@papers.command("get")
@click.argument("key")
@click.pass_context
def get_paper(ctx: click.Context, key: str) -> None:
    """Get detailed information about a paper."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]
    svc = ZoteroService(base_url=settings.base_url)

    try:
        item = svc.get_paper_by_key(key)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc

    if output_json:
        click.echo(json.dumps(item, indent=2, ensure_ascii=False))
        return

    data = item.get("data", {})
    click.echo(f"Title:    {data.get('title', '')}")
    click.echo(f"Authors:  {_format_authors(data.get('creators', []))}")
    click.echo(f"Year:     {_extract_year(data.get('date'))}")
    click.echo(f"Journal:  {data.get('publicationTitle', '')}")
    click.echo(f"DOI:      {data.get('DOI', '')}")
    click.echo(f"URL:      {data.get('url', '')}")
    click.echo(f"Abstract: {data.get('abstractNote', '')}")
    click.echo(f"Tags:     {_format_tags(data.get('tags', []))}")
    click.echo(f"Key:      {item.get('key', '')}")


# ---------------------------------------------------------------------------
# papers pdf
# ---------------------------------------------------------------------------


@papers.command("pdf")
@click.argument("key")
@click.option(
    "--open", "open_file", is_flag=True, default=False, help="Open the PDF file"
)
@click.pass_context
def get_pdf(ctx: click.Context, key: str, open_file: bool) -> None:
    """Get or open the PDF for a paper."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]
    svc = ZoteroService(base_url=settings.base_url)

    try:
        path = _resolve_pdf_path(svc, key)
    except click.ClickException:
        raise
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc

    if output_json:
        click.echo(
            json.dumps({"key": key, "pdf_path": path}, indent=2, ensure_ascii=False)
        )
        return

    if open_file:
        click.echo(f"Opening {path}")
        click.launch(path)
    else:
        click.echo(path)


# ---------------------------------------------------------------------------
# papers markdown
# ---------------------------------------------------------------------------


@papers.command("markdown")
@click.argument("key")
@click.pass_context
def paper_markdown(ctx: click.Context, key: str) -> None:
    """Convert a paper's PDF to markdown."""
    settings = ctx.obj["settings"]
    svc = ZoteroService(base_url=settings.base_url)

    try:
        path = _resolve_pdf_path(svc, key)
    except click.ClickException:
        raise
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc

    from zoterios.services.pdf import PDFService

    pdf_svc = PDFService(cache_dir=settings.cache_dir)

    try:
        markdown = pdf_svc.parse_pdf(path)
    except Exception as exc:
        click.echo(f"Error converting PDF to markdown: {exc}", err=True)
        raise SystemExit(1) from exc

    click.echo(markdown)


# ---------------------------------------------------------------------------
# papers import-pdf
# ---------------------------------------------------------------------------


@papers.command("import-pdf")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--title", required=True, help="Paper title")
@click.option(
    "--author", "-a", "authors", multiple=True, help="Author name (repeatable)"
)
@click.option("--year", default=None, help="Publication year")
@click.option(
    "--type",
    "item_type",
    default="document",
    show_default=True,
    help="Zotero item type",
)
@click.option("--journal", default=None, help="Journal / publication name")
@click.option("--abstract", default=None, help="Abstract text")
@click.option("--doi", default=None, help="DOI identifier")
@click.option("--url", default=None, help="URL of the paper")
@click.option("--tag", "-t", "tags", multiple=True, help="Tag (repeatable)")
@click.pass_context
def import_pdf(
    ctx: click.Context,
    path: str,
    title: str,
    authors: tuple[str, ...],
    year: str | None,
    item_type: str,
    journal: str | None,
    abstract: str | None,
    doi: str | None,
    url: str | None,
    tags: tuple[str, ...],
) -> None:
    """Import a local PDF file into Zotero."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]

    pdf_path = Path(path)
    if not pdf_path.exists():
        click.echo(f"Error: File not found: {path}", err=True)
        raise SystemExit(1)

    from zoterios.services.connector import ConnectorService

    connector = ConnectorService(base_url=settings.base_url)

    try:
        item_id = connector.import_pdf(
            pdf_path=str(pdf_path),
            title=title,
            authors=list(authors),
            year=year,
            item_type=item_type,
            journal=journal,
            abstract=abstract,
            doi=doi,
            url=url,
            tags=list(tags) if tags else None,
        )
    except Exception as exc:
        click.echo(f"Error importing PDF: {exc}", err=True)
        raise SystemExit(1) from exc

    if output_json:
        click.echo(json.dumps({"item_id": item_id}, indent=2, ensure_ascii=False))
    else:
        click.echo(f"✓ Imported PDF. Item ID: {item_id}")
