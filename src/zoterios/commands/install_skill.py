"""install-skill command — install SKILL.md into a skills directory."""

import shutil
from importlib import resources
from pathlib import Path

import click


@click.command("install-skill")
@click.argument("skills_dir", type=click.Path(resolve_path=True))
def install_skill(skills_dir: str) -> None:
    """Install the zoterios SKILL.md into a skills directory."""
    dest_dir = Path(skills_dir) / "zoterios"
    dest_dir.mkdir(parents=True, exist_ok=True)

    skill_file = resources.files("zoterios").joinpath("SKILL.md")
    dest = dest_dir / "SKILL.md"
    with resources.as_file(skill_file) as src:
        shutil.copy2(src, dest)

    click.echo(f"✓ Installed to {dest}")
