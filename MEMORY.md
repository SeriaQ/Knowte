# Knowte Project Memory

Last verified: 2026-07-23 (Asia/Shanghai)

## Workspaces and release authority

- The release-authority repository is on the original machine at `/root/proj/Knowte`.
- The active development copy is `/Users/seria/Documents/Knowte`.
- The development copy is exported without `.git`; this is intentional.
- All Git operations, package builds, and PyPI uploads happen on the original machine.
- The local machine is authoritative for development, runtime configuration, and testing.
- Primary development uses Python 3.12; Python 3.9 remains the minimum supported runtime and is covered by compatibility tests.
- Local application configuration and usage data live in the local machine's `~/.knowte`.
- The original machine needs only the source tree and the tooling required to build and upload a release; it does not need Knowte runtime configuration.
- Machine-specific workflow details belong in this internal file, not in the user-facing README.

## Current Product Scope

Knowte is currently a working pre-alpha research search aggregator with a browser UI. It is not yet the full AI research notebook described aspirationally in the README.

Implemented capabilities:

- Search aggregation across arXiv, OpenAlex, Semantic Scholar, and SearXNG web search.
- Configurable enabled backends, OpenAlex email, Semantic Scholar API key, SearXNG URL, and maximum result count.
- Area presets mapped to provider-specific categories/concepts/fields.
- Year-range filtering, result deduplication, pagination, incremental "Find More", and request cancellation in the UI.
- Separate paper and web usage counters and rate limits.
- Paper limits: 100 requests per 5 minutes and 5000 per UTC day.
- Web limits: 10 requests per 5 minutes and 500 per UTC day.
- Theme switching and configuration UI.
- Empty queries are rejected without consuming usage quota.
- Semantic Scholar API keys are never returned by the config API; the UI can replace or explicitly clear a saved key.
- In-process locking protects usage counter updates made by the threaded server.

Not implemented:

- Persistent notes, collections, annotations, or research workspaces.
- AI summarization or multi-paper synthesis.
- Authentication, multi-user separation, or production deployment hardening.

## Important Behavior

- `knowte/usage.py` stores paper and web usage independently.
- A request containing paper and web backends increments both counters once.
- A paper-only request ignores exhausted web quota.
- A web-only request ignores exhausted paper quota.
- If `websearch` is enabled but `searxng_url` is empty, `/api/search` removes `websearch` from the effective backends and returns `warnings: ["websearch_unconfigured"]`.
- Removing unconfigured web search must not increment web usage.
- When web quota is exhausted but paper backends remain, search continues without web and returns `websearch_rate_limited`.
- The UI distinguishes paper rate limiting, web rate limiting, and unconfigured web search.
- Paper year ranges are sent to arXiv, OpenAlex, and Semantic Scholar before local validation.
- Paper provider requests are capped at 100 results per call to stay within current API page limits.
- OpenAlex area selections are added to its text query; provider concept display names are not sent as `concepts.display_name` filters because that currently produces empty responses.
- `N` is the final target for academic-only and mixed searches. Post-filter/post-dedup allocation uses 3:3:3:1 for three academic sources plus Web, 4:4:2 for two plus Web, 7:3 for one plus Web, and equal academic shares without Web.
- Academic candidates fill Web shortages and shortages from other academic providers. Web-only searches ignore `N` and return the actual SearXNG page results.
- Find More increases the academic target when academic sources are active and requests the next SearXNG page when Web is active. Web page sizes come from each response rather than an assumed count; an empty actual page ends Web pagination.
- Successful Web page payloads are cached in process for five minutes (maximum 128 query/page entries), so cumulative Find More requests only fetch newly requested pages.
- Abstracts can be hidden or shown without re-running a search.
- The single result pager lives in a sticky toolbar and is hidden until results span more than one 20-item page.
- The Config UI suggests `http://127.0.0.1:8888/search` for SearXNG on first use; it is persisted and activated only after Save.
- Config shows in-panel saving, success, and failure feedback.
- Config and its API reject attempts to save with no search backend selected.
- Successful Config save feedback clears after one second; unsaved changes mark its navigation tab.
- Config can exempt Web Search from year filtering while retaining strict year filtering for academic providers.
- Web Search diagnostics distinguish unavailable SearXNG, invalid JSON, and results removed by active filters. Loopback SearXNG requests bypass environment proxies.
- Web Search omits the `language` query parameter when no language is configured. SearXNG 2026.7 rejects an explicitly empty `language=` with `SearxParameterException`.
- README documents SearXNG as an optional external prerequisite for Web Search and links to its official installation and API documentation.
- With a working Docker CLI and daemon, Config can create and manage a labeled `knowte-searxng` container under `~/.knowte/searxng/`, bound only to `127.0.0.1:8888`.
- Managed SearXNG controls support setup, start, stop, restart, logs, and confirmed removal. They refuse an unmanaged container name conflict.
- The threaded HTTP server enables address reuse before binding and uses daemon request threads, allowing immediate restart on the same port after Ctrl+C.
- Managed setup reuses a compatible SearXNG already on port 8888 or selects an available port from 8888-8898, persists the chosen endpoint, checks Docker Compose, serializes lifecycle operations, protects generated files with owner-only permissions, and rolls back a failed first attempt.
- Managed SearXNG Setup and Update run as pollable background tasks. The UI shows phase and elapsed time while copying Docker's merged stdout/stderr into the log panel without parsing version-dependent progress formats.
- Background task logs retain prefixed Knowte phase transitions, request plain Docker Compose progress, and report when setup reused a locally cached image.
- Update compares exact image IDs after pulling. An already-current image does not recreate the container; a changed image is applied and health-checked before a non-forced removal of only the replaced image ID. Images still used elsewhere are retained, and Knowte never runs a global prune.
- SearXNG health checks use the local `/healthz` endpoint instead of issuing a real search. This avoids generating upstream CAPTCHA/rate-limit errors merely from status polling.
- View logs toggles open and closed, reads the latest 500 lines through a merged stdout/stderr stream to preserve order, wraps long lines, and explains that individual upstream-engine errors do not necessarily indicate a failed local service.
- Managed containers use Docker `json-file` log rotation with `max-size: 10m` and `max-file: 3`. Update recreates an image-current container once when needed to apply this configuration.
- Remove retains the current image cache by default. Its explicit **Delete cached image too** option non-forcibly removes only the exact image ID used by the managed container and reports when Docker retains an image still used elsewhere.
- Set up automatically persists the managed endpoint and enables Web Search; it first saves any other unsaved Config edits so the post-setup refresh cannot discard them.
- Image pulls have a 10-minute timeout and container creation has a separate 2-minute timeout. First-setup failures and timeouts use the same rollback path while preserving Docker's downloaded layer cache.
- Docker subprocesses prepend Docker Desktop and `~/.docker/bin` helper directories to PATH so credential helpers work even when the user's shell or virtual environment does not expose Docker CLI paths.
- Docker discovery is platform-layered: `KNOWTE_DOCKER_BIN`, system PATH, user locations, then macOS/Windows/Linux standard candidates. Subprocesses inherit Docker contexts, proxy/certificate variables, and `DOCKER_CONFIG`; Docker Desktop is not required.
- Search responses report final result counts by source. When Web Search is combined with a year filter, the UI explains that undated web results are excluded.
- Frontend static asset version is `20260724b` in `knowte/web/index.html`.

## Key Files

- `knowte/server.py`: static server and `/api/health`, `/api/config`, `/api/usage`, `/api/search`, `/api/searxng`, and `/api/searxng/job` endpoints.
- `knowte/searxng.py`: Docker discovery and lifecycle management for Knowte's labeled local SearXNG container.
- `knowte/search.py`: provider orchestration, filtering, deduplication, and result serialization.
- `knowte/usage.py`: persistent counters and quota decisions.
- `knowte/config.py`: simple YAML-like configuration stored at `~/.knowte/config.yml` by default.
- `knowte/providers/`: provider adapters.
- `knowte/web/`: browser UI.
- `tests/test_usage.py`: independent quota and counter regression tests.
- `tests/test_server.py`: API regression test for unconfigured web search.

## Verification

Run from either workspace root:

```bash
python -m unittest discover -s tests -v
python -m compileall -q knowte tests
node --check knowte/web/app.js
```

Verified on 2026-07-23:

- All 44 automated tests pass on Python 3.12.13 and Python 3.9.6.
- JavaScript syntax checking passes.
- API tests use an ephemeral local server, temporary config and usage files, mocked search results, and no external network.

## Known Limitations and Risks

- Usage locking is in-process only; running multiple Knowte server processes against the same usage file is unsupported.
- Rate-limit checking and request recording are separate operations, so simultaneous requests near a limit can temporarily overshoot it.
- Provider behavior is not covered by automated contract tests and depends on external APIs.
- Academic-provider HTTP and timeout failures are still converted to empty lists; Web Search failures now have explicit diagnostics.

## Next Priorities

1. Surface provider failures separately from genuine zero-result searches.
2. Make quota admission and recording atomic if strict enforcement is needed.
3. Add provider contract tests using saved fixtures.
4. Define the next product milestone before adding notebook or AI synthesis features.

## Change Discipline

- Keep changes surgical and tied to an explicit request.
- Add a reproducing test before fixing a bug when practical.
- Do not perform Git or PyPI operations in the exported development copy.
- Update this file after material behavior, verification, path, or priority changes.
