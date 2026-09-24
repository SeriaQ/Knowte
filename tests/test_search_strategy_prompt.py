from knowte.prompts.search_strategy import build_search_strategy_prompt


def test_prompt_uses_general_example_without_area_filter():
    prompt = build_search_strategy_prompt([]).guidance

    assert "Qwen Technical Report" in prompt
    assert "query and purpose have different jobs" in prompt
    assert "find\", \"retrieve" in prompt


def test_prompt_selects_ai_examples_from_area_filter():
    prompt = build_search_strategy_prompt(["ai.nlp"]).guidance

    assert "retrieval augmented generation factuality" in prompt
    assert "GLP-1 receptor agonist" not in prompt


def test_prompt_routes_specialized_ai_areas_to_distinct_examples():
    safety_prompt = build_search_strategy_prompt(["ai.safety"]).guidance
    reasoning_prompt = build_search_strategy_prompt(["ai.reasoning"]).guidance

    assert "jailbreak defense adaptive attack evaluation" in safety_prompt
    assert "test-time compute mathematical reasoning" not in safety_prompt
    assert "test-time compute mathematical reasoning" in reasoning_prompt
    assert "jailbreak defense adaptive attack evaluation" not in reasoning_prompt


def test_prompt_combines_at_most_two_ai_area_example_sets():
    prompt = build_search_strategy_prompt(
        ["ai.ir", "ai.multi_agent", "ai.robotics"]
    ).guidance

    assert "hybrid retrieval dense sparse benchmark" in prompt
    assert "multi-agent debate benchmark" in prompt
    assert "vision language action robot policy" not in prompt


def test_prompt_can_combine_two_area_example_sets_without_unrelated_examples():
    prompt = build_search_strategy_prompt(["med.general", "econ.general"]).guidance

    assert "GLP-1 receptor agonist" in prompt
    assert "central bank digital currency" in prompt
    assert "dynamic 3D Gaussian splatting" not in prompt


def test_prompt_appends_custom_copilot_instructions():
    prompt = build_search_strategy_prompt(
        ["ai.rl"], "Prefer primary sources written in English."
    ).guidance

    assert "offline reinforcement learning conservative Q-learning" in prompt
    assert prompt.endswith("Prefer primary sources written in English.")
