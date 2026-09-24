"""Prompt assembly for source-specific Search strategy discussion."""

from __future__ import annotations

from collections.abc import Iterable


from ..stage_skills import skill_prompt


def _example_keys(areas: Iterable[str]) -> list[str]:
    codes = [str(area).strip().lower() for area in areas if str(area).strip()]
    if not codes:
        return ["general"]

    keys: list[str] = []
    for code in codes:
        if code.startswith(("bio.", "med.")):
            key = "bio_med"
        elif code.startswith(("econ.", "fin.")):
            key = "econ_fin"
        elif code.startswith("physics."):
            key = "physics"
        elif code.startswith(("math.", "stat.")):
            key = "math_stats"
        elif code.startswith("ai.rl"):
            key = "ai_rl"
        elif code.startswith("ai.robotics"):
            key = "ai_robotics"
        elif code.startswith(("ai.cv", "cs.graphics")):
            key = "vision_graphics"
        elif code.startswith("ai.nlp"):
            key = "ai_nlp"
        elif code.startswith("ai.ir"):
            key = "ai_ir"
        elif code.startswith("ai.multi_agent"):
            key = "ai_multi_agent"
        elif code.startswith("ai.safety"):
            key = "ai_safety"
        elif code.startswith("ai.reasoning"):
            key = "ai_reasoning"
        elif code.startswith("ai."):
            key = "ai_model"
        else:
            continue
        if key not in keys:
            keys.append(key)
        if len(keys) == 2:
            break
    return keys or ["general"]


def build_search_strategy_prompt(
    areas: Iterable[str] = (), custom_instructions: str = "", directory=None,
) -> str:
    return skill_prompt(
        "search_strategy", directory, _example_keys(areas), custom_instructions,
    )
