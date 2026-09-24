---
name: claim-proposal
description: Evidence · Propose Claims
stage: claim_proposal
contract_version: 1
---

# Claim Change Proposal Capability

Capability ID: `claim-proposal-v4`

Turn the user's selected Evidence into the smallest useful set of reviewable
changes to durable Claims. This is knowledge distillation, not passage
summarization. Every output remains a draft until the user accepts it.

The input contains:

- `focus`: an optional retrieval goal. It controls relevance and granularity,
  never the truth of a Claim.
- `evidence`: the complete active grounding scope. Only these exact Evidence
  identifiers may be linked by this run.
- `existing_claims`: a bounded, locally retrieved comparison set. Use it to
  avoid duplicates and detect support, contradiction, or limitation. It is not
  additional Evidence.

Closed vocabularies:

- Claim basis: `reported` or `inference` in this Evidence-grounded operation.
- Evidence–Claim stance: `supports`, `contradicts`, or `limits`.
- Claim–Claim relation: `supports`, `contradicts`, or `related`.

Method:

1. Examine every selected Evidence item. Decompose compound passages into
   independently examinable factual units internally.
2. Cluster units by the same subject, mechanism, version, condition, metric, or
   question. Do not cluster merely because they mention the same broad topic.
3. Compare candidates with `existing_claims` before proposing anything new.
4. Keep only propositions that are atomic, self-contained, adequately
   qualified, and useful beyond a one-off summary.
5. Deduplicate the proposal set. Do not mechanically rewrite every Evidence
   item into a Claim and do not fill a quota.

New Claims:

- Use `reported` when the complete proposition is directly stated by the
  linked Evidence. One Evidence may support several distinct Claims, and one
  reported Claim may have several direct supporting items.
- Use `inference` only when at least two selected Evidence items make materially
  necessary contributions to a conclusion not completely stated by any one of
  them. If removing an Evidence item leaves the full Claim supported, do not
  attach that item merely to make the Claim look synthesized.
- A broad narrative, list of adjacent facts, or topic overview belongs in a
  View, not in a Claim.
- Preserve version, time, population, model size, experimental setting, and
  other truth-condition qualifiers whenever they matter.

Existing Claims:

- If selected Evidence repeats an existing Claim, propose an
  `existing_claim_update` with `supports`; do not create a duplicate Claim.
- Use `contradicts` only when the Evidence conflicts under materially matching
  conditions.
- Use `limits` when the Evidence lends some support but narrows the Claim's
  scope, strength, conditions, or time range.
- Source count is context, not a relation. Several excerpts from one Source can
  compose a conclusion but are not independent corroboration.
- Give each new Claim a unique `temp_id` such as `new:1`. Relation endpoints
  may use these temporary IDs or exact supplied existing Claim IDs. Consider
  new–new and new–existing pairs; consider existing–existing pairs only when
  this run's Evidence adds a materially new judgment. Do not scan old knowledge
  incidentally. Relations are independent review drafts, not automatically accepted.
- `supports` is directional: the subject provides a reason to believe the object;
  `contradicts` requires matching truth conditions; `related` requires a specific
  useful conceptual connection. Explain that connection in the rationale.
  Shared topic, Source, or wording alone does not justify a relation. Do not fill
  a quota. Never use an unknown or discarded candidate ID.

Quality and safety:

- Use only exact supplied identifiers. Never invent a Source, Evidence, Claim,
  quotation, or locator.
- Every Evidence link needs a short, checkable rationale explaining its actual
  contribution.
- Put a caveat in `caveats` only for a concrete material uncertainty,
  dependency, missing coverage, or conflict. Otherwise return an empty array.
- Do not silently revise, withdraw, supersede, accept, or dispute an existing
  Claim.
- Do not return chain-of-thought. Rationales are concise review explanations.
- `skipped` is a transient explanation, not a knowledge object. Use it when
  material is irrelevant to the Focus, duplicative within the run, too weak,
  or better suited to a View.
