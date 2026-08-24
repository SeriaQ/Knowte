"""Prompt assembly for source-specific Search strategy discussion."""

from __future__ import annotations

from collections.abc import Iterable


_CORE_PROMPT = """You design a visible, editable Source-discovery strategy in Knowte.

Return JSON only, as an object with an `actions` array. Propose no more than five actions total. Every action must contain:
- `query`: the exact text Knowte should send to a search provider;
- `target`: `academic`, `web`, or `both`;
- `purpose`: a short explanation of what this action should retrieve and why it covers part of the intent.

The query and purpose have different jobs. Never put retrieval instructions such as "find", "retrieve", "look for", "primary paper", "independent analysis", or "official source" in an Academic query; put them in `purpose`.

Academic-query rules:
- Write portable lexical queries for arXiv, OpenAlex, and Semantic Scholar, not natural-language research tasks.
- Prefer 2–8 discriminative terms likely to occur in a title or abstract. Preserve exact model, method, dataset, benchmark, organism, or theory names.
- An exact paper/report title is excellent only when you are confident it is real. Otherwise use stable title/abstract terms and do not invent a title.
- Split materially different discovery goals into separate actions: primary work or successor, survey, comparative evaluation, and foundational method. Do not add generic words such as "paper", "study", "analysis", or "comparison" unless they are meaningful terms in that literature.
- Avoid provider-specific field syntax and elaborate Boolean expressions.

Web-query rules:
- Natural search-engine phrasing is allowed. Add discriminators such as documentation, release notes, model card, repository, implementation, production, or independent evaluation when they improve precision.
- Prefer first-party material for specifications and releases; use independent sources for practice, criticism, and comparison.

Strategy rules:
- Preserve the user's intent. Do not silently broaden it, change Area/year filters, or claim that anything has already been searched.
- Use only enabled channels. Prefer source-specific actions over `both` when Academic and Web need different wording.
- Cover distinct information needs rather than producing near-duplicate paraphrases.
- Fewer strong actions are better than filling all five slots.
"""


_EXAMPLE_SETS = {
    "general": """Example — model-family investigation (no Area filter)
Intent: understand the architecture, evolution, and long-context improvements of the Qwen model family
Good actions:
{"query":"Qwen Technical Report","target":"academic","purpose":"Locate the original Qwen family report."}
{"query":"Qwen2 Technical Report","target":"academic","purpose":"Retrieve the primary successor report for architectural and training changes."}
{"query":"Qwen2.5 long context","target":"academic","purpose":"Find papers or reports whose titles or abstracts discuss Qwen2.5 long-context capability."}
{"query":"Qwen2.5 long context documentation","target":"web","purpose":"Find first-party configuration limits and implementation guidance."}
Bad Academic query: "Qwen series architecture technical report primary paper"
Why bad: it mixes a discovery instruction with several weak terms instead of using a real title or discriminative title/abstract vocabulary.
""",
    "ai_model": """Example — AI / model families and machine learning
Intent: understand the architecture, evolution, and long-context improvements of the Qwen model family
Good actions:
{"query":"Qwen Technical Report","target":"academic","purpose":"Locate the original Qwen family report."}
{"query":"Qwen2 Technical Report","target":"academic","purpose":"Retrieve the primary successor report for architectural and training changes."}
{"query":"Qwen2.5 long context","target":"academic","purpose":"Find papers or reports using Qwen2.5 and long-context terminology in titles or abstracts."}
{"query":"Qwen2.5 long context documentation","target":"web","purpose":"Find first-party configuration limits and implementation guidance."}
Bad Academic query: "Qwen model performance benchmarks and comparative analysis"
Why bad: "performance", "benchmarks", "comparative", and "analysis" form a vague bundle. Search a named report, capability, or benchmark separately.
""",
    "ai_nlp": """Example — AI / NLP method evaluation
Intent: understand how retrieval-augmented generation affects factuality
Good actions:
{"query":"retrieval augmented generation factuality","target":"academic","purpose":"Retrieve core methods and evaluations using likely title/abstract terminology."}
{"query":"RAG hallucination benchmark","target":"academic","purpose":"Find benchmark-driven evaluations rather than another paraphrase of the method query."}
{"query":"retrieval augmented generation production evaluation","target":"web","purpose":"Find implementation experience and evaluation guidance outside papers."}
Bad Academic query: "Find primary papers about how RAG reduces hallucinations"
Why bad: it is a question for a researcher, not title/abstract vocabulary for a bibliographic search engine.
""",
    "ai_rl": """Example — AI / reinforcement learning
Intent: compare offline reinforcement learning algorithms and understand when conservative methods help
Good actions:
{"query":"offline reinforcement learning conservative Q-learning","target":"academic","purpose":"Retrieve the named method family and closely related successors."}
{"query":"offline reinforcement learning benchmark","target":"academic","purpose":"Find comparative evaluations across datasets and algorithms."}
{"query":"offline reinforcement learning implementation pitfalls","target":"web","purpose":"Find practical training and evaluation lessons."}
Bad Academic query: "best offline reinforcement learning algorithms and why they work"
""",
    "ai_robotics": """Example — AI / robotics
Intent: understand how vision-language-action models transfer to real robots
Good actions:
{"query":"vision language action robot policy","target":"academic","purpose":"Retrieve the central model and policy literature."}
{"query":"vision language action sim-to-real","target":"academic","purpose":"Target transfer and deployment evidence rather than repeating the broad query."}
{"query":"vision language action robot deployment","target":"web","purpose":"Find first-party demonstrations, code, and engineering limitations."}
""",
    "ai_ir": """Example — AI / information retrieval
Intent: compare dense and hybrid retrieval for domain-specific corpora
Good actions:
{"query":"dense retrieval domain adaptation","target":"academic","purpose":"Retrieve methods addressing domain shift in dense retrievers."}
{"query":"hybrid retrieval dense sparse benchmark","target":"academic","purpose":"Find direct comparative evaluations of hybrid retrieval."}
{"query":"hybrid search production evaluation","target":"web","purpose":"Find operational guidance on indexing, latency, and relevance evaluation."}
""",
    "ai_multi_agent": """Example — AI / multi-agent systems
Intent: determine whether LLM multi-agent collaboration improves reasoning
Good actions:
{"query":"LLM multi-agent collaboration reasoning","target":"academic","purpose":"Retrieve primary collaboration methods and evaluations."}
{"query":"multi-agent debate benchmark","target":"academic","purpose":"Target a named interaction pattern and its comparative evidence."}
{"query":"LLM multi-agent failure modes","target":"academic","purpose":"Find work measuring coordination failures and correlated errors."}
Bad Academic query: "Do multiple AI agents really reason better together"
""",
    "ai_safety": """Example — AI / safety
Intent: understand defenses against jailbreak attacks and whether they generalize
Good actions:
{"query":"large language model jailbreak defense","target":"academic","purpose":"Retrieve proposed defense methods."}
{"query":"jailbreak defense adaptive attack evaluation","target":"academic","purpose":"Find evaluations against adaptive rather than static attacks."}
{"query":"LLM jailbreak benchmark","target":"academic","purpose":"Locate reusable datasets and evaluation protocols."}
{"query":"LLM jailbreak defense deployment guidance","target":"web","purpose":"Find current provider and practitioner mitigations."}
""",
    "ai_reasoning": """Example — AI / reasoning
Intent: understand how test-time computation improves mathematical reasoning
Good actions:
{"query":"test-time compute mathematical reasoning","target":"academic","purpose":"Retrieve methods linking inference-time computation to math performance."}
{"query":"process reward model mathematical reasoning","target":"academic","purpose":"Target a distinct mechanism used to guide multi-step reasoning."}
{"query":"test-time scaling reasoning benchmark","target":"academic","purpose":"Find scaling and comparative evaluation evidence."}
Bad Academic query: "new techniques that make language models think longer and solve math"
""",
    "vision_graphics": """Example — vision / graphics
Intent: understand dynamic-scene extensions of 3D Gaussian splatting
Good actions:
{"query":"dynamic 3D Gaussian splatting","target":"academic","purpose":"Retrieve primary dynamic-scene methods."}
{"query":"dynamic Gaussian splatting benchmark","target":"academic","purpose":"Find comparative evaluations and datasets."}
{"query":"dynamic Gaussian splatting implementation repository","target":"web","purpose":"Locate maintained implementations and practical constraints."}
""",
    "math_stats": """Example — mathematics / statistics
Intent: understand conformal prediction under covariate shift
Good actions:
{"query":"conformal prediction covariate shift","target":"academic","purpose":"Retrieve the central theoretical and methodological literature."}
{"query":"weighted conformal prediction covariate shift","target":"academic","purpose":"Target a major method family without writing a prose research task."}
""",
    "bio_med": """Example — biology / medicine
Intent: evaluate cardiovascular evidence for GLP-1 receptor agonists
Good actions:
{"query":"GLP-1 receptor agonist cardiovascular outcomes trial","target":"academic","purpose":"Retrieve primary outcomes trials and closely matching evidence."}
{"query":"GLP-1 cardiovascular outcomes meta-analysis","target":"academic","purpose":"Retrieve synthesized comparative evidence."}
{"query":"FDA GLP-1 cardiovascular indication label","target":"web","purpose":"Find current first-party regulatory material."}
""",
    "physics": """Example — physics
Intent: understand evidence for high-temperature superconductivity in hydrides
Good actions:
{"query":"hydride high temperature superconductivity","target":"academic","purpose":"Retrieve central experimental and theoretical work."}
{"query":"superconducting hydrides experimental evidence","target":"academic","purpose":"Target evidence-focused follow-up and review literature."}
""",
    "econ_fin": """Example — economics / finance
Intent: understand how central bank digital currency could affect bank lending
Good actions:
{"query":"central bank digital currency bank lending","target":"academic","purpose":"Retrieve directly relevant models and empirical studies."}
{"query":"CBDC bank disintermediation","target":"academic","purpose":"Target the established mechanism and terminology used in the literature."}
{"query":"BIS CBDC bank lending report","target":"web","purpose":"Find institutional analysis and policy evidence."}
""",
}


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
    areas: Iterable[str] = (), custom_instructions: str = ""
) -> str:
    """Build the stable rules plus only the examples relevant to selected Areas."""

    examples = "\n\n".join(_EXAMPLE_SETS[key] for key in _example_keys(areas))
    prompt = f"{_CORE_PROMPT}\n\nRelevant examples:\n{examples}"
    instructions = custom_instructions.strip()
    if instructions:
        prompt += "\n\nUser-configured Copilot instructions:\n" + instructions
    return prompt
