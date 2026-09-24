"""Stage-specific system prompts for the Review Copilot."""
from __future__ import annotations

from ..stage_skills import BUILTINS, skill_info, skill_prompt

_STAGES = ("search", "library", "evidence", "claims", "views", "artifact")
_ALIASES = {"sources": "library", "projects": "artifact", "wiki": "views"}


def review_copilot_prompt(context: str, custom_instructions: str = "", directory=None) -> str:
    stage = str(context or "").strip().lower()
    stage = _ALIASES.get(stage, stage)
    if stage not in _STAGES:
        stage = "search"
    return skill_prompt("copilot_" + stage, directory, preferences=custom_instructions)


def review_copilot_shared_prompt() -> str:
    return (BUILTINS / "rules.md").read_text(encoding="utf-8")


def review_copilot_stage_prompt_previews() -> dict[str, str]:
    return {stage: skill_info("copilot_" + stage)["guidance"] for stage in _STAGES}


def review_copilot_prompt_previews(custom_instructions: str = "") -> dict[str, str]:
    return {stage: review_copilot_prompt(stage, custom_instructions) for stage in _STAGES}
