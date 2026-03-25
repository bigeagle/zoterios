"""CLI entry point for zoterios."""

import click

from zoterios.commands.arxiv import arxiv
from zoterios.commands.markdownit import markdownit
from zoterios.commands.papers import papers
from zoterios.commands.ping import ping
from zoterios.config import get_settings


@click.group()
@click.option(
    "--base-url",
    default=None,
    help="Zotero local API URL (default: http://localhost:23119)",
)
@click.option(
    "--cache-dir",
    default=None,
    help="Cache directory path (default: ~/.cache/zoterios)",
)
@click.option(
    "--json", "output_json", is_flag=True, default=False, help="Output in JSON format"
)
@click.pass_context
def cli(
    ctx: click.Context, base_url: str | None, cache_dir: str | None, output_json: bool
) -> None:
    """zoterios — A CLI tool to interact with local Zotero library."""
    ctx.ensure_object(dict)
    settings = get_settings(base_url=base_url, cache_dir=cache_dir)
    ctx.obj["settings"] = settings
    ctx.obj["json"] = output_json


cli.add_command(ping)
cli.add_command(papers)
cli.add_command(arxiv)
cli.add_command(markdownit)


def main() -> None:
    cli()
