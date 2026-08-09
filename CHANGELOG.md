# Changelog

All notable changes to Knowte will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
