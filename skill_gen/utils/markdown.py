"""
Markdown generation helpers for building SKILL.md files.

Provides utilities for YAML frontmatter, sections, code blocks,
tables, and content truncation.
"""

from __future__ import annotations

import re
from typing import Any

import yaml


def frontmatter_to_yaml(data: dict[str, Any]) -> str:
    """Convert a dictionary to YAML frontmatter block.

    Args:
        data: Dictionary of frontmatter fields. Values that are lists
              are rendered as YAML sequences.

    Returns:
        A string wrapped in ``---`` delimiters ready for a Markdown file.
    """
    # Use block style for lists, keep scalars inline
    yaml_body = yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    ).rstrip("\n")
    return f"---\n{yaml_body}\n---"


def section(title: str, content: str, level: int = 2) -> str:
    """Build a Markdown section with a heading and body.

    Args:
        title: Section heading text.
        content: Body content (may contain Markdown).
        level: Heading level (1-6).

    Returns:
        Formatted Markdown section string.
    """
    prefix = "#" * max(1, min(level, 6))
    return f"{prefix} {title}\n\n{content.rstrip()}\n"


def code_block(code: str, language: str = "bash") -> str:
    """Wrap code in a fenced code block.

    Args:
        code: The source code or command text.
        language: Language identifier for syntax highlighting.

    Returns:
        A fenced Markdown code block.
    """
    return f"```{language}\n{code.rstrip()}\n```"


def table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a Markdown table.

    Args:
        headers: Column header labels.
        rows: List of rows, each row a list of cell values.

    Returns:
        A pipe-delimited Markdown table string.
    """
    if not headers:
        return ""

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    def _pad(values: list[str]) -> str:
        parts = []
        for i, v in enumerate(values):
            width = col_widths[i] if i < len(col_widths) else len(str(v))
            parts.append(f" {str(v).ljust(width)} ")
        return "|" + "|".join(parts) + "|"

    header_line = _pad(headers)
    separator = "|" + "|".join(f" {'-' * w} " for w in col_widths) + "|"
    body_lines = [_pad(row) for row in rows]

    return "\n".join([header_line, separator, *body_lines])


def truncate_to_lines(text: str, max_lines: int = 500) -> str:
    """Truncate text to a maximum number of lines.

    If the text exceeds *max_lines*, it is cut and a truncation notice is
    appended.

    Args:
        text: The full text to potentially truncate.
        max_lines: Maximum number of lines to keep.

    Returns:
        The (possibly truncated) text.
    """
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text

    kept = lines[:max_lines - 2]
    kept.append("")
    kept.append(f"<!-- Truncated: {len(lines) - max_lines + 2} lines omitted to stay within {max_lines}-line limit -->")
    return "\n".join(kept)


def slugify(text: str) -> str:
    """Convert text to a URL/filename-friendly slug.

    Args:
        text: Arbitrary text.

    Returns:
        Lowercased, hyphen-separated slug.
    """
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")
