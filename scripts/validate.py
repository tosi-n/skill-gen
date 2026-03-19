#!/usr/bin/env python3
"""Validate a SKILL.md file for correctness and completeness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from skill_gen.core.validator import SkillValidator, Severity, ValidationResult


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a SKILL.md file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s ./skills/docker-compose/SKILL.md
  %(prog)s --verbose ./skills/fastapi/SKILL.md
""",
    )
    parser.add_argument(
        "path",
        type=str,
        help="Path to the SKILL.md file to validate",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all issues including informational messages",
    )
    return parser.parse_args()


def display_result(result: ValidationResult, verbose: bool = False) -> None:
    """Display validation results with rich formatting."""
    # Header
    filepath = result.file_path or "(unknown)"
    console.print()
    console.print(
        Panel(
            f"[bold]Validating:[/bold] {filepath}",
            border_style="blue",
        )
    )
    console.print()

    # Metadata
    if result.line_count > 0:
        console.print(f"Lines: {result.line_count}")
        console.print()

    # Determine which issues to show
    issues_to_show = result.issues
    if not verbose:
        issues_to_show = [i for i in result.issues if i.severity != Severity.INFO]

    if issues_to_show:
        table = Table(show_header=True, header_style="bold", show_lines=False, pad_edge=True)
        table.add_column("", width=4, justify="center")
        table.add_column("Check", min_width=40)
        table.add_column("Suggestion", style="dim", min_width=30)

        for issue in issues_to_show:
            if issue.severity == Severity.ERROR:
                icon = "[bold red]X[/bold red]"
                msg_style = "red"
            elif issue.severity == Severity.WARNING:
                icon = "[bold yellow]![/bold yellow]"
                msg_style = "yellow"
            else:
                icon = "[bold green]i[/bold green]"
                msg_style = "dim"

            line_info = f" (line {issue.line})" if issue.line else ""
            table.add_row(
                icon,
                f"[{msg_style}]{issue.message}{line_info}[/{msg_style}]",
                issue.suggestion or "",
            )

        console.print(table)
    else:
        console.print("[dim]No issues to display.[/dim]")

    console.print()

    # Summary
    err_count = len(result.errors)
    warn_count = len(result.warnings)
    info_count = len([i for i in result.issues if i.severity == Severity.INFO])

    if result.valid and warn_count == 0:
        console.print(
            f"[bold green]PASSED[/bold green]  "
            f"{err_count} error(s), {warn_count} warning(s), {info_count} info(s)"
        )
    elif result.valid:
        console.print(
            f"[bold yellow]PASSED with warnings[/bold yellow]  "
            f"{err_count} error(s), {warn_count} warning(s), {info_count} info(s)"
        )
    else:
        console.print(
            f"[bold red]FAILED[/bold red]  "
            f"{err_count} error(s), {warn_count} warning(s), {info_count} info(s)"
        )

    console.print()


def main() -> int:
    args = parse_args()

    # Resolve path
    skill_path = Path(args.path)
    if not skill_path.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {skill_path}")
        return 1

    validator = SkillValidator()
    result = validator.validate(str(skill_path))

    display_result(result, verbose=args.verbose)

    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
