#!/usr/bin/env python3
"""Initialize a blank skill scaffold with the standard directory structure."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from rich.console import Console
from rich.tree import Tree

from skill_gen.core.generator import SkillGenerator


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize a blank skill scaffold.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s --name docker-compose
  %(prog)s --name fastapi --template api --output ./my-skills/fastapi/
""",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Name of the skill (used as slug, e.g. 'docker-compose')",
    )
    parser.add_argument(
        "--template",
        type=str,
        default="basic",
        choices=["basic", "browser", "api", "cli", "composite"],
        help="Template to use for the SKILL.md scaffold (default: basic)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: ./skills/{name}/)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    slug = args.name.lower().replace(" ", "-").replace("_", "-")
    display_name = args.name.replace("-", " ").replace("_", " ").title()

    # Determine output directory
    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        output_dir = (Path.cwd() / "skills" / slug).resolve()

    # Check if already exists
    if output_dir.exists() and any(output_dir.iterdir()):
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Directory already exists and is not empty: {output_dir}"
        )
        console.print("Continuing will overwrite SKILL.md if present.")
        console.print()

    # Use the existing SkillGenerator.generate_from_template method
    generator = SkillGenerator(template=args.template)
    skill_path = generator.generate_from_template(
        name=display_name,
        template=args.template,
        output_dir=str(output_dir),
    )

    # Ensure assets/ directory also exists (generate_from_template creates scripts/)
    (output_dir / "assets").mkdir(exist_ok=True)

    # Display what was created
    console.print()
    console.print(f"[bold green]Skill scaffold created:[/bold green] {slug}")
    console.print()

    tree = Tree(f"[bold]{output_dir}[/bold]")
    tree.add("[green]SKILL.md[/green]  (template: {})".format(args.template))
    tree.add("[dim]scripts/[/dim]")
    tree.add("[dim]assets/[/dim]")
    console.print(tree)
    console.print()

    console.print(f"[dim]Edit {skill_path} to fill in your skill content.[/dim]")
    console.print(
        f"[dim]Validate with: python scripts/validate.py {skill_path}[/dim]"
    )
    console.print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
