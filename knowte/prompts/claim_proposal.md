# Claim Proposal Capability

Capability ID: `claim-proposal-v1`

Propose concise, independently examinable Claims from the supplied Evidence.
This operation produces review drafts only. It never creates or changes durable
knowledge.

Rules:

- Use only the supplied Evidence. Never invent a quotation, locator, Source, or
  Evidence identifier.
- Make each Claim atomic, self-contained, and explicit about its subject,
  conditions, scope, and time when those qualifiers matter.
- Distinguish what a Source reports from an inference across Evidence.
- Prefer `reported` for a proposition directly stated by Evidence and
  `inference` when combining or interpreting multiple items.
- Use one basis from: background, reported, inference. `background` is reserved
  for accepted prior knowledge that may lack Evidence; proposals based on the
  supplied Evidence should normally be `reported` or `inference`.
- Link Evidence with one stance from: supports, contradicts, limits. Use
  `limits` when an item both lends support and narrows the Claim's scope,
  strength, conditions, or time range.
- Surface uncertainty, missing coverage, and possible contradictions in
  `caveats` rather than smoothing them away.
- Do not return chain-of-thought. `rationale` must be a short,
  evidence-grounded explanation suitable for user review.

Return JSON with this shape:

```json
{
  "summary": "Short description of the proposal set",
  "claims": [
    {
      "statement": "An atomic proposition",
      "basis": "reported",
      "evidence": [
        {
          "evidence_id": "supplied-id",
          "stance": "supports",
          "rationale": "Short checkable explanation"
        }
      ],
      "tags": ["optional", "free-form"],
      "rationale": "Why this is a useful independent Claim",
      "caveats": ["Limits or missing Evidence"]
    }
  ]
}
```
