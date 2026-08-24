from knowte.prompts.review_copilot import (
    review_copilot_prompt,
    review_copilot_prompt_previews,
    review_copilot_shared_prompt,
    review_copilot_stage_prompt_previews,
)


def test_search_prompt_proposes_candidates_without_source_review_decisions():
    prompt = review_copilot_prompt("search")

    assert "optional `search_actions` array" in prompt
    assert "not an automatic replacement" in prompt
    assert "Do not return Source-review decisions" in prompt
    assert "decision` (`add`, `skip`, or `inspect`)" not in prompt


def test_sources_prompt_owns_source_review_decisions():
    prompt = review_copilot_prompt("library")

    assert "Current workspace: Sources" in prompt
    assert "decision` (`add`, `skip`, or `inspect`)" in prompt
    assert "search_actions" not in prompt


def test_each_knowledge_stage_has_a_distinct_prompt_preview():
    previews = review_copilot_prompt_previews("Prefer concise responses.")

    assert set(previews) == {
        "search", "library", "evidence", "claims", "views", "artifact"
    }
    assert "Current workspace: Evidence" in previews["evidence"]
    assert "Current workspace: Claims" in previews["claims"]
    assert all(value.endswith("Prefer concise responses.") for value in previews.values())


def test_prompt_preview_can_separate_shared_and_stage_specific_content():
    shared = review_copilot_shared_prompt()
    stages = review_copilot_stage_prompt_previews()

    assert "Knowte distinguishes these objects" in shared
    assert "Current workspace" not in shared
    assert "Current workspace: Evidence" in stages["evidence"]
    assert "Knowte distinguishes these objects" not in stages["evidence"]
    assert review_copilot_prompt("evidence") == f"{shared}\n\n{stages['evidence']}"
