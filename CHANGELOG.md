# Changelog

All notable changes to Knowte will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-10-02

### Release highlights

- Continuous discovery through reusable Search and Subscribe Actions, multi-Action
  Plans, local scheduling, durable incremental Runs and independent consumption.
- An optimistic Evidence → Claims → Relations → Projected Wiki pipeline. Proposals
  remain pending; dependency tracking reconciles acceptance, revision and rejection.
- Feed-provided content is preserved for grounded Evidence generation instead of
  requiring a model to revisit inaccessible original URLs. Content may be excerpted.
- Model connection failures defer subsequent Evidence batches using that model.
  Run details expose stage progress, model usage, failures and retained work.

### Added

- GitHub public activity and selectable repository scopes, Hacker News keyword/user
  subscriptions for posts and comments, and Others for RSS/Atom, RSSHub and declared website
  feeds. Channel URLs are identified automatically after input; no social-login
  credentials or WeRSS deployment are managed. Scope is saved with each Channel
  and captured in Run history; Plan consumption remains independent.
- Optional, explicit local RSSHub Docker setup/start/stop/removal restricted to
  this library's owned container. Existing instances remain supported. Secrets are hidden in API responses and can be
  preserved, cleared, or redacted on Config export.

### Fixed

- Plan Search now pages past previously seen candidates to refill its new-candidate
  target, with a ten-page/provider bound, request quota accounting and explicit stop
  reasons. Partial fetch failures retain results without advancing that checkpoint.
- Completed Plan Runs notify only newly added or changed review items, not an
  unchanged backlog. Fast first Runs also refresh knowledge and review queues.
- Claim merge previews resolve existing Claim text instead of exposing internal
  identifiers. Knowledge-only Run details explicitly distinguish recomputation
  from discovery and Source capture.
- Cross-page Claim merges now keep one Wiki membership, turn other occurrences into
  links, and remap summary references without breaking unrelated links. Merges mark
  Wiki knowledge stale even when they happen within the same second as organization.
- Ignore actions explicitly target one draft or its pending draft chain, reject
  merge/revision conflicts, and cannot waive existing Wiki organization versions.
- Startup removes unreferenced Knowte Evidence PNGs under a database write lock,
  preserving current/history references, symlinks and manually named files. Cleanup
  failures are reported without preventing startup.
- Abrupt-process recovery is tested before/after acquisition commit, after proposal
  persistence and during review acceptance. Interrupted Runs warn that requests
  without persisted results may already have consumed model quota before retrying.

- Initialize the knowledge database before the local scheduler and HTTP handlers
  start together, preventing first-run WAL initialization lock conflicts.
- Refresh knowledge and review queues when a Plan finishes, and refresh Evidence
  proposals on navigation. Pending relation previews show Claim text instead of
  internal identifiers; Run details route revisions to Evidence-change review.
- Wrap Wiki import/export controls consistently on narrow screens and hide
  reviewed-organization call estimates in Projected view.
- Plans now describe the full optimistic pipeline instead of an outdated
  not-yet-connected Wiki notice; structured failure responses remain readable.

- Evidence acceptance now commits captures, related Sources, tags, annotations and
  downstream review dependencies together. Failed saves roll back database changes
  and remove only newly written snapshot files, leaving existing images intact.
- Claim proposal acceptance now commits the reviewed object, tags, proposal outcome,
  and downstream dependency changes together. Interrupted acceptance rolls back,
  including relation creation, Evidence linking, and Claim merges, so retrying does
  not leave a partially accepted knowledge chain.

### Added

- Subscribe now has an inline Channel form with Save. Each Channel is directly
  selectable in Plans; existing grouped Subscribe Actions and Run history remain
  compatible. Shared feed caching and independent Plan consumption are unchanged.
- Ignore downstream drafts rebases a pending Claim/relation dependency subtree in
  one transaction, without accepting it or clearing unrelated branches. Missing,
  stale external inputs or already-scheduled replacements block the whole operation.
  Existing Wiki organization snapshots remain unchanged.
- Non-overlapping Claim merge proposals now preview one combined identity in
  Projected Wiki. Input snapshots guard against outdated merges; Evidence and
  relation remapping match reviewed merge rules. Overlapping merges wait for review.
- Current AI Claim revisions can continue through relation discovery and Projected
  Wiki organization before review. The projected revision replaces its old version,
  without inheriting old semantic relations. Unchanged acceptance remaps downstream
  references; edits, Ignore and withdrawal invalidate affected projected knowledge.
- Reviewed Plan Claims affected by Evidence edits receive AI revision suggestions
  on a subsequent enabled Run, using their original model and Focus. Suggestions
  remain in Evidence-change review; formal Claims stay unchanged until acceptance.
  Version guards reject outdated responses, receipts prevent duplicate completed
  calls, and unsupported revisions remain for manual review.
- Stale pending Plan Claim drafts are grouped into replacement jobs on the next
  enabled Run, preserving original drafts and review status. Relation jobs can
  recompute current endpoints; replacement Claims rediscover their own relations.
  Recompute starts a knowledge-only Run without discovery or Source capture.
  Ignore impact explicitly rebases one pending draft when its inputs still exist;
  other impacted drafts remain untouched. Replacement links and status are visible.
- Projected Wiki structures can enter the existing editable Wiki Patch review
  workflow once their Claims are reviewed and current. Applying checks inputs again;
  discarding keeps the projection intact. Review provenance prevents an applied
  projection from resurfacing as an outdated replacement.
- Non-logical Evidence edits preserve downstream logical fingerprints while keeping
  the latest text available to readers/models; earlier stale dependencies remain
  stale. Legacy revision records keep their existing version semantics.
- Plans can organize a durable Projected Wiki with an explicit model, without
  changing reviewed pages or accepting proposals. Organization respects the Wiki
  batch limit and uses one call, or two with bounded reference-page selection.
  Version checks reject stale in-flight results; unchanged acceptance remaps links;
  changed/rejected dependencies hide affected summaries while preserving other
  pages. Run history retains projection provenance, retries and raw JSON failures.
- Optional Plan relation discovery continues from pending Claims using the existing
  Claim Audit skill, bounded nearby-pair retrieval and an explicit model. Atomic
  proposal/completion receipts, version checks, retry history and raw invalid-JSON
  output preserve review boundaries and avoid duplicate successful calls. Run
  details report the separate Relation stage; existing Plans leave it disabled.
- Wiki Reviewed only / Projected lens previews current pending Claims, Evidence-link
  updates and Claim relations without accepting them or modifying reviewed pages.
  Stale/invalidated branches are excluded; pending items link to their review queue.
  Automatic projected organization is separate from reviewed pages. Merge/revision
  conflicts are explicitly reported instead of silently applied.
- Plan Claim generation continues from pending or reviewed Evidence without
  auto-acceptance, using its own Focus/model and configured batch limit. Cross-Source
  batches reuse interactive Claim comparison and proposal generation. Durable
  receipts support retry/recovery; content-version checks prevent outdated model
  responses from becoming valid proposals when upstream Evidence changes mid-call.
- Plans can generate pending Evidence with an optional Focus and explicit model. Generation
  shares the interactive capture/native-document/URL-fetch service, respects
  Combined / One by one settings, keeps durable batch receipts and retries failed
  batches on a later Run without duplicating already-saved proposals. Per-Run
  generation history is retained.
- Versioned provisional proposal dependencies: pending Claims can reference pending
  Evidence without accepting it. Unchanged acceptance resolves references; edits
  or rejection mark affected descendants stale/invalidated, with retained review
  outcomes and acceptance guards throughout automatic Plan execution.
- Plan processing can automatically save selected discoveries to global Sources,
  with cross-Action deduplication, existing Source preservation, a per-Run new
  Source limit, and durable overflow processed by later Runs. Run history reports
  created/reused/deferred counts and links to Sources; Source details trace each
  discovery to its Plan, Run, Action version and provider or subscription.
  Existing Plans keep discovery-only behavior until explicitly enabled.
- Discover replaces Search in navigation, with Search / Subscribe / Import entries.
- Subscribe channel management, native RSS 2.0/Atom fetching and an optional RSSHub
  Base URL for adding routes. Subscribe Actions can share channels and run alongside
  Search Actions. ETag/Last-Modified fetching and persistent feed caches are shared,
  but each Plan consumes independently; Test fetch never advances Plan checkpoints.
- Reusable Search Actions and multi-Action manual Plans stored in SQLite. Existing
  saved search Plans migrate transactionally into Actions plus manual Plans;
  the original JSON file is retained. Actions support editing, version checks,
  checkpoint-free Test Run and reuse across independently tracked Plan associations.
- Local scheduling for every N hours, daily and weekly Plans, with IANA timezones,
  DST handling, durable next-run timestamps, catch-up-once and coalesced triggers.
  Pause/resume works during an active Run without interrupting it. Scheduling only
  runs while the Knowte server process is running; no cloud/background OS service.
- Manual Plan Runs with durable Action snapshots, provider checkpoints, shared
  identity aliases and independent per-Plan consumption. Repeated/undated results
  are deduplicated before AI Review; failed or unprocessed candidates remain queued.
  Run history includes results, errors and checkpoints. Failed provider requests no
  longer count as successful empty searches in this workflow. Current connectors
  use explicit user date filters only (not unsafe automatic publication-year windows).
  Processing policy controls continuation into Sources and knowledge proposals.
- Evidence edits can be marked as non-logical changes beside Save. The version
  history records this decision; earlier unresolved logical changes remain pending.
- Evidence-changed Claim reviews provide Ignore for explicitly non-logical edits,
  with version checks and persisted decision history. Deletion impacts cannot be
  ignored; neither action rewrites Claims or calls a model.

## [0.6.1] - 2026-09-24

### Added

- Related-paper discovery from saved academic Sources through references,
  citations and recommendations, with an optional Focus, model selection,
  retrieval caching and explicit coverage/rate-limit warnings.
- Named libraries: `knowte --new NAME` creates an isolated knowledge library
  with copied configuration and Skills; `--mount NAME` reopens it. The original
  library remains `default`, without moving existing data.
- Customizable stage Skills, with local files, folder reveal, reload and built-in
  fallback controls. Product rules, output contracts and review permissions remain
  application-owned.
- Local PDF, Markdown, TXT and DOCX import, with validation, editable titles and
  content deduplication. Wiki/Project exports include dependent original files.
- Evidence extraction from provider-native PDFs or URL access without requiring
  local text parsing. Config supports combined or per-Source requests; related-page
  selection adds one model call and supports up to ten pages.
- Web Evidence can preserve original embedded images and captions. Extraction
  reports page provenance, coverage gaps, truncation, failures and estimated calls.
- Versioned Evidence edits. Affected Claims enter a separate Evidence-changed
  review queue with before/after context and explicit confirmation or withdrawal.
- Tag/status filters, batch tagging and deletion for Sources and Evidence, with
  impact previews and themed confirmation dialogs. Tagging has no total item cap
  and is processed in internal batches.
- Scoped selection and batch decisions in review queues, including Keep selected
  disputed for eligible Claims. Failed items remain pending.
- Configurable proposal, Copilot context, Claim comparison and Wiki batch limits.
  Wiki organization prioritizes stale, unorganized, then other Claims; Wiki and
  Article generation default to 100 Claims.
- Claim proposals can suggest new–new and new–existing relations in the same model
  call. Relations have independent review and persisted endpoint dependencies;
  discarded endpoints explicitly block application.
- Claim Audit discovers missing relations and proposes corrections or removals
  of existing links. Candidate counts and estimated calls are shown before running;
  findings require review.
- Independent Claim Graph with compact stable clusters, Page/relation filters,
  pan, pinch/modifier-wheel zoom, Fit, one-hop focus and selected-Claim details.
  Unconnected Claims are separate; Page hierarchy does not determine placement.
- Wiki Reset clears organization and pending structure drafts after confirmation,
  preserving Claims, Evidence, Sources, Projects and Articles.
- Lightweight Article editing, paragraph-citation editing and formatted preview.

### Changed

- Search and Import replace the Keyword/Intelligent/Import switch. AI Review is
  independent of Discuss; existing Plans and defaults preserve their review behavior.
- Search focuses on academic providers. Generic SearXNG Web Search is no longer
  exposed; webpages remain supported through Import and Web Companion.
- Search and related-paper discovery share Strong / Possible / Excluded review
  levels. Results support relevance, year and citation-count sorting.
- Discuss and Import guidance reflect academic retrieval and Source exploration;
  Import no longer displays or copies irrelevant search filters.
- Ordinary Config saves detect obsolete settings and ask before removing them.
- Claim comparison retrieves candidates per Evidence with round-robin coverage,
  reports truncation and stays within the same proposal call.
- Wiki Claims have one home Page; other Pages link to them without duplicating
  membership. Partial organization selects reference pages from summaries before
  reading bounded Claim samples, with one/two-call estimates.

### Fixed

- Wiki Edit, Apply and Discard avoid redundant reloads and hidden Graph rendering.
  Local requests have bounded timeouts, independent loading and visible retry/error
  feedback; late responses do not overwrite newer decisions or unsaved drafts.
- Empty Wiki patches explain Reset; empty review queues are disabled. Confirmed
  batch decisions disappear immediately, with partial-failure progress.
- Claim text no longer clips at rounded corners. Evidence, Claims and review
  previews render formulas while preserving editable original text.
- Model selections refresh after Config saves; dropdown arrows and theme styling
  remain consistent. Proposal selection/progress and cross-tab counts stay in sync.
- Project Wiki previews preserve knowledge gaps. Saved Articles retain citations,
  render Markdown and survive Project export/import with remapped Claim IDs.
- Imported arXiv/DOI links are recognized as papers. Exploration normalizes arXiv
  identifiers, reports actual sampling/assessment counts and distinguishes failed
  retrieval from genuinely empty results.
- Normal scrolling passes over Graph without zooming; clicking a selected node
  again clears selection and exits focused mode.

## [0.6.0] - 2026-08-27

### Added

- Projects now provide one shared global Claim selector for manual inclusion
  and model-assisted, reviewable Claim recommendations.
- Projects can organize their Claims into a durable, reviewable mini-Wiki and
  keep goal-specific generated Articles that can be reopened for reading.
- Config can apply an outgoing HTTP/SOCKS proxy to a Knowte-managed SearXNG
  instance.
- The global Wiki and individual Projects can be exported as portable ZIP
  packages containing readable Markdown, structured provenance JSON, a
  versioned manifest, and included Snapshot Evidence images.
- Wiki packages can be reviewed once in Wiki and merged with their complete
  page structure and dependent knowledge; Project packages remain isolated in
  a Project review. The two package types cannot be cross-imported.
- Config can be exported with API keys and other stored secrets redacted by
  default.
- Managed SearXNG setup falls back from Docker Hub to the official GitHub
  Container Registry when the primary image pull fails.
- Wiki structure can be edited as a persistent reviewable Patch, including
  nested Pages, canonical Claim placement, and direct navigation to Claims.

### Changed

- Projects explicitly include only Claims; supporting Evidence and Sources are
  derived through Claim provenance rather than selected as Working Materials.
- New installations ignore the year filter for Web Search by default so
  undated Web results are not silently excluded.
- Web results now trust SearXNG's relevance ranking instead of requiring every
  literal query token to appear in each result title or snippet.
- User documentation now reflects the complete Source-to-View workflow,
  current AI model routing, Claim auditing, and browser companion behavior.
- Every reviewed active Claim belongs to the global Wiki automatically;
  unassigned knowledge appears under Unorganized instead of an incoming queue.
- Article generation now belongs to Projects and uses only the selected
  Project's Claims.
- Local client disconnects no longer print misleading server tracebacks after
  a capture or other request has already completed its work.
- Wiki Pages and Claims can be reordered or nested by drag and drop, with
  precise button controls retained as a fallback.
- The deterministic Claim Graph now uses relation-driven two-dimensional
  placement, directional edges, compact nodes, and stable neighborhood
  highlighting.

### Fixed

- Discarding a Wiki edit draft no longer temporarily hides the accepted Wiki.
- Wiki Patch Claim rows no longer clip long text or overflow horizontally.
- Claim Graph nodes no longer jump when hovered.

## [0.5.1] - 2026-08-26

### Added

- Evidence cards provide a consistent magnifying-glass action for opening the
  full Evidence detail view.
- Selected Evidence can receive Tags in one batch without replacing Tags
  already attached to individual items.
- Selected Claims can receive Tags in one batch from the list controls shared
  with Select all.
- Evidence and Claims use dedicated, composable Any-of and All-of Tag menus
  with consistent selection counts.
- Proposed Claims show their grounding Evidence and link back to the matching
  item in the Evidence workspace.
- Claim proposal runs compare likely existing Claims for duplicates,
  contradictions, and related knowledge before presenting reviewable changes.
- Claims can be audited across the entire Library or a Tag-defined scope, with
  a local candidate preview, bounded model batches, and resumable progress.

### Changed

- Cross-stage AI proposals now leave the user in the working Tab, show a
  spinner there while processing, and notify the destination Tab when review
  results are ready instead of forcing an immediate navigation.
- Claims Select all now sits below the Manual Claim editor and stays out of
  the action toolbar and proposal-review state.
- Wiki organization now requires explicitly incoming Claims, reports progress
  on the Views Tab, and no longer silently falls back to every active Claim.
- Claim proposal runs accept up to 30 selected Evidence items.
- Search actions use a more compact height, and the Claim audit entry is
  visually distinguished from routine Claim actions.

### Fixed

- Copilot context-status messages no longer overlap the first chat response in
  the compact review panel.
- Evidence card open actions retain their compact icon treatment, and the
  batch Tag control no longer shifts the Evidence toolbar when selection changes.
- Rounded gradient buttons no longer expose a hard-colored edge at their
  right boundary.

## [0.5.0] - 2026-08-25

### Added

- Search strategy discussion with up to five editable, source-specific
  Academic/Web retrieval actions.
- Third-party Source import for human-curated links, DOI/arXiv identifiers, and
  structured external-LLM results, plus a dynamic copyable import prompt.
- One purpose-neutral global Wiki over accepted Claims, with persistent,
  reviewable AI Wiki Patches and legacy Wiki migration.
- Deterministic Claim Graph rendering from accepted Claim relations, without
  model-authored graph structure.
- Goal-driven temporary Articles for which the model selects and organizes
  relevant Claims across the global Wiki, with an explicit option to save the
  result as Project content.
- Reusable AI model Profiles with per-stage model assignment, independent
  proxy routing, write-only credentials, and distinct adapters for OpenAI,
  Gemini, Anthropic, DeepSeek, Qwen, Kimi, generic OpenAI-compatible APIs, and
  custom JSON request recipes.
- Focus-guided AI Evidence proposals grounded in one or more selected Sources,
  with persistent awaiting-review queues shared by Evidence and Claims.
- Provider-aware document paths covering native PDF input, hosted file
  extraction, URL context, and native Web Search where the configured service,
  model, and endpoint have a documented Knowte adapter.
- Web Companion quick capture with an adaptive floating control, text-first and
  region-first capture modes, keyboard shortcuts, inline Tag and Annotation
  editing, and theme-aware presentation on external pages.

### Changed

- Intelligent Search now uses the user's query directly by default instead of
  silently generating retrieval expansions.
- Search strategy editing uses compact source-specific cards, and follow-up
  Copilot discussion can propose a complete replacement for explicit review.
- Search strategy generation now separates provider-ready queries from their
  retrieval purpose and adds domain examples selected for the active Area
  filters, with dedicated guidance across major AI subfields.
- Review Copilot now uses distinct system prompts for Search, Sources,
  Evidence, Claims, Views, and Projects, all visible by stage in Config.
- Copilot Search suggestions are previewed and appended as editable waiting
  candidates; only the ordered Top 5 actions are executed or saved to a Plan.
- Copilot stage prompts now include exact JSON response contracts; common local
  model JSON deviations are repaired, with a text-only fallback for chat.
- Copilot chat supports Command/Ctrl+Enter sending and per-workspace input
  history; Search candidates move directly between the active list and waiting
  list with a guarded five-item active limit.
- Multi-line Copilot drafts reserve arrow keys for text navigation, while
  Search-list transfers use directional icons and a two-pulse full-list alert.
- Import can be selected as the persisted default Search mode, and the manual
  strategy control is labeled as adding a new query.
- Views now separates durable Wiki organization, deterministic relationship
  exploration, and transient purpose-specific synthesis instead of treating
  Wiki, Article, and Graph as peer saved formats.
- AI Evidence and Claim generation now shows the active model at the point of
  use and preserves malformed structured responses as visible model output
  instead of silently issuing a second paid request.
- Claim proposals synthesize across the selected Evidence set, can relate new
  Evidence to existing Claims, and keep Rationale and optional Caveats visible
  throughout review.
- Model capabilities are split into Chat, Embeddings, Native PDF, File
  extraction, Web Search, and URL fetch. Unsupported combinations are locked
  from both the interface and configuration API instead of trusting arbitrary
  capability checkboxes.
- Review queues now open as focused list states with consistent awaiting-review
  controls, and accepted entities return to their normal workspace lists.

### Fixed

- Evidence proposals navigate to the awaiting-review list after completion and
  preserve the raw response when required JSON cannot be parsed.
- Source inspection, Evidence review, and model selection controls retain
  usable dimensions and consistent visual hierarchy across light and dark
  themes.
- Qwen multi-PDF handling no longer assumes an undocumented request contract;
  unsupported multi-document combinations fall back to captured Source text.
- Temporary Kimi file-extraction uploads are deleted after their content is
  retrieved so they do not accumulate against the user's file quota.

## [0.4.0] - 2026-08-09

### Added

- First Claims vertical slice with Evidence-backed propositions, controlled
  Basis, review state, and Lifecycle fields, revision history, Claim relations,
  Tags, Annotations, and optional Project links.
- A global Evidence workspace for selecting Evidence across Sources and
  creating manual or AI-assisted Claims.
- Versioned AI Claim-proposal instructions and a visual review queue whose
  awaiting proposals persist across page refreshes and Knowte restarts until
  the user explicitly accepts, keeps as disputed, or discards them.
- Distinct Search, Sources, Evidence, Claims, and Views workspaces with explicit
  forward handoffs, visible Incoming trays, and preserved return-to-draft flows.
- Wiki and Article documents composed from persistent Heading, Paragraph, and
  Claim-reference blocks, plus an interactive Claim graph with node details.

### Changed

- Refined the Sources-to-Views funnel with clearer manual and LLM proposal
  actions, a focused Source reader, and more coherent Claims and Views controls.
- Standardized compact Copilot context controls and lightened Claim and View
  handoff actions while preventing wrapped navigation labels.
- Renamed the Copilot selection action to `Add to context` to distinguish chat
  context from entity selection.
- Simplified Claim Basis to Background, Reported, or Inference; replaced the
  editable Standing field with explicit Accepted and Disputed review outcomes;
  and reduced Evidence–Claim stances to Supports, Contradicts, or Limits.
- Renamed the user-facing Artifact concept to Project while preserving the
  existing storage and API identifiers for compatible upgrades.
- Reduced Claim–Claim relations to Supports, Contradicts, or Related; retired
  relation types are dropped during migration instead of being reinterpreted.

## [0.3.0] - 2026-08-02

### Added

- SQLite-backed global Source Library and Purpose-driven Artifacts.
- Search result collection with global deduplication and optional Artifact
  linking.
- Initial Library and Create views forming the first Collect-to-Artifact
  workflow.
- Persisted Keyword or Intelligent default-mode selection.
- Search-side Review panel with current Artifact and Library collection status.
- Expandable Artifact Source references in the Create view.
- Offline PDF.js Source Viewer preserving original pages, figures, tables, and
  multi-column layout.
- Text Evidence from PDF or captured HTML selections, plus Snapshot Evidence
  from user-selected PDF regions.
- Source- and Evidence-level Annotations in the contextual Review workspace.
- Global free-form Tags for Sources, Evidence, and Artifacts, with
  controlled entity-type validation and migration from the retired Evidence
  Group prototype.
- Content-addressed Source captures and secure same-origin serving of captured
  files and Evidence snapshots.
- Clean Reader for captured Web Sources and original-layout PDF inspection.
- Knowte Web Companion for capturing pages, selected text, and screen regions
  from original webpages into the Library and optional Artifacts.
- Context-aware Review Copilot with compact and expanded chat workspaces,
  selectable Source and Evidence context, multimodal Snapshot Evidence, and
  configurable instructions and generation parameters.

### Changed

- Artifact selection now describes optional linking instead of presenting the
  global Library as if it were an Artifact destination.
- Search-mode controls use clearer grouping, separation, and default markers.
- Saved Source counts are visible from Search and the Library navigation item.
- Search result actions consistently save to Library, with optional Artifact
  linking reported as a secondary effect.
- Keyword and Intelligent result state is isolated when switching modes.
- Intelligent results report final source distribution, and non-empty result
  lists always provide a working return-to-top action.
- Search, Library, and Source inspection now share a persistent contextual
  Review workspace for collection, Evidence, Annotation, Tag, and Copilot
  actions.
- Config is organized by Search, AI Models, Review Copilot, Source
  Connections, and Web Companion instead of presenting unrelated settings as
  one search-backend group.

### Fixed

- Source inspection preserves the current PDF page and zoom position across
  Evidence and Annotation actions.
- Review controls remain usable in narrow layouts without clipping or
  horizontal overflow.
- Review Copilot resolves saved Sources and Evidence from the knowledge store,
  attaches Snapshot image content, and no longer duplicates the current user
  question in recent conversation history.

## [0.2.0] - 2026-07-30

### Added

- OpenAI-compatible Chat Completions and Embeddings clients supporting shared
  or separate cloud and local connections.
- Production Intelligent Search pipeline with academic query expansion, broad
  recall, cached batch Embeddings, semantic ranking, and LLM verification.
- Web Intelligent Search path that skips academic expansion and Embeddings and
  proceeds directly from SearXNG recall to LLM verification.
- Per-result discovery paths, match explanations, semantic scores, actual AI
  request counts, retrieval-round counts, and visible degraded-stage fallbacks.
- Write-only AI and Embedding API key configuration with user-only config-file
  permissions where supported.
- Locally persisted search Plans that store intent, filters, mode, and logical
  source selection while continuing to use current Config credentials and
  service endpoints.
- Plans view for loading, running, renaming, editing the query, and deleting
  reusable searches.
- Configurable AI request timeout, verification batch size, verification
  concurrency, and model thinking behavior.
- Live Intelligent Search stage progress, elapsed time, and visible expanded
  retrieval queries.

### Changed

- Intelligent Search now runs directly from Search instead of opening an
  intermediate Search Plan dialog.
- Plans uses a direct **Go to Search** action instead of the ambiguous
  **Save Current** action.
- Keyword and Intelligent result targets are configured independently.
- Academic candidate retrieval is derived automatically from the Keyword
  result target and each provider's one-request maximum.
- LLM verification now proceeds in batches until it reaches the Intelligent
  result target or exhausts the candidate pool.
- Academic providers run concurrently within each retrieval query while
  original and expanded queries remain sequential to reduce rate-limit risk.
- Intelligent Search progress now follows the actual order: semantic
  expansion, recall, semantic ranking, and LLM verification.

### Fixed

- Intelligent Search no longer appears to remain in Recall while later AI
  stages are running.
- Verification fallback messages distinguish embedding-ranked, academic
  recall, and Web recall results.
- Local OpenAI-compatible endpoints bypass system proxies when appropriate.

### Removed

- The previous interpreted-query Search Plan dialog.
- Manual Academic candidate and LLM verification candidate limits.

## [0.1.0] - 2026-07-28

### Added

- Local browser interface with Search and Config views.
- Unified search across arXiv, OpenAlex, and Semantic Scholar.
- Optional Web Search through an existing or Knowte-managed SearXNG instance.
- Research-area and publication-year filters mapped across academic providers.
- Cross-source result deduplication and source-aware result allocation.
- Direct Paper, PDF, and DOI actions when supplied by academic sources.
- Pagination with short-lived academic candidate and Web page caches.
- Independent five-minute and daily request limits for academic and Web
  channels.
- Local configuration and usage storage under `~/.knowte/`.
- Configurable academic sources, result count, OpenAlex contact email, Semantic
  Scholar API key, SearXNG endpoint, and Web year-filter behavior.
- Automated local SearXNG setup, start, stop, update, log viewing, and removal
  through Docker Compose.
- SearXNG port conflict handling, setup timeouts, health checks, rollback, image
  cleanup controls, and container log rotation.
- Auto, Light, and Dark interface themes with saved user preference.
- Python 3.9–3.12 support and a standard-library-only Python runtime.

### Changed

- Academic sources are enabled by default; Web Search is enabled automatically
  after successful local SearXNG setup.

### Fixed

- Empty SearXNG language parameters are no longer sent.
- Knowte can restart immediately on the same local port after shutdown.
- Docker Desktop credential helpers are discoverable without assuming a
  platform or Docker distribution.
- Repeated searches recover correctly after an empty or failed Web response.
- SearXNG logs wrap and remain contained within the Config panel.
