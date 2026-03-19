"""
skill-gen: Autonomous skill file generator using browser-use for research.

Generates well-structured SKILL.md files by researching tools, libraries,
and frameworks through autonomous web browsing.
"""

__version__ = "0.1.0"
__author__ = "skill-gen contributors"

from skill_gen.core.generator import SkillGenerator
from skill_gen.core.validator import SkillValidator, ValidationResult


def __getattr__(name: str):
    """Lazy-import SkillResearcher to avoid pulling in browser-use at module load."""
    if name == "SkillResearcher":
        from skill_gen.core.researcher import SkillResearcher
        return SkillResearcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SkillGenerator",
    "SkillResearcher",
    "SkillValidator",
    "ValidationResult",
]
