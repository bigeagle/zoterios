"""arXiv commands — fetch, pdf, markdown, source, save, check, clear-cache."""

import json

import click


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


@click.group()
def arxiv() -> None:
    """Interact with arXiv papers."""


# ---------------------------------------------------------------------------
# arxiv fetch
# ---------------------------------------------------------------------------


@arxiv.command("fetch")
@click.argument("arxiv_id")
@click.pass_context
def fetch(ctx: click.Context, arxiv_id: str) -> None:
    """Fetch metadata for an arXiv paper."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]

    from zoterios.services.arxiv import ArxivService

    svc = ArxivService(cache_dir=settings.cache_dir)

    metadata = svc.get_metadata(arxiv_id)
    if metadata is None:
        click.echo(f"Error: Paper not found on arXiv: {arxiv_id}", err=True)
        raise SystemExit(1)

    if output_json:
        click.echo(json.dumps(metadata.model_dump(), indent=2, ensure_ascii=False))
        return

    click.echo(f"Title:      {metadata.title}")
    click.echo(f"Authors:    {', '.join(metadata.authors)}")
    click.echo(f"Published:  {metadata.published}")
    click.echo(f"Categories: {', '.join(metadata.categories)}")
    click.echo(f"Abstract:   {metadata.abstract}")
    click.echo(f"PDF URL:    {metadata.pdf_url}")
    click.echo(f"arXiv ID:   {metadata.arxiv_id}")


# ---------------------------------------------------------------------------
# arxiv pdf
# ---------------------------------------------------------------------------


@arxiv.command("pdf")
@click.argument("arxiv_id")
@click.option(
    "--open", "open_file", is_flag=True, default=False, help="Open the PDF file"
)
@click.pass_context
def pdf(ctx: click.Context, arxiv_id: str, open_file: bool) -> None:
    """Download the PDF for an arXiv paper."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]

    from zoterios.services.arxiv import ArxivService

    svc = ArxivService(cache_dir=settings.cache_dir)

    try:
        path = svc.download_pdf(arxiv_id)
    except Exception as exc:
        click.echo(f"Error downloading PDF: {exc}", err=True)
        raise SystemExit(1) from exc

    if output_json:
        click.echo(
            json.dumps(
                {"arxiv_id": arxiv_id, "pdf_path": str(path)},
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if open_file:
        click.echo(f"Opening {path}")
        click.launch(str(path))
    else:
        click.echo(str(path))


# ---------------------------------------------------------------------------
# arxiv markdown
# ---------------------------------------------------------------------------


@arxiv.command("markdown")
@click.argument("arxiv_id")
@click.pass_context
def markdown(ctx: click.Context, arxiv_id: str) -> None:
    """Convert an arXiv paper's PDF to markdown."""
    settings = ctx.obj["settings"]

    from zoterios.services.arxiv import ArxivService

    svc = ArxivService(cache_dir=settings.cache_dir)

    try:
        md = svc.get_markdown(arxiv_id)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc

    click.echo(md)


# ---------------------------------------------------------------------------
# arxiv source
# ---------------------------------------------------------------------------


@arxiv.command("source")
@click.argument("arxiv_id")
@click.pass_context
def source(ctx: click.Context, arxiv_id: str) -> None:
    """Download and extract the TeX source for an arXiv paper."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]

    from zoterios.services.arxiv import ArxivService

    svc = ArxivService(cache_dir=settings.cache_dir)

    try:
        source_dir = svc.download_source(arxiv_id)
    except Exception as exc:
        click.echo(f"Error downloading source: {exc}", err=True)
        raise SystemExit(1) from exc

    files = sorted(p.name for p in source_dir.iterdir() if p.is_file())

    if output_json:
        click.echo(
            json.dumps(
                {"arxiv_id": arxiv_id, "source_dir": str(source_dir), "files": files},
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    click.echo(f"Source directory: {source_dir}")
    click.echo(f"Files ({len(files)}):")
    for f in files:
        click.echo(f"  {f}")


# ---------------------------------------------------------------------------
# arxiv save
# ---------------------------------------------------------------------------


@arxiv.command("save")
@click.argument("arxiv_id")
@click.option(
    "--no-pdf", is_flag=True, default=False, help="Save without downloading the PDF"
)
@click.pass_context
def save(ctx: click.Context, arxiv_id: str, no_pdf: bool) -> None:
    """Save an arXiv paper to the local Zotero library."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]

    from zoterios.services.arxiv import ArxivService
    from zoterios.services.connector import ConnectorService

    arxiv_svc = ArxivService(cache_dir=settings.cache_dir)
    connector = ConnectorService(base_url=settings.base_url)

    # Fetch metadata
    metadata = arxiv_svc.get_metadata(arxiv_id)
    if metadata is None:
        click.echo(f"Error: Paper not found on arXiv: {arxiv_id}", err=True)
        raise SystemExit(1)

    # Check if already in Zotero
    existing_key = connector.find_paper_by_title_and_url(
        metadata.title, f"arxiv.org/abs/{arxiv_id}"
    )
    if existing_key:
        if output_json:
            click.echo(
                json.dumps(
                    {"status": "exists", "key": existing_key},
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            click.echo(f"Already in Zotero (key: {existing_key})")
        return

    # Download PDF unless --no-pdf
    pdf_path = None
    if not no_pdf:
        try:
            pdf_path = arxiv_svc.download_pdf(arxiv_id)
        except Exception as exc:
            click.echo(f"Warning: Could not download PDF: {exc}", err=True)

    # Save to Zotero
    try:
        item_key = connector.save_arxiv_paper(
            arxiv_id=arxiv_id,
            metadata=metadata,
            pdf_path=pdf_path,
        )
    except Exception as exc:
        click.echo(f"Error saving to Zotero: {exc}", err=True)
        raise SystemExit(1) from exc

    if output_json:
        click.echo(
            json.dumps(
                {"status": "saved", "key": item_key, "title": metadata.title},
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        click.echo(f"✓ Saved to Zotero (key: {item_key})")
        click.echo(f"  Title: {metadata.title}")


# ---------------------------------------------------------------------------
# arxiv check
# ---------------------------------------------------------------------------


@arxiv.command("check")
@click.argument("arxiv_id")
@click.pass_context
def check(ctx: click.Context, arxiv_id: str) -> None:
    """Check if an arXiv paper is already in Zotero."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]

    from zoterios.services.arxiv import ArxivService
    from zoterios.services.connector import ConnectorService

    arxiv_svc = ArxivService(cache_dir=settings.cache_dir)
    connector = ConnectorService(base_url=settings.base_url)

    metadata = arxiv_svc.get_metadata(arxiv_id)
    if metadata is None:
        click.echo(f"Error: Paper not found on arXiv: {arxiv_id}", err=True)
        raise SystemExit(1)

    key = connector.find_paper_by_title_and_url(
        metadata.title, f"arxiv.org/abs/{arxiv_id}"
    )

    if output_json:
        click.echo(
            json.dumps(
                {"arxiv_id": arxiv_id, "in_zotero": key is not None, "key": key},
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if key:
        click.echo(f"✓ Found in Zotero (key: {key})")
    else:
        click.echo("✗ Not found in Zotero")


# ---------------------------------------------------------------------------
# arxiv clear-cache
# ---------------------------------------------------------------------------


@arxiv.command("clear-cache")
@click.argument("arxiv_id")
@click.pass_context
def clear_cache(ctx: click.Context, arxiv_id: str) -> None:
    """Clear cached data for an arXiv paper."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]

    from zoterios.services.arxiv import ArxivService

    svc = ArxivService(cache_dir=settings.cache_dir)
    cleared = svc.clear_cache(arxiv_id)

    if output_json:
        click.echo(
            json.dumps(
                {"arxiv_id": arxiv_id, "cleared": cleared},
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if cleared:
        click.echo(f"✓ Cache cleared for {arxiv_id}")
    else:
        click.echo(f"No cache found for {arxiv_id}")
