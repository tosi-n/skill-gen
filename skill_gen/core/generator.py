"""
Skill generator engine.

Transforms structured research data into a complete SKILL.md file,
optionally creating supporting directories for scripts and assets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from jinja2 import BaseLoader, Environment

from skill_gen.core.templates import TEMPLATES, get_template
from skill_gen.core.validator import SkillValidator, ValidationResult
from skill_gen.utils.markdown import (
    code_block,
    section,
    table,
    truncate_to_lines,
)


class SkillGenerator:
    """Transforms research findings into a well-structured SKILL.md.

    Args:
        template: Template name -- one of ``basic``, ``browser``, ``api``,
                  ``cli``, ``composite``.
    """

    def __init__(self, template: str = "basic") -> None:
        self.template_name = template
        self._jinja_env = Environment(loader=BaseLoader(), autoescape=False)
        self._validator = SkillValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        research_data: dict[str, Any],
        output_dir: str,
    ) -> str:
        """Generate a complete skill from research data.

        Args:
            research_data: Dictionary with keys such as *name*,
                *description*, *installation*, *commands*, *workflows*,
                *configuration*, *triggers*, *examples*.
            output_dir: Directory where the SKILL.md (and optional
                subdirectories) will be written.

        Returns:
            Absolute path to the generated ``SKILL.md``.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # 1. Select and render template
        template_str = get_template(self.template_name)
        context = self._build_template_context(research_data)
        rendered = self._render_template(template_str, context)

        # 2. Truncate to 500 lines
        rendered = truncate_to_lines(rendered, max_lines=500)

        # 3. Validate the generated content by writing a temporary buffer
        skill_path = out / "SKILL.md"
        skill_path.write_text(rendered, encoding="utf-8")

        validation = self._validator.validate(str(skill_path))
        if not validation.valid:
            # Attempt auto-fix for common issues, then re-validate
            rendered = self._auto_fix(rendered, validation)
            skill_path.write_text(rendered, encoding="utf-8")

        # 4. Create optional supporting directories
        self._create_support_dirs(out, research_data)

        return str(skill_path.resolve())

    def generate_from_template(
        self,
        name: str,
        template: str = "basic",
        output_dir: str = ".",
    ) -> str:
        """Generate a blank skill scaffold from a template (synchronous).

        Used by the ``init`` CLI command to create a starting-point file.

        Args:
            name: Skill name.
            template: Template type.
            output_dir: Output directory.

        Returns:
            Absolute path to the generated SKILL.md.
        """
        template_str = get_template(template)
        context = {
            "name": name,
            "description": f"Skill for {name}.",
            "allowed_tools": [],
            "installation": "",
            "workflow": "",
            "commands": "",
            "patterns": "",
            "configuration": "",
            "tips": "",
        }
        rendered = self._render_template(template_str, context)

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        skill_path = out / "SKILL.md"
        skill_path.write_text(rendered, encoding="utf-8")
        self._create_support_dirs(out, {})

        return str(skill_path.resolve())

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    def _build_template_context(self, data: dict[str, Any]) -> dict[str, Any]:
        """Prepare the Jinja2 context dictionary from research data."""
        return {
            "name": data.get("name", "Unnamed Skill"),
            "description": data.get("description", ""),
            "allowed_tools": data.get("allowed_tools", []),
            "installation": self._build_installation(data),
            "workflow": self._build_workflow(data),
            "commands": self._build_commands(data),
            "patterns": self._build_patterns(data),
            "configuration": self._build_configuration(data),
            "tips": self._build_tips(data),
        }

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_installation(self, data: dict[str, Any]) -> str:
        """Build the installation / prerequisites section content."""
        install = data.get("installation")
        if not install:
            return ""

        if isinstance(install, str):
            return code_block(install, "bash")

        # install is a list of commands
        if isinstance(install, list):
            parts: list[str] = []
            for item in install:
                if isinstance(item, dict):
                    mgr = item.get("package_manager", "bash")
                    cmd = item.get("command", "")
                    parts.append(f"**{mgr}**:\n\n{code_block(cmd, 'bash')}")
                else:
                    parts.append(code_block(str(item), "bash"))
            return "\n\n".join(parts)

        return str(install)

    def _build_workflow(self, data: dict[str, Any]) -> str:
        """Build the core workflow section."""
        workflows = data.get("workflows", [])
        if not workflows:
            return ""

        lines: list[str] = []
        for i, wf in enumerate(workflows, 1):
            if isinstance(wf, dict):
                title = wf.get("title", f"Step {i}")
                desc = wf.get("description", "")
                lines.append(f"{i}. **{title}** -- {desc}")
            else:
                lines.append(f"{i}. {wf}")
        return "\n".join(lines)

    def _build_commands(self, data: dict[str, Any]) -> str:
        """Build the commands / API reference section."""
        commands = data.get("commands", [])
        if not commands:
            return ""

        headers = ["Command", "Description"]
        rows: list[list[str]] = []
        for cmd in commands:
            if isinstance(cmd, dict):
                name = f"`{cmd.get('name', '')}`"
                syntax = cmd.get("syntax", "")
                desc = cmd.get("description", "")
                display = f"{syntax} -- {desc}" if syntax else desc
                rows.append([name, display])
            else:
                rows.append([f"`{cmd}`", ""])

        return table(headers, rows)

    def _build_patterns(self, data: dict[str, Any]) -> str:
        """Build the common patterns section with code examples."""
        examples = data.get("examples", [])
        if not examples:
            return ""

        parts: list[str] = []
        for ex in examples:
            if isinstance(ex, dict):
                desc = ex.get("description", "Example")
                lang = ex.get("language", "bash")
                code = ex.get("code", "")
                parts.append(f"### {desc}\n\n{code_block(code, lang)}")
            elif isinstance(ex, str):
                parts.append(code_block(ex, "bash"))
        return "\n\n".join(parts)

    def _build_configuration(self, data: dict[str, Any]) -> str:
        """Build the configuration section."""
        config = data.get("configuration")
        if not config:
            return ""

        if isinstance(config, str):
            return config

        if isinstance(config, list):
            headers = ["Key", "Description", "Default"]
            rows: list[list[str]] = []
            for item in config:
                if isinstance(item, dict):
                    rows.append([
                        f"`{item.get('key', '')}`",
                        item.get("description", ""),
                        item.get("default", ""),
                    ])
            if rows:
                return table(headers, rows)

        if isinstance(config, dict):
            parts: list[str] = []
            for key, val in config.items():
                parts.append(f"- **{key}**: {val}")
            return "\n".join(parts)

        return str(config)

    def _build_tips(self, data: dict[str, Any]) -> str:
        """Build the tips section."""
        tips = data.get("tips", [])
        gotchas = data.get("gotchas", [])
        all_tips = list(tips) + list(gotchas)
        if not all_tips:
            return ""

        lines: list[str] = []
        for tip in all_tips:
            if isinstance(tip, str):
                lines.append(f"- {tip}")
            elif isinstance(tip, dict):
                lines.append(f"- **{tip.get('title', 'Tip')}**: {tip.get('description', '')}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Template rendering
    # ------------------------------------------------------------------

    def _render_template(self, template_str: str, context: dict[str, Any]) -> str:
        """Render a Jinja2 template string with the given context."""
        tmpl = self._jinja_env.from_string(template_str)
        return tmpl.render(**context)

    # ------------------------------------------------------------------
    # Auto-fix
    # ------------------------------------------------------------------

    def _auto_fix(self, content: str, result: ValidationResult) -> str:
        """Attempt automatic fixes for common validation errors.

        This is best-effort; the result may still have warnings.
        """
        # If content is entirely empty after frontmatter, inject a placeholder
        if any(
            "body is empty" in issue.message.lower()
            for issue in result.errors
        ):
            content = content.rstrip() + "\n\n*This skill needs content. Edit the sections above.*\n"

        return content

    # ------------------------------------------------------------------
    # Support directories
    # ------------------------------------------------------------------

    def _create_support_dirs(
        self,
        base: Path,
        data: dict[str, Any],
    ) -> None:
        """Create optional scripts/ and assets/ directories.

        scripts/ is always created; assets/ only when the research data
        references external assets.
        """
        scripts_dir = base / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Create a placeholder so the directory is tracked by git
        gitkeep = scripts_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

        # Only create assets/ if there is asset-worthy data
        has_assets = bool(data.get("assets")) or bool(data.get("images"))
        if has_assets:
            assets_dir = base / "assets"
            assets_dir.mkdir(exist_ok=True)
            ak = assets_dir / ".gitkeep"
            if not ak.exists():
                ak.touch()
