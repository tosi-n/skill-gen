"""
skill-gen CLI.

Provides commands for generating, validating, and evolving SKILL.md
files using autonomous browser-based research.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from skill_gen.core.generator import SkillGenerator
from skill_gen.core.researcher import SkillResearcher
from skill_gen.core.validator import SkillValidator, Severity

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_llm(llm_name: str):
    """Instantiate an LLM by short name.

    Supports:
        - ``openai`` / ``gpt-4o``  -> ChatOpenAI (requires OPENAI_API_KEY)
        - ``anthropic`` / ``claude`` -> ChatAnthropic (requires ANTHROPIC_API_KEY)

    Returns a langchain chat model instance.
    """
    name = llm_name.lower().strip()

    if name in ("openai", "gpt-4o", "gpt4o", "gpt-4", "gpt4"):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            console.print(
                "[red]langchain-openai is required. "
                "Install it with: pip install langchain-openai[/red]"
            )
            raise SystemExit(1)
        return ChatOpenAI(model="gpt-4o")

    if name in ("anthropic", "claude", "claude-sonnet", "sonnet"):
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            console.print(
                "[red]langchain-anthropic is required. "
                "Install it with: pip install langchain-anthropic[/red]"
            )
            raise SystemExit(1)
        return ChatAnthropic(model="claude-sonnet-4-20250514")

    # Fallback: try openai with model name as-is
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=name)
    except Exception as exc:
        console.print(f"[red]Could not initialise LLM '{llm_name}': {exc}[/red]")
        raise SystemExit(1)


def _run_async(coro):
    """Run an async coroutine from synchronous Click code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside an event loop (e.g. Jupyter).  Create a new thread.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="skill-gen")
def cli():
    """skill-gen -- Autonomous skill file generator."""


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

@cli.command()
def doctor():
    """Check that skill-gen and all prerequisites are installed correctly."""
    import shutil

    all_ok = True

    # 1. Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 11):
        console.print(f"  [green]OK[/green]  Python {py_ver}")
    else:
        console.print(f"  [red]FAIL[/red]  Python {py_ver} (need >=3.11)")
        all_ok = False

    # 2. browser-use
    try:
        import browser_use  # noqa: F401
        console.print(f"  [green]OK[/green]  browser-use installed")
    except ImportError:
        console.print("  [red]FAIL[/red]  browser-use not installed")
        console.print("        [dim]pip install git+https://github.com/tosi-n/skill-gen.git[/dim]")
        all_ok = False

    # 3. playwright
    try:
        import playwright  # noqa: F401
        console.print(f"  [green]OK[/green]  playwright installed")
    except ImportError:
        console.print("  [red]FAIL[/red]  playwright not installed")
        console.print("        [dim]pip install playwright[/dim]")
        all_ok = False

    # 4. chromium binary
    pw_bin = shutil.which("playwright")
    if pw_bin:
        import subprocess
        result = subprocess.run(
            ["playwright", "install", "--dry-run", "chromium"],
            capture_output=True, text=True,
        )
        # If dry-run exits 0 or mentions "already installed", we're good
        if result.returncode == 0 or "already" in result.stdout.lower():
            console.print(f"  [green]OK[/green]  Chromium browser available")
        else:
            console.print("  [yellow]WARN[/yellow]  Chromium may not be installed")
            console.print("        [dim]playwright install chromium[/dim]")
            all_ok = False
    else:
        console.print("  [yellow]WARN[/yellow]  Cannot verify Chromium (playwright CLI not in PATH)")
        console.print("        [dim]playwright install chromium[/dim]")

    # 5. browser-use CLI
    bu_bin = shutil.which("browser-use")
    if bu_bin:
        console.print(f"  [green]OK[/green]  browser-use CLI available")
    else:
        console.print("  [yellow]WARN[/yellow]  browser-use CLI not in PATH")
        console.print("        [dim]pip install git+https://github.com/tosi-n/skill-gen.git[/dim]")

    # 6. skill-gen itself
    console.print(f"  [green]OK[/green]  skill-gen CLI working")

    console.print()
    if all_ok:
        console.print("[bold green]All checks passed. skill-gen is ready.[/bold green]")
    else:
        console.print("[bold yellow]Some checks failed. Fix the issues above, then re-run: skill-gen doctor[/bold yellow]")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# forge
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--topic", "-t", type=str, default=None, help="Topic to research (e.g. 'browser-use').")
@click.option("--url", "-u", type=str, default=None, help="Starting URL for research.")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory.")
@click.option(
    "--template",
    type=click.Choice(["basic", "browser", "api", "cli", "composite"], case_sensitive=False),
    default="basic",
    help="Skill template to use.",
)
@click.option("--llm", type=str, default="openai", help="LLM backend (openai, anthropic, or model name).")
@click.option("--max-depth", type=int, default=3, help="Max link-follow depth.")
@click.option("--max-pages", type=int, default=10, help="Max pages to visit.")
def forge(
    topic: str | None,
    url: str | None,
    output: str,
    template: str,
    llm: str,
    max_depth: int,
    max_pages: int,
):
    """Generate a SKILL.md by researching a topic or URL.

    Orchestrates the full pipeline: research -> extract -> synthesize -> validate -> write.
    """
    if not topic and not url:
        console.print("[red]Provide at least --topic or --url.[/red]")
        raise SystemExit(1)

    label = topic or url or ""
    console.print(Panel(f"[bold]Forging skill:[/bold] {label}", style="cyan"))

    async def _forge():
        # Step 1: Research
        with console.status("[bold green]Researching..."):
            llm_instance = _get_llm(llm)
            researcher = SkillResearcher(
                llm=llm_instance,
                max_depth=max_depth,
                max_pages=max_pages,
            )
            research_data = await researcher.research(topic=topic, url=url)

        console.print("[green]Research complete.[/green]")
        _print_research_summary(research_data)

        # Step 2: Generate
        with console.status("[bold green]Generating skill file..."):
            generator = SkillGenerator(template=template)
            skill_path = await generator.generate(research_data, output)

        console.print(f"[green]Skill written to:[/green] {skill_path}")

        # Step 3: Validate
        validator = SkillValidator()
        result = validator.validate(skill_path)
        _print_validation(result)

        return skill_path

    _run_async(_forge())


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--name", "-n", required=True, type=str, help="Skill name.")
@click.option(
    "--template",
    type=click.Choice(["basic", "browser", "api", "cli", "composite"], case_sensitive=False),
    default="basic",
    help="Skill template.",
)
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory.")
def init(name: str, template: str, output: str):
    """Initialize a blank skill scaffold."""
    console.print(Panel(f"[bold]Initializing skill:[/bold] {name}", style="cyan"))

    generator = SkillGenerator(template=template)
    path = generator.generate_from_template(name=name, template=template, output_dir=output)

    console.print(f"[green]Scaffold created at:[/green] {path}")
    console.print("Edit the generated SKILL.md to fill in the details.")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("path", type=click.Path(exists=True))
def validate(path: str):
    """Validate an existing SKILL.md file."""
    console.print(Panel(f"[bold]Validating:[/bold] {path}", style="cyan"))

    validator = SkillValidator()
    result = validator.validate(path)
    _print_validation(result)

    if not result.valid:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# evolve
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--skill", "-s", required=True, type=click.Path(exists=True), help="Path to existing SKILL.md.")
@click.option("--query", "-q", type=str, default=None, help="What to improve or add.")
@click.option("--url", "-u", type=str, default=None, help="Additional URL to research.")
@click.option("--llm", type=str, default="openai", help="LLM backend.")
@click.option("--max-depth", type=int, default=2, help="Max link-follow depth for additional research.")
@click.option("--max-pages", type=int, default=5, help="Max pages to visit.")
def evolve(
    skill: str,
    query: str | None,
    url: str | None,
    llm: str,
    max_depth: int,
    max_pages: int,
):
    """Improve an existing skill with additional research.

    Reads the current SKILL.md, optionally researches a URL for new data,
    and regenerates an improved version.
    """
    if not query and not url:
        console.print("[red]Provide at least --query or --url.[/red]")
        raise SystemExit(1)

    console.print(Panel(f"[bold]Evolving skill:[/bold] {skill}", style="cyan"))

    skill_path = Path(skill)
    existing_content = skill_path.read_text(encoding="utf-8")

    async def _evolve():
        additional_data: dict = {}

        # If a URL is provided, run a focused research pass
        if url:
            with console.status("[bold green]Researching additional source..."):
                llm_instance = _get_llm(llm)
                researcher = SkillResearcher(
                    llm=llm_instance,
                    max_depth=max_depth,
                    max_pages=max_pages,
                )
                additional_data = await researcher.research(url=url, topic=query)
            console.print("[green]Additional research complete.[/green]")

        # Merge: use the LLM to synthesize the improvement
        with console.status("[bold green]Synthesizing improvements..."):
            llm_instance = _get_llm(llm)
            improved = await _synthesize_evolution(
                llm_instance, existing_content, query, additional_data
            )

        # Write the improved skill
        output_dir = str(skill_path.parent)
        backup_path = skill_path.with_suffix(".md.bak")
        backup_path.write_text(existing_content, encoding="utf-8")
        console.print(f"[dim]Backup saved to {backup_path}[/dim]")

        skill_path.write_text(improved, encoding="utf-8")
        console.print(f"[green]Skill updated:[/green] {skill_path}")

        # Validate
        validator = SkillValidator()
        result = validator.validate(str(skill_path))
        _print_validation(result)

    _run_async(_evolve())


async def _synthesize_evolution(
    llm,
    existing_content: str,
    query: str | None,
    additional_data: dict,
) -> str:
    """Use the LLM to merge existing skill content with new research."""
    from skill_gen.utils.markdown import truncate_to_lines

    additional_json = json.dumps(additional_data, indent=2) if additional_data else "No additional data."
    query_text = query or "Improve the skill generally: add missing sections, fix errors, enrich examples."

    prompt = (
        "You are a technical writer specialising in SKILL.md files for AI agents.\n\n"
        "Below is the current SKILL.md content:\n"
        "```markdown\n"
        f"{existing_content}\n"
        "```\n\n"
        "The user wants to evolve this skill. Their request:\n"
        f"{query_text}\n\n"
        "Additional research data (if any):\n"
        f"```json\n{additional_json}\n```\n\n"
        "Produce an improved SKILL.md that:\n"
        "1. Keeps the YAML frontmatter with name, description, and allowed-tools.\n"
        "2. Incorporates the new information from the research data.\n"
        "3. Addresses the user's query.\n"
        "4. Stays under 500 lines.\n"
        "5. Retains existing good content.\n\n"
        "Return ONLY the full Markdown content of the improved SKILL.md, nothing else."
    )

    response = await llm.ainvoke(prompt)
    improved = response.content if hasattr(response, "content") else str(response)

    # Strip any wrapping code fences the LLM might add
    if improved.startswith("```markdown"):
        improved = improved[len("```markdown"):].strip()
    if improved.startswith("```"):
        improved = improved[3:].strip()
    if improved.endswith("```"):
        improved = improved[:-3].strip()

    return truncate_to_lines(improved, max_lines=500)


# ---------------------------------------------------------------------------
# from-url
# ---------------------------------------------------------------------------

@cli.command("from-url")
@click.argument("urls", nargs=-1, required=True)
@click.option("--name", "-n", type=str, default=None, help="Skill name (auto-detected if omitted).")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory.")
@click.option(
    "--template",
    type=click.Choice(["basic", "browser", "api", "cli", "composite"], case_sensitive=False),
    default="basic",
    help="Skill template.",
)
@click.option("--llm", type=str, default="claude", help="LLM backend (openai, anthropic, or model name).")
@click.option("--headed", is_flag=True, default=False, help="Show browser window.")
def from_url(
    urls: tuple[str, ...],
    name: str | None,
    output: str,
    template: str,
    llm: str,
    headed: bool,
):
    """Generate a skill directly from one or more URLs.

    Pass blog posts, tutorials, documentation pages, or GitHub READMEs.
    skill-gen will browse each URL, extract the content, and synthesize
    a skill from the combined findings.

    \b
    Examples:
      skill-gen from-url https://blog.example.com/intro-to-fastapi -o ./skills/fastapi/
      skill-gen from-url https://docs.tool.dev/guide https://docs.tool.dev/api -n my-tool
      skill-gen from-url https://github.com/org/repo --template cli
    """
    url_list = list(urls)
    console.print(Panel(
        f"[bold]Generating skill from {len(url_list)} URL(s)[/bold]\n"
        + "\n".join(f"  {u}" for u in url_list),
        style="cyan",
    ))

    async def _from_url():
        llm_instance = _get_llm(llm)

        # Research each URL with a focused single-page extraction
        all_research: list[dict] = []
        for i, url in enumerate(url_list, 1):
            with console.status(f"[bold green]Reading URL {i}/{len(url_list)}: {url}"):
                researcher = SkillResearcher(
                    llm=llm_instance,
                    max_depth=1,
                    max_pages=2,
                    headed=headed,
                )
                data = await researcher.research_url(url)
                all_research.append(data)
            console.print(f"  [green]Done:[/green] {url}")

        # Merge all research into one dataset
        merged = _merge_research_data(all_research, name=name)
        _print_research_summary(merged)

        # Generate
        with console.status("[bold green]Generating skill file..."):
            generator = SkillGenerator(template=template)
            skill_path = await generator.generate(merged, output)

        console.print(f"[green]Skill written to:[/green] {skill_path}")

        # Validate
        validator = SkillValidator()
        result = validator.validate(skill_path)
        _print_validation(result)

        return skill_path

    _run_async(_from_url())


def _merge_research_data(datasets: list[dict], name: str | None = None) -> dict:
    """Merge multiple research data dicts into one combined dataset."""
    if not datasets:
        return {}
    if len(datasets) == 1 and not name:
        return datasets[0]

    merged = {
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

    descriptions = []
    for d in datasets:
        desc = d.get("description", "")
        if desc:
            descriptions.append(desc)
        for key in ("installation", "commands", "workflows", "configuration",
                     "examples", "gotchas", "allowed_tools", "source_urls"):
            existing = d.get(key, [])
            if isinstance(existing, list):
                merged[key].extend(existing)

    # Pick the longest description or combine them
    if descriptions:
        merged["description"] = max(descriptions, key=len)

    return merged


# ---------------------------------------------------------------------------
# research
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--topic", "-t", type=str, default=None, help="Topic to research.")
@click.option("--url", "-u", type=str, default=None, help="Starting URL.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output JSON file path.")
@click.option("--llm", type=str, default="openai", help="LLM backend.")
@click.option("--max-depth", type=int, default=3, help="Max link-follow depth.")
@click.option("--max-pages", type=int, default=10, help="Max pages to visit.")
def research(
    topic: str | None,
    url: str | None,
    output: str | None,
    llm: str,
    max_depth: int,
    max_pages: int,
):
    """Run the research phase and output findings as JSON."""
    if not topic and not url:
        console.print("[red]Provide at least --topic or --url.[/red]")
        raise SystemExit(1)

    label = topic or url or ""
    console.print(Panel(f"[bold]Researching:[/bold] {label}", style="cyan"))

    async def _research():
        with console.status("[bold green]Researching..."):
            llm_instance = _get_llm(llm)
            researcher = SkillResearcher(
                llm=llm_instance,
                max_depth=max_depth,
                max_pages=max_pages,
            )
            data = await researcher.research(topic=topic, url=url)

        _print_research_summary(data)

        # Write output
        json_text = json.dumps(data, indent=2, ensure_ascii=False)
        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json_text, encoding="utf-8")
            console.print(f"[green]Research data written to:[/green] {out_path}")
        else:
            console.print("\n[bold]Raw research data:[/bold]")
            console.print(json_text)

    _run_async(_research())


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------

def _print_research_summary(data: dict) -> None:
    """Display a concise summary of research findings."""
    tbl = Table(title="Research Summary", show_lines=True)
    tbl.add_column("Field", style="bold")
    tbl.add_column("Value")

    tbl.add_row("Name", data.get("name", ""))
    tbl.add_row("Description", (data.get("description") or "")[:120])
    tbl.add_row("Install commands", str(len(data.get("installation", []))))
    tbl.add_row("Commands / API", str(len(data.get("commands", []))))
    tbl.add_row("Code examples", str(len(data.get("examples", []))))
    tbl.add_row("Workflows", str(len(data.get("workflows", []))))
    tbl.add_row("Config entries", str(len(data.get("configuration", []))))
    tbl.add_row("Tips / gotchas", str(len(data.get("gotchas", []))))

    console.print(tbl)


def _print_validation(result) -> None:
    """Display validation results with colours."""
    if result.valid:
        console.print(f"[green bold]{result.summary()}[/green bold]")
    else:
        console.print(f"[red bold]{result.summary()}[/red bold]")

    for issue in result.issues:
        if issue.severity == Severity.ERROR:
            icon = "[red]ERROR[/red]"
        elif issue.severity == Severity.WARNING:
            icon = "[yellow]WARN [/yellow]"
        else:
            icon = "[dim]INFO [/dim]"

        line_info = f" (line {issue.line})" if issue.line else ""
        console.print(f"  {icon} {issue.message}{line_info}")
        if issue.suggestion:
            console.print(f"         [dim]-> {issue.suggestion}[/dim]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Package entry point."""
    cli()


if __name__ == "__main__":
    main()
