"""
Autonomous research engine.

Uses browser-use to navigate documentation sites, GitHub repos, and
API references, extracting structured data for skill generation.

All browser-use dependent imports are deferred so this module can be
imported without browser-use being installed.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from skill_gen.browser.session import ResearchSession
    from skill_gen.browser.tools import ResearchFindings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def _build_llm(provider: str = "claude") -> Any:
    """Build a LangChain chat model for the given provider.

    This is a convenience function used by the CLI scripts to construct
    the LLM instance that :class:`SkillResearcher` requires.

    Args:
        provider: One of ``claude``, ``gemini``, or ``openai``.

    Returns:
        A LangChain chat model instance.

    Raises:
        EnvironmentError: If the required API key is not set.
        ValueError: If the provider name is unrecognised.
    """
    provider = provider.lower().strip()

    if provider in ("claude", "anthropic"):
        from langchain_anthropic import ChatAnthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Export it or add it to your .env file."
            )
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            temperature=0,
        )
    elif provider in ("gemini", "google"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "GOOGLE_API_KEY is not set. "
                "Export it or add it to your .env file."
            )
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0,
        )
    elif provider in ("openai", "gpt"):
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Export it or add it to your .env file."
            )
        return ChatOpenAI(
            model="gpt-4o",
            api_key=api_key,
            temperature=0,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider!r}. Use claude, gemini, or openai."
        )


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class CommandInfo(BaseModel):
    name: str = ""
    syntax: str = ""
    description: str = ""


class CodeExample(BaseModel):
    language: str = "bash"
    code: str = ""
    description: str = ""


class InstallInfo(BaseModel):
    command: str = ""
    package_manager: str = "pip"


class WorkflowStep(BaseModel):
    title: str = ""
    description: str = ""


class ResearchData(BaseModel):
    """Structured output from a research session."""
    name: str = ""
    description: str = ""
    installation: list[InstallInfo] = Field(default_factory=list)
    commands: list[CommandInfo] = Field(default_factory=list)
    workflows: list[WorkflowStep] = Field(default_factory=list)
    configuration: list[dict[str, str]] = Field(default_factory=list)
    examples: list[CodeExample] = Field(default_factory=list)
    gotchas: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


# ---------------------------------------------------------------------------
# Researcher
# ---------------------------------------------------------------------------

class SkillResearcher:
    """Uses browser-use to autonomously research a tool or library.

    Args:
        llm: Language model instance for the browser-use agent.
        max_depth: Maximum number of follow-up link levels to pursue.
        max_pages: Maximum total pages to visit during research.
        headed: Show the browser window (useful for debugging).
    """

    def __init__(
        self,
        llm: Any = None,
        max_depth: int = 3,
        max_pages: int = 10,
        headed: bool = False,
    ) -> None:
        self.llm = llm
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.headed = headed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def research(
        self,
        topic: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        """Research a topic or URL and return structured findings.

        At least one of *topic* or *url* must be provided.  If both are
        given, the URL is used as the starting point and the topic is
        included in the agent prompt for context.

        Args:
            topic: Free-text topic to research (e.g. ``"browser-use"``).
            url: A starting URL (e.g. a GitHub repo or docs site).

        Returns:
            A dictionary conforming to :class:`ResearchData`.
        """
        if not topic and not url:
            raise ValueError("Provide at least one of 'topic' or 'url'.")

        if self.llm is None:
            raise RuntimeError(
                "No LLM configured for the researcher. "
                "Pass an LLM instance (e.g. ChatOpenAI) to SkillResearcher(llm=...)."
            )

        from skill_gen.browser.session import ResearchSession
        from skill_gen.browser.tools import ResearchFindings

        session = ResearchSession(headed=self.headed)

        try:
            await session.start()

            # Phase 1: If no URL, search for the topic first
            if not url:
                url = await self._search_for_topic(session, topic)  # type: ignore[arg-type]

            # Phase 2: Main research pass -- browse and extract
            findings = await self._run_research_agent(
                session, topic=topic or "", url=url or ""
            )

            # Phase 3: Follow interesting links for deeper data
            if findings and len(findings.links) > 0:
                findings = await self._follow_links(session, findings, topic or "")

            # Phase 4: Aggregate into ResearchData
            return self._aggregate(findings, url=url or "", topic=topic or "")

        finally:
            await session.close()

    async def research_url(self, url: str) -> dict[str, Any]:
        """Focused single-page research for a blog post, tutorial, or doc page.

        Unlike :meth:`research`, this method is optimised for extracting
        content from a *single* URL (or at most one follow-up link).  It
        uses a specialised prompt that asks the agent to treat the page as
        an article/tutorial and extract its content holistically.

        Args:
            url: The URL to extract content from.

        Returns:
            A dictionary conforming to :class:`ResearchData`.
        """
        if self.llm is None:
            raise RuntimeError(
                "No LLM configured. Pass an LLM to SkillResearcher(llm=...)."
            )

        from skill_gen.browser.session import ResearchSession
        from skill_gen.browser.tools import ResearchFindings

        session = ResearchSession(headed=self.headed)

        try:
            await session.start()

            task = self._build_page_extraction_task(url)
            agent, findings = await session.create_agent(
                task=task,
                llm=self.llm,
                max_steps=30,
            )
            await agent.run()
            return self._aggregate(findings or ResearchFindings(), url=url, topic="")

        finally:
            await session.close()

    def _build_page_extraction_task(self, url: str) -> str:
        """Build a prompt optimised for single-page content extraction."""
        return (
            f"You are reading a web page to extract information for creating a skill file.\n"
            f"URL: {url}\n\n"
            f"Navigate to the URL and carefully read the full page content.\n"
            f"This could be a blog post, tutorial, documentation page, or GitHub README.\n\n"
            f"Extract ALL of the following:\n"
            f"1. Use set_overview to describe what this page/tool is about.\n"
            f"2. Use extract_article_content to capture the main content (title, body, author).\n"
            f"3. Use save_code_example for EVERY code block or snippet you find.\n"
            f"4. Use record_install_command for any installation/setup instructions.\n"
            f"5. Use record_command for any CLI commands or API methods described.\n"
            f"6. Use extract_tutorial_steps if the content is a step-by-step guide.\n"
            f"7. Use extract_key_concepts for any important terms or definitions.\n"
            f"8. Use record_doc_link for any important links referenced in the content.\n"
            f"9. Use extract_structured_data for configuration options, env vars, or settings.\n\n"
            f"Be thorough — capture code examples exactly as written on the page.\n"
            f"Scroll down to read the entire page, not just the visible portion."
        )

    # ------------------------------------------------------------------
    # Internal phases
    # ------------------------------------------------------------------

    async def _search_for_topic(
        self,
        session: "ResearchSession",
        topic: str,
    ) -> str:
        """Use browser-use to search Google for the topic and find the best URL."""
        task = (
            f"Search Google for '{topic}' and find the official documentation "
            f"or GitHub repository. Return the best URL you find.\n"
            f"Steps:\n"
            f"1. Go to https://www.google.com/search?q={topic.replace(' ', '+')}+documentation\n"
            f"2. Look at the top results for the official site, GitHub repo, or docs\n"
            f"3. Click on the most relevant result\n"
            f"4. Use the record_doc_link action to save the URL you land on"
        )
        agent, findings = await session.create_agent(
            task=task,
            llm=self.llm,
            max_steps=15,
        )
        await agent.run()

        # The agent should have recorded a link via the tool
        if findings and findings.links:
            return findings.links[0]["url"]

        # Fallback: construct a search URL
        logger.warning("Agent did not record a URL; falling back to GitHub search.")
        return f"https://github.com/search?q={topic.replace(' ', '+')}&type=repositories"

    async def _run_research_agent(
        self,
        session: "ResearchSession",
        topic: str,
        url: str,
    ) -> "ResearchFindings":
        """Run the main research agent on the given URL."""
        from skill_gen.browser.tools import ResearchFindings

        task = self._build_research_task(topic, url)
        agent, findings = await session.create_agent(
            task=task,
            llm=self.llm,
            max_steps=self.max_pages * 5,
        )
        await agent.run()
        return findings or ResearchFindings()

    async def _follow_links(
        self,
        session: "ResearchSession",
        findings: "ResearchFindings",
        topic: str,
    ) -> "ResearchFindings":
        """Visit additional doc links discovered in the first pass.

        Respects :attr:`max_depth` and :attr:`max_pages` limits.
        """
        visited = 0
        links_to_follow = findings.links[: self.max_depth]

        for link_info in links_to_follow:
            if visited >= self.max_pages:
                break

            link_url = link_info.get("url", "")
            if not link_url:
                continue

            label = link_info.get("label", "documentation page")
            task = (
                f"You are researching '{topic}'. Visit {link_url} "
                f"(described as: {label}). Extract any useful information:\n"
                f"- Use set_overview if you find a better description\n"
                f"- Use save_code_example for code snippets\n"
                f"- Use record_command for CLI commands or API methods\n"
                f"- Use record_install_command for installation instructions\n"
                f"- Use extract_structured_data for configuration or options"
            )
            agent, sub_findings = await session.create_agent(
                task=task,
                llm=self.llm,
                max_steps=20,
            )
            try:
                await agent.run()
            except Exception:
                logger.warning("Error following link %s; skipping.", link_url, exc_info=True)
                continue

            # Merge sub-findings into main findings
            if sub_findings:
                self._merge_findings(findings, sub_findings)
            visited += 1

        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_research_task(self, topic: str, url: str) -> str:
        """Construct the task prompt for the main research agent."""
        topic_ctx = f" about '{topic}'" if topic else ""
        return (
            f"You are a technical researcher{topic_ctx}.\n"
            f"Starting URL: {url}\n\n"
            f"Your goal is to thoroughly research this tool/library and extract "
            f"all the information needed to write a comprehensive skill file.\n\n"
            f"Follow these steps:\n"
            f"1. Navigate to {url} and read the main page.\n"
            f"2. Use set_overview to record a concise description of what this tool does.\n"
            f"3. Look for installation instructions and use record_install_command for each one.\n"
            f"4. Find the main commands/API methods and use record_command for each.\n"
            f"5. Find code examples and use save_code_example for each.\n"
            f"6. Look for configuration options and use extract_structured_data.\n"
            f"7. Find links to API reference, guides, or examples and use record_doc_link.\n"
            f"8. Browse up to {self.max_pages} pages total, following the most relevant links.\n\n"
            f"Focus on practical usage information: how to install, configure, and use the tool."
        )

    @staticmethod
    def _merge_findings(
        target: "ResearchFindings",
        source: "ResearchFindings",
    ) -> None:
        """Merge *source* findings into *target* in place."""
        if source.overview and not target.overview:
            target.overview = source.overview
        target.structured_data.extend(source.structured_data)
        target.code_examples.extend(source.code_examples)
        target.install_commands.extend(source.install_commands)
        target.commands.extend(source.commands)
        # Don't merge links -- we don't want infinite recursion

    def _aggregate(
        self,
        findings: "ResearchFindings",
        url: str,
        topic: str,
    ) -> dict[str, Any]:
        """Convert raw ``ResearchFindings`` into a ``ResearchData`` dict."""
        # Derive a name from topic or URL
        name = topic or url.rstrip("/").split("/")[-1]
        name = name.replace("-", " ").replace("_", " ").title()

        data = ResearchData(
            name=name,
            description=findings.overview or f"Skill for {name}.",
            installation=[
                InstallInfo(**ic) for ic in findings.install_commands
            ],
            commands=[
                CommandInfo(**c) for c in findings.commands
            ],
            examples=[
                CodeExample(**ce) for ce in findings.code_examples
            ],
            source_urls=[url] if url else [],
        )

        # Mine structured_data for workflows, config, gotchas
        for blob in findings.structured_data:
            if isinstance(blob, dict):
                # Workflows
                for wf in blob.get("workflows", []):
                    if isinstance(wf, dict):
                        data.workflows.append(WorkflowStep(**wf))
                    elif isinstance(wf, str):
                        data.workflows.append(WorkflowStep(title=wf, description=""))

                # Configuration
                for cfg in blob.get("configuration", []):
                    if isinstance(cfg, dict):
                        data.configuration.append(cfg)

                # Gotchas / tips
                for g in blob.get("gotchas", []):
                    if isinstance(g, str):
                        data.gotchas.append(g)

                # Allowed tools
                for t in blob.get("allowed_tools", []):
                    if isinstance(t, str) and t not in data.allowed_tools:
                        data.allowed_tools.append(t)

        return data.to_dict()
