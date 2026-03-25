"""Ping command — test connection to Zotero."""

import json

import click

from zoterios.services.zotero import ZoteroService


@click.command()
@click.pass_context
def ping(ctx: click.Context) -> None:
    """Test connection to Zotero."""
    settings = ctx.obj["settings"]
    output_json = ctx.obj["json"]
    svc = ZoteroService(base_url=settings.base_url)
    ok = svc.test_connection()
    if output_json:
        click.echo(json.dumps({"connected": ok}))
    elif ok:
        click.echo("✓ Connected to Zotero")
    else:
        click.echo(
            "✗ Cannot connect to Zotero. Is it running on " + settings.base_url + "?",
            err=True,
        )
        raise SystemExit(1)
