---
name: wiki-context-selection
description: Wiki · Select reference pages
stage: wiki_context_selection
contract_version: 1
---

Select existing Wiki pages worth reading before organizing the supplied batch of Claims.
Use the directory titles, hierarchy and summaries, not assumptions about unseen Claims.
Return at most five exact page_ids, most useful first. Prefer likely home pages,
overlapping concepts, and pages needed to distinguish similar topics. Return an empty
list if no existing page is relevant. Do not force five results or organize Claims yet.
The application will read a bounded sample of their Claims as reference-only context.
