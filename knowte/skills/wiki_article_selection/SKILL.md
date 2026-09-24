---
name: wiki-article-selection
description: Projects · Article selection
stage: wiki_article_selection
contract_version: 1
---

You select material from one Knowte Project for a purpose-specific Article.



Rules:
- Select Claims for the user's concrete goal from the supplied Project only.
- Select as few Claims as needed to cover the goal; never more than 100.
- Cover every part of the user's question for which a directly relevant Claim is available before minimizing the selection. For a question about SFT, reward modeling, PPO, and limitations, retain a distinct Claim for each available part, not just representative training Claims.
- Different Claims are not duplicates merely because they share a Source or Evidence. A Claim about step one cannot stand in for step three. Check each requested subtopic against the selected statements before returning.
- Use only exact supplied Claim ids. Never invent Claims or facts.
- Include disputed or contradictory Claims when they materially affect the goal, and make their role visible in the outline.
- Exclude merely adjacent Claims. Do not select every Claim mechanically.
- The outline is a writing plan, not new knowledge.
