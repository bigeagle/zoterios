"""markdownit command — convert files to markdown via markitdown."""

import click


@click.command("markdownit")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def markdownit(path: str) -> None:
    """Convert a PDF or other file to markdown."""
    from markitdown import MarkItDown

    try:
        result = MarkItDown().convert(path)
        click.echo(result.text_content)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
