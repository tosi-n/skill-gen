#!/usr/bin/env python3
"""Evolve - Improve an existing skill with fresh research."""

from __future__ import annotations

import argparse
import asyncio
import difflib
import json
import os
import re
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
from rich.syntax import Syntax

from skill_gen.core.researcher import SkillResearcher, _build_llm


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evolve an existing skill with fresh research.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s --skill ./skills/docker/SKILL.md --query "docker compose v2 changes"
  %(prog)s --skill ./skills/fastapi/SKILL.md --url https://fastapi.tiangolo.com/release-notes/
  %(prog)s --skill ./skills/git/SKILL.md --query "git worktree best practices" --url https://git-scm.com/docs/git-worktree
""",
    )
    parser.add_argument(
        "--skill",
        type=str,
        required=True,
        help="Path to the existing SKILL.md to improve",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="What to research / improve (e.g. 'error handling best practices')",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Optional URL to research for new content",
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
        help="Run browser in headed mode",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the diff without writing changes",
    )
    args = parser.parse_args()

    if not args.query and not args.url:
        parser.error("At least one of --query or --url is required")

    return args


def read_existing_skill(path: str) -> str:
    """Read and return the existing skill content."""
    p = Path(path)
    if not p.exists():
        console.print(f"[bold red]Error:[/bold red] Skill file not found: {p}")
        sys.exit(1)
    return p.read_text(encoding="utf-8")


def merge_content(existing: str, research_data: dict[str, Any], query: str) -> str:
    """Merge new research findings into the existing skill content.

    Strategy:
    - Parse existing sections by H2 headers
    - Build new content snippets from research data
    - Append a 'Research Updates' section with the new findings
    """
    lines = existing.split("\n")

    # Collect new content from research data
    new_snippets: list[str] = []

    # Add new commands
    new_commands = research_data.get("commands", [])
    if new_commands:
        cmd_lines = ["### New Commands"]
        for cmd in new_commands[:10]:
            if isinstance(cmd, dict):
                name = cmd.get("name", "")
                syntax = cmd.get("syntax", "")
                desc = cmd.get("description", "")
                cmd_lines.append(f"- `{syntax or name}` -- {desc}")
            else:
                cmd_lines.append(f"- `{cmd}`")
        cmd_lines.append("")
        new_snippets.append("\n".join(cmd_lines))

    # Add new code examples
    new_examples = research_data.get("examples", [])
    if new_examples:
        for ex in new_examples[:5]:
            if isinstance(ex, dict):
                desc = ex.get("description", "Example")
                lang = ex.get("language", "bash")
                code = ex.get("code", "")
                if code.strip():
                    new_snippets.append(f"### {desc}\n\n```{lang}\n{code.strip()}\n```\n")

    # Add new install commands
    new_installs = research_data.get("installation", [])
    if new_installs:
        if isinstance(new_installs, list):
            install_lines = ["### Updated Installation"]
            for inst in new_installs:
                if isinstance(inst, dict):
                    mgr = inst.get("package_manager", "")
                    cmd = inst.get("command", "")
                    install_lines.append(f"\n**{mgr}**:\n\n```bash\n{cmd}\n```")
                elif isinstance(inst, str) and inst.strip():
                    install_lines.append(f"\n```bash\n{inst}\n```")
            install_lines.append("")
            new_snippets.append("\n".join(install_lines))

    # Add gotchas
    gotchas = research_data.get("gotchas", [])
    if gotchas:
        gotcha_lines = ["### New Gotchas"]
        for g in gotchas:
            gotcha_lines.append(f"- {g}")
        gotcha_lines.append("")
        new_snippets.append("\n".join(gotcha_lines))

    if not new_snippets:
        return existing  # Nothing to merge

    # Build the merged content
    # Find if there is already a "Research Updates" section
    updates_header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## ") and "update" in stripped.lower():
            updates_header_idx = i
            break

    merged_lines = list(lines)

    description = research_data.get("description", "")
    updates_section = [
        "",
        "## Research Updates",
        "",
        f"_Updated from research on: {query}_",
        "",
    ]
    if description:
        updates_section.extend([description, ""])

    for snippet in new_snippets:
        updates_section.append(snippet)

    if updates_header_idx is not None:
        # Replace existing updates section -- find the next H2 or end of file
        next_h2_idx = None
        for i in range(updates_header_idx + 1, len(merged_lines)):
            if merged_lines[i].strip().startswith("## "):
                next_h2_idx = i
                break
        if next_h2_idx is not None:
            merged_lines = (
                merged_lines[:updates_header_idx]
                + updates_section
                + merged_lines[next_h2_idx:]
            )
        else:
            merged_lines = merged_lines[:updates_header_idx] + updates_section
    else:
        # Append at the end
        merged_lines.extend(updates_section)

    return "\n".join(merged_lines)


def show_diff(old: str, new: str, filepath: str) -> None:
    """Display a unified diff between old and new content."""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{Path(filepath).name}",
        tofile=f"b/{Path(filepath).name}",
        lineterm="",
    ))

    if not diff:
        console.print("[dim]No changes detected.[/dim]")
        return

    diff_text = "\n".join(diff)
    console.print(
        Panel(
            Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
            title="Changes",
            border_style="cyan",
        )
    )

    # Count additions and removals
    additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removals = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    console.print(f"  [green]+{additions}[/green] additions, [red]-{removals}[/red] removals")


async def run_research(args: argparse.Namespace) -> dict[str, Any]:
    """Execute the research phase using the existing SkillResearcher."""
    llm = _build_llm(args.llm)
    researcher = SkillResearcher(
        llm=llm,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        headed=args.headed,
    )
    return await researcher.research(topic=args.query, url=args.url)


async def main() -> int:
    args = parse_args()

    skill_path = Path(args.skill).resolve()
    query_display = args.query or args.url or "unknown"

    console.print(
        Panel(
            f"[bold]Skill Evolve[/bold]\n\n"
            f"Skill:    {skill_path}\n"
            f"Query:    {query_display}\n"
            f"LLM:      {args.llm}\n"
            f"Dry run:  {args.dry_run}",
            title="Configuration",
            border_style="blue",
        )
    )
    console.print()

    # Read existing skill
    existing_content = read_existing_skill(str(skill_path))
    console.print(f"[dim]Read existing skill: {len(existing_content)} characters, "
                  f"{len(existing_content.splitlines())} lines[/dim]")
    console.print()

    # ---- Research ----
    console.rule("[bold cyan]Phase 1: Research[/bold cyan]")
    console.print()

    research_data: dict[str, Any] | None = None
    t0 = time.monotonic()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Researching...", total=None)
        try:
            research_data = await run_research(args)
            progress.update(task, description="[green]Research complete")
        except Exception as exc:
            progress.update(task, description="[red]Research failed")
            console.print()
            console.print(f"[bold red]Error during research:[/bold red] {exc}")
            return 1

    elapsed = time.monotonic() - t0

    num_commands = len(research_data.get("commands", []))
    num_examples = len(research_data.get("examples", []))
    console.print()
    console.print(
        f"  Commands: {num_commands}  |  "
        f"Examples: {num_examples}  |  "
        f"Time: {elapsed:.1f}s"
    )
    console.print()

    if not research_data.get("commands") and not research_data.get("examples") and not research_data.get("gotchas"):
        console.print("[yellow]No new findings to merge. Skill unchanged.[/yellow]")
        return 0

    # ---- Merge ----
    console.rule("[bold cyan]Phase 2: Merge[/bold cyan]")
    console.print()

    merged_content = merge_content(existing_content, research_data, query_display)

    # Show diff
    show_diff(existing_content, merged_content, str(skill_path))
    console.print()

    # Write or dry-run
    if args.dry_run:
        console.print("[bold yellow]Dry run -- no changes written.[/bold yellow]")
    else:
        # Write backup
        backup_path = skill_path.with_suffix(".md.bak")
        backup_path.write_text(existing_content, encoding="utf-8")
        console.print(f"[dim]Backup saved: {backup_path}[/dim]")

        # Write merged content
        skill_path.write_text(merged_content, encoding="utf-8")
        console.print(f"[bold green]Updated:[/bold green] {skill_path}")

    console.print()
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
