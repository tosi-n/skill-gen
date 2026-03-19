"""
Skill validation engine.

Checks SKILL.md files for structural correctness, required fields,
content constraints, and formatting best practices.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Issue severity level."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """A single validation finding."""
    severity: Severity
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Aggregate validation outcome."""
    valid: bool = True
    issues: list[ValidationIssue] = Field(default_factory=list)
    file_path: Optional[str] = None
    line_count: int = 0

    def add_error(
        self,
        message: str,
        line: int | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.valid = False
        self.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                message=message,
                line=line,
                suggestion=suggestion,
            )
        )

    def add_warning(
        self,
        message: str,
        line: int | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                message=message,
                line=line,
                suggestion=suggestion,
            )
        )

    def add_info(
        self,
        message: str,
        line: int | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                severity=Severity.INFO,
                message=message,
                line=line,
                suggestion=suggestion,
            )
        )

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def summary(self) -> str:
        """One-line summary of validation outcome."""
        e = len(self.errors)
        w = len(self.warnings)
        status = "PASS" if self.valid else "FAIL"
        return f"[{status}] {e} error(s), {w} warning(s) -- {self.line_count} lines"


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_CODE_BLOCK_RE = re.compile(r"```[\w]*\n.*?\n```", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# Required frontmatter fields
_REQUIRED_FM_FIELDS = {"name", "description"}

# Maximum recommended line count
_MAX_LINES = 500


class SkillValidator:
    """Validates a SKILL.md file for structure, content, and best practices."""

    def validate(self, skill_path: str) -> ValidationResult:
        """Validate a SKILL.md file at the given path.

        Args:
            skill_path: Filesystem path to the SKILL.md file.

        Returns:
            A :class:`ValidationResult` with all findings.
        """
        result = ValidationResult(file_path=skill_path)
        path = Path(skill_path)

        # --- File existence ---
        if not path.exists():
            result.add_error(f"File not found: {skill_path}")
            return result

        if not path.is_file():
            result.add_error(f"Path is not a file: {skill_path}")
            return result

        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")
        result.line_count = len(lines)

        # --- Frontmatter presence ---
        fm_match = _FRONTMATTER_RE.match(content)
        if not fm_match:
            result.add_error(
                "Missing YAML frontmatter (file must start with '---').",
                line=1,
                suggestion="Add a YAML frontmatter block at the top of the file.",
            )
            # We can still check other things, but frontmatter-dependent
            # checks will be skipped.
            self._check_body(content, lines, result)
            return result

        # --- Parse YAML frontmatter ---
        fm_raw = fm_match.group(1)
        try:
            fm_data = yaml.safe_load(fm_raw)
            if not isinstance(fm_data, dict):
                result.add_error(
                    "Frontmatter did not parse as a YAML mapping.",
                    line=1,
                )
                fm_data = {}
        except yaml.YAMLError as exc:
            result.add_error(
                f"Invalid YAML in frontmatter: {exc}",
                line=1,
            )
            fm_data = {}

        # --- Required fields ---
        for field in _REQUIRED_FM_FIELDS:
            if field not in fm_data:
                result.add_error(
                    f"Required frontmatter field '{field}' is missing.",
                    line=1,
                    suggestion=f"Add '{field}: <value>' to the frontmatter.",
                )
            elif not fm_data[field]:
                result.add_error(
                    f"Frontmatter field '{field}' is empty.",
                    line=1,
                )

        # --- allowed-tools format ---
        allowed_tools = fm_data.get("allowed-tools")
        if allowed_tools is not None:
            if not isinstance(allowed_tools, list):
                result.add_error(
                    "'allowed-tools' must be a YAML list.",
                    line=1,
                    suggestion="Use '- tool_name' syntax under allowed-tools.",
                )
            else:
                for tool in allowed_tools:
                    if not isinstance(tool, str):
                        result.add_warning(
                            f"allowed-tools entry should be a string, got: {type(tool).__name__}",
                            line=1,
                        )

        # --- Body checks ---
        # Body is everything after the closing '---'
        body_start = fm_match.end()
        body = content[body_start:]
        self._check_body(body, lines, result)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_body(
        self,
        body: str,
        all_lines: list[str],
        result: ValidationResult,
    ) -> None:
        """Run content-level checks on the Markdown body."""

        # --- Line count ---
        if result.line_count > _MAX_LINES:
            result.add_warning(
                f"File has {result.line_count} lines (recommended max: {_MAX_LINES}).",
                suggestion="Trim verbose sections or move details to separate files.",
            )

        # --- At least one code example ---
        if not _CODE_BLOCK_RE.search(body):
            result.add_warning(
                "No fenced code block found in the body.",
                suggestion="Add at least one code example using ``` fencing.",
            )

        # --- Check for headings ---
        headings = _HEADING_RE.findall(body)
        if not headings:
            result.add_warning(
                "No Markdown headings found in the body.",
                suggestion="Use ## Heading to organize the skill into sections.",
            )

        # --- Check for empty body ---
        stripped = body.strip()
        if not stripped:
            result.add_error("Skill body is empty (no content after frontmatter).")

        # --- Look for common structural sections ---
        heading_names = {h[1].strip().lower() for h in headings}
        recommended = {"prerequisites", "commands", "core workflow", "common patterns"}
        missing = recommended - heading_names
        if missing:
            result.add_info(
                f"Recommended section(s) not found: {', '.join(sorted(missing))}",
                suggestion="Consider adding these sections for completeness.",
            )
