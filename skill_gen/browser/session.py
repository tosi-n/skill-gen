"""
Browser session management for research agents.

Wraps browser-use's Browser and Agent classes to provide a clean
lifecycle (start / create_agent / close) with sensible defaults.

All browser-use imports are deferred to method bodies so the module
can be imported without browser-use being installed (useful for the
validate/init CLI commands that don't need a browser).
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from browser_use import Agent, Browser, BrowserConfig
    from skill_gen.browser.tools import ResearchFindings

logger = logging.getLogger(__name__)


class ResearchSession:
    """Manages browser-use sessions for research.

    Args:
        headed: If ``True``, launch the browser with a visible window
                (useful for debugging). Defaults to headless.
        browser_config: Optional ``BrowserConfig`` override.
    """

    def __init__(
        self,
        headed: bool = False,
        browser_config: Any = None,
    ) -> None:
        self.headed = headed
        self._browser_config = browser_config
        self.browser: Any = None  # Browser | None
        self._agents: list[Any] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialise the browser instance."""
        if self.browser is not None:
            logger.debug("Browser already running; skipping start.")
            return

        from browser_use import Browser, BrowserConfig

        config = self._browser_config or BrowserConfig(
            headless=not self.headed,
        )
        self.browser = Browser(config=config)
        logger.info("Browser session started (headed=%s).", self.headed)

    async def close(self) -> None:
        """Tear down the browser and all agents."""
        if self.browser is not None:
            try:
                await self.browser.close()
            except Exception:
                logger.warning("Error closing browser; ignoring.", exc_info=True)
            finally:
                self.browser = None
        self._agents.clear()
        logger.info("Browser session closed.")

    # ------------------------------------------------------------------
    # Agent factory
    # ------------------------------------------------------------------

    async def create_agent(
        self,
        task: str,
        llm: Any = None,
        max_steps: int = 50,
        include_research_tools: bool = True,
    ) -> tuple[Any, Any]:
        """Create a browser-use Agent bound to the managed browser.

        Args:
            task: Natural-language task description for the agent.
            llm: Language model instance (e.g. ``ChatOpenAI``).  Required
                 by browser-use; must be supplied by the caller.
            max_steps: Maximum actions the agent may take.
            include_research_tools: Attach the skill-gen custom research
                tools so the agent can persist structured findings.

        Returns:
            A tuple of ``(agent, findings)`` where *findings* is a
            ``ResearchFindings`` that accumulates data extracted
            by the agent, or ``None`` when research tools are disabled.
        """
        if self.browser is None:
            await self.start()

        from browser_use import Agent
        from skill_gen.browser.tools import ResearchFindings, create_research_tools

        findings: ResearchFindings | None = None
        controller = None

        if include_research_tools:
            controller, findings = create_research_tools()

        agent = Agent(
            task=task,
            llm=llm,
            browser=self.browser,
            controller=controller,
            max_actions_per_step=5,
        )

        self._agents.append(agent)
        logger.info("Created agent for task: %.80s...", task)
        return agent, findings

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "ResearchSession":
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
