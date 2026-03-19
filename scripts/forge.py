#!/usr/bin/env python3
"""Skill Forge - Generate Claude Code skills from web research using browser-use."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path so we can import skill_gen
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.table import Table

from skill_gen.core.researcher import SkillResearcher, _build_llm
from skill_gen.core.generator import SkillGenerator
from skill_gen.core.validator import SkillValidator, Severity


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Skill Forge - Generate Claude Code skills from web research.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s --topic "docker compose" --output ./skills/docker-compose/
  %(prog)s --url https://docs.docker.com --output ./skills/docker/
  %(prog)s --topic "fastapi" --template api --output ./skills/fastapi/
  %(prog)s --topic "playwright" --template browser --headed --output ./skills/playwright/
""",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Topic to research (e.g. 'docker compose', 'fastapi')",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Starting URL to research from",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for the generated skill (SKILL.md will be created inside)",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=os.getenv("SKILL_GEN_TEMPLATE", "basic"),
        choices=["basic", "browser", "api", "cli", "composite"],
        help="Template to use for generation (default: basic)",
    )
    parser.add_argument(
        "--llm",
        type=str,
        default=os.getenv("SKILL_GEN_LLM", "claude"),
        choices=["claude", "gemini", "openai"],
        help="LLM provider to use for research (default: claude)",
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
        help="Maximum pages to visit per session (default: 10)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=os.getenv("SKILL_GEN_HEADED", "false").lower() == "true",
        help="Run browser in headed (visible) mode",
    )
    args = parser.parse_args()

    if not args.topic and not args.url:
        parser.error("At least one of --topic or --url is required")

    return args


async def run_research(args: argparse.Namespace) -> dict:
    """Execute the research phase using the existing SkillResearcher.

    Returns:
        A research data dict suitable for SkillGenerator.generate().
    """
    llm = _build_llm(args.llm)
    researcher = SkillResearcher(
        llm=llm,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        headed=args.headed,
    )
    return await researcher.research(topic=args.topic, url=args.url)


async def run_generation(research_data: dict, args: argparse.Namespace) -> str:
    """Execute the generation phase using the existing SkillGenerator.

    Returns:
        Absolute path to the generated SKILL.md.
    """
    generator = SkillGenerator(template=args.template)
    return await generator.generate(research_data, args.output)


def run_validation(output_path: str) -> bool:
    """Execute the validation phase using the existing SkillValidator.

    Returns:
        True if validation passes (no errors), False otherwise.
    """
    validator = SkillValidator()
    result = validator.validate(output_path)

    # Display validation results
    table = Table(title="Validation Results", show_lines=False)
    table.add_column("Status", width=8)
    table.add_column("Message")
    table.add_column("Suggestion", style="dim")

    for issue in result.issues:
        if issue.severity == Severity.ERROR:
            icon = "[bold red]FAIL[/bold red]"
        elif issue.severity == Severity.WARNING:
            icon = "[bold yellow]WARN[/bold yellow]"
        else:
            icon = "[bold green]OK[/bold green]"
        table.add_row(icon, issue.message, issue.suggestion or "")

    console.print(table)
    console.print()

    if result.valid:
        console.print("[bold green]Validation passed.[/bold green]")
    else:
        console.print("[bold red]Validation failed -- see errors above.[/bold red]")

    return result.valid


async def main() -> int:
    args = parse_args()

    topic_display = args.topic or args.url or "unknown"
    console.print(
        Panel(
            f"[bold]Skill Forge[/bold]\n\n"
            f"Topic:    {topic_display}\n"
            f"Template: {args.template}\n"
            f"LLM:      {args.llm}\n"
            f"Output:   {args.output}\n"
            f"Depth:    {args.max_depth}  |  Max Pages: {args.max_pages}\n"
            f"Headed:   {args.headed}",
            title="Configuration",
            border_style="blue",
        )
    )
    console.print()

    # ---- Phase 1: Research ----
    console.rule("[bold cyan]Phase 1: Research[/bold cyan]")
    console.print()

    research_data: dict | None = None
    t0 = time.monotonic()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Researching with browser-use...", total=None)
        try:
            research_data = await run_research(args)
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

    elapsed_research = time.monotonic() - t0

    # Show research stats
    num_commands = len(research_data.get("commands", []))
    num_examples = len(research_data.get("examples", []))
    num_sources = len(research_data.get("source_urls", []))
    console.print()
    console.print(
        f"  Name:        {research_data.get('name', 'unknown')}\n"
        f"  Commands:    {num_commands}\n"
        f"  Examples:    {num_examples}\n"
        f"  Sources:     {num_sources}\n"
        f"  Time:        {elapsed_research:.1f}s"
    )
    console.print()

    # ---- Phase 2: Generation ----
    console.rule("[bold cyan]Phase 2: Generation[/bold cyan]")
    console.print()

    output_path: str = ""
    t1 = time.monotonic()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Generating SKILL.md...", total=None)
        try:
            output_path = await run_generation(research_data, args)
            progress.update(task, description="[green]Generation complete")
        except Exception as exc:
            progress.update(task, description="[red]Generation failed")
            console.print()
            console.print(f"[bold red]Error during generation:[/bold red] {exc}")
            return 1

    elapsed_gen = time.monotonic() - t1
    console.print()
    console.print(f"  Output: {output_path}")
    console.print(f"  Time:   {elapsed_gen:.1f}s")
    console.print()

    # Show a preview of the generated content
    content = Path(output_path).read_text(encoding="utf-8")
    preview_lines = content.split("\n")[:30]
    preview = "\n".join(preview_lines)
    if len(content.split("\n")) > 30:
        preview += "\n... (truncated)"
    console.print(
        Panel(
            Syntax(preview, "markdown", theme="monokai", line_numbers=False),
            title="Preview",
            border_style="dim",
        )
    )
    console.print()

    # ---- Phase 3: Validation ----
    console.rule("[bold cyan]Phase 3: Validation[/bold cyan]")
    console.print()

    is_valid = run_validation(output_path)
    console.print()

    # ---- Summary ----
    total_time = time.monotonic() - t0
    console.rule("[bold cyan]Summary[/bold cyan]")
    console.print()
    if is_valid:
        status = "[bold green]SUCCESS[/bold green]"
    else:
        status = "[bold yellow]COMPLETE (with warnings)[/bold yellow]"
    console.print(f"  Status:  {status}")
    console.print(f"  Output:  {output_path}")
    console.print(f"  Total:   {total_time:.1f}s")
    console.print()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
