<p align="center">
  <img src="https://i.ibb.co/j9qN90kg/knowte-icon.png" alt="Knowte icon" width="112" />
</p>

<h1 align="center">Knowte</h1>

<p align="center">
  <b>From sources to grounded knowledge.</b><br>
  A local-first workspace for finding information, extracting evidence,
  reviewing claims, and building reusable understanding with AI.
</p>

<p align="center">
  <img src="https://img.shields.io/pypi/v/knowte?color=blue&label=Version" alt="Version">
  <img src="https://img.shields.io/github/stars/SeriaQ/Knowte?style=social" alt="GitHub Repo Stars">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
</p>

---

## ✨ What Knowte does

Knowte turns learning into an inspectable knowledge chain:

> Sources → Evidence → Claims → Wiki

- **Find or import Sources.** Search arXiv, OpenAlex, and Semantic Scholar;
  import links or structured results; then follow citations and academic-graph
  recommendations from Sources you trust.
- **Read and ground.** Inspect saved papers and webpages, then preserve exact
  text passages or visual regions as Evidence.
- **Distill with review.** Write Claims manually or let a model propose them.
  Every AI proposal remains pending until you accept, keep as disputed, or
  discard it.
- **Organize and create.** Every reviewed active Claim belongs to the global
  Wiki. Projects select a topic-specific subset and generate focused Articles.

The durable knowledge database and captured content stay on your machine. AI
and search services are contacted only for features you explicitly configure
and use.

---

## ⚡ Quick Start

Knowte requires Python 3.9 or newer.

### 1. Install and run

```bash
python -m pip install knowte
knowte
```

Open [http://127.0.0.1:7880](http://127.0.0.1:7880). Running `knowte` is all
that is required for the default local address and port.

Specify them only when needed:

```bash
knowte --host 127.0.0.1 --port 8080
```

To try a clean, separate knowledge library:

```bash
knowte --new learning
```

Open [http://127.0.0.1:7880](http://127.0.0.1:7880). This library stores its data
in `~/.knowte/learning/` and copies your configuration (including API keys) and custom
skills on creation, but no existing knowledge or Plans. Open it again with
`knowte --mount learning`. Run `knowte` (or `knowte --mount default`) to use
the original `default` library, which stays in `~/.knowte/` without moving files.
`--new` rejects existing directories; `--mount` rejects missing libraries, and the
two options cannot be combined. Replace `learning` with your own
name (letters, numbers, underscores or hyphens). Model calls are real and may
incur costs. Companion needs separate pairing with this address.
With `--config PATH`, the named folder is created alongside that configuration;
`--port` (or `PORT`) overrides the default port of 7880 for every library.
To run two libraries at once, assign different ports, e.g.
`knowte --mount learning --port 7881`.

From a source checkout, use:

```bash
python -m pip install -e .
knowte
```

### 2. Find something

The three academic backends are enabled by default, so the first search needs
no account or AI configuration.

1. Enter a topic, title, author, or keywords in **Search**.
2. Optionally choose research areas and a year range.
3. Leave **AI Review** off and click **Search**.
4. Select useful results in the list. The Review panel tracks the selection.
5. Click **Add selected Sources** to save them to the global Source Library.

Use **Find More** to continue the same retrieval. Knowte reuses cached academic
candidates when possible before making another provider request.

<p align="center">
  <img src="https://raw.githubusercontent.com/SeriaQ/Knowte/main/docs/images/knowte-workflow-search.jpg" alt="Knowte Search workspace with Intelligent Search, filters, usage channels, and Review workspace" />
  <br><em>Search directly, discuss a retrieval strategy, or import results from elsewhere.</em>
</p>

### 3. Build the knowledge chain

1. Open **Sources**, select a saved Source, and use the magnifying-glass action
   to inspect it.
2. To expand from trusted papers, select one to three Sources, optionally enter
   a Focus under **Explore related papers**, and review the Strong, Possible,
   and Excluded candidates found through references, citations, and graph
   recommendations.
3. Select text or capture a region to create precise Evidence. You can also
   select one or more Sources, enter a focus, and choose
   **Propose Evidence via LLM**. For documentation websites, **Related pages**
   discovers navigation/sitemap links and uses one extra model call to select
   relevant pages (up to ten total). Combined extraction uses two calls;
   one-by-one uses N + 1, where N is the selected page count. This is not a
   full-site crawl. Review shows each page's actual origin; new Sources are
   saved only when you accept their Evidence.
4. Open **Evidence** to review material across Sources. Select items within the
   limit configured in **Config → Knowledge stages**,
   then write a Claim manually or choose **Propose Claims via LLM**.
5. Open **Claims** to accept, keep disputed, revise, relate, tag, or withdraw
   Claims. Reviewed active Claims enter the global Wiki automatically; select
   a subset when you want to add it to the active Project.
6. Open **Wiki** and choose **Organize with AI** to structure reviewed Claims
   in batches (100 by default), or switch to **Graph** to inspect accepted Claim relations. Use
   **Projects** to collect a topic-specific subset and generate an Article.

Tab spinners show work still running. A notification beside a destination Tab
means a proposal is ready for review; opening that review queue clears the
notification.

---

## 🧭 The workflow

### Search

Search has two entry points:

- **Search** retrieves from the enabled academic backends. Optional **AI Review**
  adds embedding ranking (when configured) and LLM relevance verification.
- **Import** accepts URLs, DOI or arXiv identifiers, and Knowte's structured
  JSON format. **Copy suggested prompt** provides instructions you can give to an
  external LLM.

  **Upload documents** accepts PDF, Markdown, TXT, and DOCX (up to 20 MB each).
  Choose or drop files, edit their titles, then import them into Sources. Files
  are parsed before saving; unsupported, unreadable, or empty documents are
  rejected. PDFs retain their pages, including scanned pages for region capture;
  Markdown/TXT and DOCX use a text reading view, not full original formatting.
  Text files must use UTF-8 or UTF-16. Image-only DOCX should be exported to PDF.
  Duplicate file contents reuse the existing Source. Uploaded originals travel
  with Wiki/Project packages when their Sources are included.

With AI Review either on or off, **Discuss** calls the Search Copilot to propose focused
academic retrieval queries. You can continue the conversation, edit the
proposals, and move candidates into or out of the Top 5 Search list. The
confirmed Search list—not the unchanged text in the input—is then executed.
With AI Review off, candidates are searched directly and results deduplicated,
without embedding or LLM review. Discuss itself still uses the model API.
Old Keyword Plans/defaults map to AI Review off; Intelligent ones map to on.

Filters apply to every retrieval action. **Save Plan** preserves reusable
search conditions; Plans currently run manually and use the credentials and
service endpoints currently saved in Config.

### Sources

A Search result becomes durable only after it is added to the global Source
Library. A Source preserves what was encountered; model output never silently
becomes or rewrites a Source.

- PDFs open in the built-in reader with their original pages.
- Web Sources open in a clean reading view, with **Original web** available
  when native layout or interaction matters.
- **Refresh** captures the latest accessible content again.
- Tags and Annotations can be attached without changing the captured Source.
- **Explore related papers** follows references, citations, and academic-graph
  recommendations from one to three selected Seed Sources. An optional Focus
  guides the shared Strong / Possible / Excluded relevance review.
  Retrieval is sampled, not exhaustive; the result summary distinguishes retrieved
  and assessed candidates and flags unavailable paths. Retrieval responses are
  cached for 15 minutes while Knowte is running, and rate limits trigger a cooldown.
  Running Explore again still performs a new model review of available candidates.

Sources remain globally shared. Projects select reviewed Claims; their
supporting Evidence and Sources follow automatically through provenance.

<p align="center">
  <img src="https://raw.githubusercontent.com/SeriaQ/Knowte/main/docs/images/knowte-workflow-sources.jpg" alt="Knowte Sources workspace with saved papers, Evidence proposal controls, and contextual Review workspace" />
  <br><em>Saved Sources remain global while the active workspace supplies stage-specific actions.</em>
</p>

### Evidence

Evidence is an addressable excerpt or snapshot grounded in a Source. It can be
created directly while inspecting material or proposed from selected Sources
by an AI model.

AI-proposed Evidence includes its quotation, location, rationale, and any
material caveat. It stays in **Awaiting review** until accepted or discarded.
Accepted Evidence can be opened back at its Source location, tagged in batches,
annotated, edited with version history, and reused across Claims. Editing linked
Evidence returns affected Claims to an **Evidence changed** review queue.

### Claims

A Claim is an atomic proposition that can be examined and revised. Claims use
three user-facing bases:

- **Background** — accepted prior knowledge intentionally kept without local
  Evidence;
- **Reported** — stated directly by linked Evidence;
- **Inference** — derived from one or more Evidence items.

Evidence may **support**, **contradict**, or **limit** a Claim. Claim-to-Claim
relations are **supports**, **contradicts**, or **related**.

Claim proposals consider the selected Evidence together and compare likely
existing Claims before suggesting new Claims, links, revisions, or relations.
Relations may connect new drafts to each other or to existing Claims. Accept their
endpoint Claims first, then review the relations; batch acceptance handles this order.
The proposal report shows what was considered and what was skipped. Proposed
changes do not enter the knowledge base until reviewed.

Use **Audit Claims** when you want a broader consistency pass. An audit can
cover the entire Library or an Any-of / All-of Tag scope. Knowte first builds a
local set of likely pairs, shows the expected number of model batches, and then
lets you start, pause, resume, or cancel the review. Its findings enter the
same proposal queue rather than changing Claims automatically. It also discovers
missing relations and reviews existing links for correction or removal. This is
a candidate-based check, not an exhaustive comparison of every possible pair.

### Wiki and Projects

These are two projections over the same global knowledge objects:

- **Wiki** is one global, purpose-neutral encyclopedia containing every
  reviewed active Claim. New Claims appear under **Unorganized** until a
  reviewed structural patch assigns them to Pages.
- **Graph** is rebuilt deterministically from accepted Claims and their
  relations, independently of Page hierarchy. Filter by Page or relation type,
  select a node to inspect its connections, and use **Focus selected** or **Fit**.
  Drag to pan; pinch or hold Ctrl (Windows/Linux) / Cmd (macOS) while scrolling
  to zoom. Click the selected node again to deselect. No model calls are needed.
- **Project** selects Claims for one topic and Purpose. Supporting Evidence and
  Sources follow through Claim provenance.
  Open a Project to filter the global Claim pool by text, Any-of Tags, and
  All-of Tags. Add Claims manually or use **Recommend Claims** to ask a selected
  model for a reviewable shortlist from that exact same scope. Organize the
  accepted subset into a reviewable Project Wiki, or generate and save Articles
  around a specific reading goal without mechanically using every Claim.
  Article generation happens inside a Project and uses only that Project's
  Claims.

### Export knowledge

Export the global Wiki from **Wiki**, or export one topic-specific Project from
**Projects**. Each ZIP contains readable Markdown, machine-readable JSON, a
versioned manifest, complete upstream provenance, and included Snapshot
Evidence images.

Import Wiki and Project packages through their matching workspace; Knowte
rejects a package opened in the wrong place. A Wiki package receives one
complete review in **Wiki**, then its page tree and all dependent Sources,
Evidence, and Claims are deduplicated and merged into the global knowledge
base. A Project package opens as an isolated Import Review Project; none of its
knowledge is accepted until you approve it there.
These portable packages support sharing and archival snapshots, but a full
copy of `~/.knowte/` remains the complete application backup.

---

## 🧠 Configure AI

AI is optional. Search with AI Review off and manual knowledge work remain available
without it.

Open **Config → AI Models**:

1. Add one **Model profile** for every model or endpoint you want to use.
2. Choose its provider, Base URL, exact model ID, optional API key, proxy
   routing, and available capabilities.
3. Under **AI roles**, assign an exact profile to Embeddings, Search
   (AI Review / Discuss), Review Copilot, Evidence, Claims, Wiki, and Article generation.
4. Save Config.

Knowte includes adapters for OpenAI-compatible endpoints, OpenAI, Google
Gemini, Anthropic, DeepSeek, Alibaba Model Studio / Qwen, Moonshot / Kimi, and
advanced Custom Recipes. A local OpenAI-compatible Base URL commonly ends in
`/v1`, for example:

```text
http://127.0.0.1:8000/v1
```

Do not append `/chat/completions`. Enter the exact model ID served by the
endpoint; it is not an arbitrary display name.

Capabilities are conservative and provider-specific. Depending on the adapter
and model, Knowte can send extracted text, multiple native documents, source
URLs, or provider web-search tools. Unsupported capability controls remain
unavailable. **Custom Recipe** is the advanced escape hatch for a documented
request format that does not fit a built-in adapter.

Each profile can use automatic routing, the system proxy, a direct connection,
or a custom proxy. Automatic routing keeps local endpoints direct and lets
public endpoints use the system proxy.

The Review Copilot is contextual to the active Tab and selection. Its compact
panel can expand into the main workspace for detailed context management.
Custom instructions and supported request parameters are configurable; stage
prompts remain separate so Search discussion, Evidence extraction, Claim
review, and Wiki maintenance do not share the wrong task contract.

In **Config → Stage skills**, select a stage and choose **Create custom copy** to create
an editable `~/.knowte/skills/<stage>/SKILL.md`. **Show in Finder / Open folder**
opens its location; **Reload** validates your edits and refreshes the preview.
Edits apply to the next request. **Use built-in** disables the custom version
without deleting it; **Use custom** reactivates it. Knowte updates do not
overwrite your files.

Keep the `stage` and `contract_version` metadata in the file. Incompatible
versions block the affected stage until you update the Skill or select the
built-in version. Product rules and output contracts are read-only: a custom
Skill changes methods and preferences, not object types, review permissions,
or accepted output fields. Invalid model output is shown for inspection without
an automatic retry. Search Skills also include editable, Area-specific examples;
arbitrary scripts and other referenced files are not executed or loaded.

API keys are stored in `~/.knowte/config.yml`, are exposed to the UI only as
configured / not configured, and are never copied into Plans. Choose providers
appropriate for the Sources, Evidence, Claims, and conversation context you
send them.

---

## 🧩 Knowte Web Companion

The bundled browser extension lets you create Sources and Evidence while
reading an original webpage. Chromium browsers and Firefox are supported for
local loading.

1. Start Knowte and open **Config → Knowte Web Companion**.
2. Choose **Copy extension path**.
3. Open the browser's extension page and load that folder:
   - Chromium: `chrome://extensions`, enable Developer mode, then
     **Load unpacked**.
   - Firefox: `about:debugging#/runtime/this-firefox`, then load the extension's
     `manifest.json` temporarily.
4. In a native folder picker, press `⌘⇧G` on macOS or `Ctrl+L` on
   Windows/Linux to paste the copied path directly.
5. Generate a temporary pairing key in Knowte and enter it in the extension
   within five minutes.

On a webpage, select text or start a capture from the floating Knowte control.
The default shortcuts are `Alt+Shift+K` for text and `Alt+Shift+X` for a
region; browser extension settings can remap them. The inline editor lets you
choose a destination, add Tags or an Annotation, and save without leaving the
page. **Save page** stores only the current webpage as a Source.

Knowte must be running when the extension pairs or saves. An already loaded
extension does not need to be reinstalled after ordinary Knowte restarts.

---

## 🔎 Search sources and result limits

| Source | Coverage | Optional configuration |
| --- | --- | --- |
| **arXiv** | Preprints and open research papers | None |
| **OpenAlex** | Broad scholarly metadata | Contact email recommended |
| **Semantic Scholar** | Papers and citation metadata | API key |

**Search results (AI Review off)** defaults to `100`. It is the initial academic target and
the increment used by **Find More**. Academic providers cap a single request at
`100`, so Knowte caches surplus candidates and avoids another provider request
while usable cached results remain.

**AI-reviewed results** defaults to `20` and controls how many Strong or
Possible candidates may pass final model verification. Excluded candidates
remain available in a folded section for inspection. The same three levels are
used by Source-based related-paper discovery.

---

## 🔒 Local data

By default, Knowte stores its durable state under `~/.knowte/`:

- `config.yml` — configuration and locally stored credentials;
- `knowte.db` — Sources, Evidence, Claims, relations, Tags, Annotations,
  Projects, review proposals, and Wiki state;
- `content/` — captured documents, webpages, and snapshots;
- `plans.json` — saved Search Plans;
- `usage.json` — local request and token counters.

The browser UI has no authentication or multi-user isolation. Keep the default
loopback host unless you intentionally want to expose Knowte on another
interface.

---

## 🛠️ Development

```bash
uv pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q knowte tests
node --check knowte/web/app.js
```

Node.js is needed only for the optional JavaScript syntax check.

---

## 🚧 Project status

Knowte is alpha software. The core local workflow, contextual Review Copilot,
AI proposal queues, global Wiki, Claim graph, Article generation, Projects,
Tags, Annotations, saved Plans, and browser companion are implemented and
evolving.

Scheduled or recurring Plans, authentication, and multi-user isolation are not
implemented yet. Expect data models and UI details to continue changing before
a stable release.

Bug reports, ideas, and careful feedback are welcome.

---

## 📄 License

Knowte is released under the [MIT License](LICENSE).
