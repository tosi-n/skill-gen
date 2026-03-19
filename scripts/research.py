#!/usr/bin/env python3
"""Standalone research script - Research a topic or URL and output findings as JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from skill_gen.core.researcher import SkillResearcher, _build_llm


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Research a topic or URL using browser-use and output findings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s --topic "docker compose" --output research.json
  %(prog)s --url https://docs.python.org/3/whatsnew/ --output python-news.json
  %(prog)s --topic "kubernetes operators" --llm gemini --max-pages 15
""",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Topic to research",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="URL to research",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (if not specified, prints to stdout)",
    )
    parser.add_argument(
        "--llm",
        type=str,
        default=os.getenv("SKILL_GEN_LLM", "claude"),
        choices=["claude", "gemini", "openai"],
        help="LLM provider (default: claude)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=int(os.getenv("SKILL_GEN_MAX_DEPTH", "3")),
        help="Maximum crawl depth (default: 3)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=int(os.getenv("SKILL_GEN_MAX_PAGES", "10")),
        help="Maximum pages to visit (default: 10)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=os.getenv("SKILL_GEN_HEADED", "false").lower() == "true",
        help="Run browser in headed (visible) mode",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print the human-readable summary, skip full JSON output to console",
    )
    args = parser.parse_args()

    if not args.topic and not args.url:
        parser.error("At least one of --topic or --url is required")

    return args


def print_summary(data: dict[str, Any], topic_display: str) -> None:
    """Print a human-readable summary of the research results."""
    console.print()
    console.rule("[bold cyan]Research Summary[/bold cyan]")
    console.print()

    console.print(f"  [bold]Topic:[/bold]          {topic_display}")
    console.print(f"  [bold]Name:[/bold]           {data.get('name', 'unknown')}")
    console.print(f"  [bold]Commands:[/bold]       {len(data.get('commands', []))}")
    console.print(f"  [bold]Examples:[/bold]       {len(data.get('examples', []))}")
    console.print(f"  [bold]Install cmds:[/bold]   {len(data.get('installation', []))}")
    console.print(f"  [bold]Workflows:[/bold]      {len(data.get('workflows', []))}")
    console.print(f"  [bold]Gotchas:[/bold]        {len(data.get('gotchas', []))}")
    console.print(f"  [bold]Source URLs:[/bold]     {len(data.get('source_urls', []))}")
    console.print()

    description = data.get("description", "")
    if description:
        console.print(
            Panel(
                description[:1000] + ("..." if len(description) > 1000 else ""),
                title="Description",
                border_style="green",
            )
        )
        console.print()

    source_urls = data.get("source_urls", [])
    if source_urls:
        console.print("[bold]Source URLs:[/bold]")
        for i, url in enumerate(source_urls, 1):
            console.print(f"  {i}. {url}")
        console.print()

    commands = data.get("commands", [])
    if commands:
        table = Table(title="Commands", show_lines=True)
        table.add_column("#", width=4, justify="right")
        table.add_column("Name", min_width=15)
        table.add_column("Syntax", min_width=30)
        table.add_column("Description", min_width=30)

        for i, cmd in enumerate(commands[:15], 1):
            if isinstance(cmd, dict):
                table.add_row(
                    str(i),
                    cmd.get("name", ""),
                    cmd.get("syntax", ""),
                    cmd.get("description", ""),
                )
        console.print(table)
        console.print()

    examples = data.get("examples", [])
    if examples:
        table = Table(title="Code Examples", show_lines=True)
        table.add_column("#", width=4, justify="right")
        table.add_column("Language", width=10)
        table.add_column("Description", min_width=30)
        table.add_column("Code Preview", min_width=40)

        for i, ex in enumerate(examples[:10], 1):
            if isinstance(ex, dict):
                code_preview = ex.get("code", "")[:100].replace("\n", " ")
                if len(ex.get("code", "")) > 100:
                    code_preview += "..."
                table.add_row(
                    str(i),
                    ex.get("language", ""),
                    ex.get("description", ""),
                    code_preview,
                )
        console.print(table)
        console.print()

    gotchas = data.get("gotchas", [])
    if gotchas:
        console.print("[bold yellow]Gotchas:[/bold yellow]")
        for g in gotchas:
            console.print(f"  [yellow]- {g}[/yellow]")
        console.print()


async def main() -> int:
    args = parse_args()

    topic_display = args.topic or args.url or "unknown"

    console.print(
        Panel(
            f"[bold]Skill Research[/bold]\n\n"
            f"Target:     {topic_display}\n"
            f"LLM:        {args.llm}\n"
            f"Max depth:  {args.max_depth}\n"
            f"Max pages:  {args.max_pages}\n"
            f"Headed:     {args.headed}\n"
            f"Output:     {args.output or '(stdout)'}",
            title="Configuration",
            border_style="blue",
        )
    )
    console.print()

    # Run research
    t0 = time.monotonic()
    research_data: dict[str, Any] | None = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Researching with browser-use...", total=None)
        try:
            llm = _build_llm(args.llm)
            researcher = SkillResearcher(
                llm=llm,
                max_depth=args.max_depth,
                max_pages=args.max_pages,
                headed=args.headed,
            )
            research_data = await researcher.research(topic=args.topic, url=args.url)
            progress.update(task, description="[green]Research complete")
        except Exception as exc:
            progress.update(task, description="[red]Research failed")
            console.print()
            console.print(f"[bold red]Error during research:[/bold red] {exc}")
            console.print()
            console.print(
                "[dim]Hint: Make sure your API key is set and browser-use is installed.\n"
                "  pip install browser-use langchain-anthropic\n"
                "  playwright install chromium[/dim]"
            )
            return 1

    elapsed = time.monotonic() - t0
    console.print()
    console.print(f"[dim]Research completed in {elapsed:.1f}s[/dim]")

    # Print human-readable summary
    print_summary(research_data, topic_display)

    # Output JSON
    json_str = json.dumps(research_data, indent=2, ensure_ascii=False, default=str)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_str, encoding="utf-8")
        console.print(f"[bold green]JSON output written to:[/bold green] {out_path.resolve()}")
        console.print()
    elif not args.summary_only:
        console.rule("[bold cyan]JSON Output[/bold cyan]")
        console.print()
        # Print to stdout (not through rich, so it can be piped)
        print(json_str)
        console.print()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
