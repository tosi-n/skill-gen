#!/usr/bin/env python3
"""Generate a Claude Code skill directly from one or more URLs.

Usage:
    python scripts/from_url.py URL [URL ...] --output ./skills/my-skill/
    python scripts/from_url.py https://blog.example.com/post --name my-tool
    python scripts/from_url.py https://docs.tool.dev/guide https://docs.tool.dev/api -o ./out/
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from skill_gen.core.generator import SkillGenerator
from skill_gen.core.researcher import SkillResearcher, _build_llm
from skill_gen.core.validator import SkillValidator, Severity

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a skill from one or more URLs (blogs, docs, tutorials).",
    )
    parser.add_argument("urls", nargs="+", help="One or more URLs to extract content from.")
    parser.add_argument("--name", "-n", default=None, help="Skill name (auto-detected if omitted).")
    parser.add_argument("--output", "-o", required=True, help="Output directory for the generated skill.")
    parser.add_argument(
        "--template", default="basic",
        choices=["basic", "browser", "api", "cli", "composite"],
        help="Skill template (default: basic).",
    )
    parser.add_argument("--llm", default="claude", choices=["claude", "gemini", "openai"], help="LLM provider.")
    parser.add_argument("--headed", action="store_true", help="Show browser window.")
    return parser.parse_args()


def merge_data(datasets: list[dict], name: str | None = None) -> dict:
    """Merge multiple research data dicts into one combined dataset."""
    if not datasets:
        return {}
    if len(datasets) == 1 and not name:
        return datasets[0]

    merged: dict = {
        "name": name or datasets[0].get("name", ""),
        "description": "",
        "installation": [],
        "commands": [],
        "workflows": [],
        "configuration": [],
        "examples": [],
        "gotchas": [],
        "allowed_tools": [],
        "source_urls": [],
    }

    descriptions: list[str] = []
    for d in datasets:
        desc = d.get("description", "")
        if desc:
            descriptions.append(desc)
        for key in merged:
            if key in ("name", "description"):
                continue
            existing = d.get(key, [])
            if isinstance(existing, list):
                merged[key].extend(existing)

    if descriptions:
        merged["description"] = max(descriptions, key=len)

    return merged


async def main() -> int:
    args = parse_args()

    console.print(Panel(
        f"[bold]Skill from URL[/bold]\n\n"
        + "\n".join(f"  {u}" for u in args.urls)
        + f"\n\n  Template: {args.template}  |  LLM: {args.llm}",
        title="Configuration",
        border_style="blue",
    ))

    llm = _build_llm(args.llm)
    all_data: list[dict] = []

    for i, url in enumerate(args.urls, 1):
        console.print(f"\n[bold cyan]URL {i}/{len(args.urls)}:[/bold cyan] {url}")
        with console.status("  Browsing and extracting..."):
            researcher = SkillResearcher(
                llm=llm, max_depth=1, max_pages=2, headed=args.headed,
            )
            try:
                data = await researcher.research_url(url)
                all_data.append(data)
                console.print(f"  [green]Extracted {len(data.get('examples', []))} examples, "
                              f"{len(data.get('commands', []))} commands[/green]")
            except Exception as exc:
                console.print(f"  [red]Failed: {exc}[/red]")
                continue

    if not all_data:
        console.print("[red]No data extracted from any URL.[/red]")
        return 1

    merged = merge_data(all_data, name=args.name)

    # Show summary
    tbl = Table(title="Extracted Data", show_lines=True)
    tbl.add_column("Field", style="bold")
    tbl.add_column("Count")
    tbl.add_row("Name", merged.get("name", ""))
    tbl.add_row("Install commands", str(len(merged.get("installation", []))))
    tbl.add_row("Commands / API", str(len(merged.get("commands", []))))
    tbl.add_row("Code examples", str(len(merged.get("examples", []))))
    tbl.add_row("Source URLs", str(len(merged.get("source_urls", []))))
    console.print(tbl)

    # Generate
    console.print()
    with console.status("[bold green]Generating SKILL.md..."):
        generator = SkillGenerator(template=args.template)
        skill_path = await generator.generate(merged, args.output)

    console.print(f"[green]Skill written to:[/green] {skill_path}")

    # Validate
    validator = SkillValidator()
    result = validator.validate(skill_path)
    for issue in result.issues:
        if issue.severity == Severity.ERROR:
            console.print(f"  [red]ERROR[/red] {issue.message}")
        elif issue.severity == Severity.WARNING:
            console.print(f"  [yellow]WARN[/yellow]  {issue.message}")

    if result.valid:
        console.print(f"\n[bold green]Done! Skill ready at {skill_path}[/bold green]")
    else:
        console.print(f"\n[bold yellow]Skill generated with warnings at {skill_path}[/bold yellow]")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
