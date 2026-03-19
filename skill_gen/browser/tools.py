"""
Custom browser-use action tools for autonomous research sessions.

These tools are injected into a browser-use Agent so the LLM can
persist structured research findings during browsing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchFindings:
    """Accumulator for data extracted during a research session.

    Tools write into this object; the researcher reads it back when the
    agent finishes.
    """

    overview: str = ""
    structured_data: list[dict[str, Any]] = field(default_factory=list)
    code_examples: list[dict[str, str]] = field(default_factory=list)
    install_commands: list[dict[str, str]] = field(default_factory=list)
    commands: list[dict[str, str]] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overview": self.overview,
            "structured_data": self.structured_data,
            "code_examples": self.code_examples,
            "install_commands": self.install_commands,
            "commands": self.commands,
            "links": self.links,
        }


def create_research_tools(findings: ResearchFindings | None = None):
    """Build a list of controller action callables backed by *findings*.

    The returned list is suitable for passing to a browser-use ``Agent``
    via its ``controller`` parameter.  Each callable is decorated so
    browser-use's controller can discover it.

    If *findings* is ``None`` a fresh :class:`ResearchFindings` instance
    is created internally and returned alongside the tools.

    Returns:
        Tuple of ``(actions_list, findings)``.
    """
    from browser_use import Controller

    if findings is None:
        findings = ResearchFindings()

    controller = Controller()

    # ------------------------------------------------------------------
    # Action: extract_structured_data
    # ------------------------------------------------------------------
    @controller.action(
        description=(
            "Extract structured data from the current page. "
            "Provide a JSON string with relevant key-value pairs you found."
        ),
    )
    def extract_structured_data(data_json: str) -> str:
        """Persist a free-form JSON blob extracted from the page."""
        try:
            parsed = json.loads(data_json)
        except json.JSONDecodeError:
            parsed = {"raw": data_json}
        findings.structured_data.append(parsed)
        return f"Saved structured data ({len(findings.structured_data)} total entries)."

    # ------------------------------------------------------------------
    # Action: save_code_example
    # ------------------------------------------------------------------
    @controller.action(
        description=(
            "Save a code example found on the page. "
            "Provide the programming language, the code itself, and a short description."
        ),
    )
    def save_code_example(language: str, code: str, description: str) -> str:
        """Persist a code snippet."""
        findings.code_examples.append({
            "language": language,
            "code": code,
            "description": description,
        })
        return f"Saved code example: {description!r} ({len(findings.code_examples)} total)."

    # ------------------------------------------------------------------
    # Action: record_install_command
    # ------------------------------------------------------------------
    @controller.action(
        description=(
            "Record an installation command for the tool being researched. "
            "Provide the command text and the package manager name (pip, npm, brew, etc.)."
        ),
    )
    def record_install_command(command: str, package_manager: str) -> str:
        """Persist an install command."""
        findings.install_commands.append({
            "command": command,
            "package_manager": package_manager,
        })
        return f"Recorded install command: {command!r} ({package_manager})."

    # ------------------------------------------------------------------
    # Action: record_command
    # ------------------------------------------------------------------
    @controller.action(
        description=(
            "Record a CLI command or API method provided by the tool. "
            "Provide the name, the full syntax, and a description of what it does."
        ),
    )
    def record_command(name: str, syntax: str, description: str) -> str:
        """Persist a command or API method reference."""
        findings.commands.append({
            "name": name,
            "syntax": syntax,
            "description": description,
        })
        return f"Recorded command: {name!r} ({len(findings.commands)} total)."

    # ------------------------------------------------------------------
    # Action: record_doc_link
    # ------------------------------------------------------------------
    @controller.action(
        description=(
            "Record a documentation or reference link found on the page. "
            "Provide the URL and a short label describing the link."
        ),
    )
    def record_doc_link(url: str, label: str) -> str:
        """Persist a documentation link for follow-up."""
        findings.links.append({"url": url, "label": label})
        return f"Recorded link: {label!r} -> {url}"

    # ------------------------------------------------------------------
    # Action: set_overview
    # ------------------------------------------------------------------
    @controller.action(
        description=(
            "Set the high-level overview / description of the tool being researched. "
            "Provide a concise paragraph summarising what the tool is and does."
        ),
    )
    def set_overview(text: str) -> str:
        """Persist the tool overview."""
        findings.overview = text
        return "Overview saved."

    # ------------------------------------------------------------------
    # Action: extract_article_content
    # ------------------------------------------------------------------
    @controller.action(
        description=(
            "Extract the main article/blog content from the current page. "
            "Provide the title, author (if visible), and the full body text. "
            "Strip navigation, ads, footers. Focus on the core content."
        ),
    )
    def extract_article_content(title: str, body: str, author: str = "") -> str:
        """Persist extracted article content."""
        findings.structured_data.append({
            "type": "article",
            "title": title,
            "author": author,
            "body": body,
        })
        return f"Extracted article: {title!r}"

    # ------------------------------------------------------------------
    # Action: extract_tutorial_steps
    # ------------------------------------------------------------------
    @controller.action(
        description=(
            "Extract step-by-step tutorial/guide content from the page. "
            "Provide a JSON array of steps, each with 'title' and 'content' keys."
        ),
    )
    def extract_tutorial_steps(steps_json: str) -> str:
        """Persist tutorial steps extracted from a guide or blog post."""
        try:
            steps = json.loads(steps_json)
        except json.JSONDecodeError:
            steps = [{"title": "Step", "content": steps_json}]
        findings.structured_data.append({
            "type": "tutorial",
            "steps": steps,
        })
        return f"Extracted {len(steps)} tutorial steps."

    # ------------------------------------------------------------------
    # Action: extract_key_concepts
    # ------------------------------------------------------------------
    @controller.action(
        description=(
            "Extract key concepts, terms, or definitions from the page. "
            "Provide a JSON object mapping concept names to their descriptions."
        ),
    )
    def extract_key_concepts(concepts_json: str) -> str:
        """Persist key concepts from the page."""
        try:
            concepts = json.loads(concepts_json)
        except json.JSONDecodeError:
            concepts = {"raw": concepts_json}
        findings.structured_data.append({
            "type": "concepts",
            "concepts": concepts,
        })
        return f"Extracted {len(concepts)} key concepts."

    return controller, findings
