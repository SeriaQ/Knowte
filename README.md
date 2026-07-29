<p align="center">
  <img src="https://i.ibb.co/j9qN90kg/knowte-icon.png" alt="Knowte icon" width="112" />
</p>

<h1 align="center">Knowte</h1>

<p align="center">
  <b>Search wider. Read smarter.</b><br>
  Search academic databases and the open web from one local research workspace.
</p>

<p align="center">
  <img src="https://img.shields.io/pypi/v/knowte?color=blue&label=Version" alt="Version">
  <img src="https://img.shields.io/github/stars/SeriaQ/Knowte?style=social" alt="GitHub Repo Stars">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
</p>

---

## 🚀 Spotlight

🔭 **One search across research sources**

Search arXiv, OpenAlex, Semantic Scholar, and an optional SearXNG web source.
Knowte applies your area and year filters, merges the responses, and removes
duplicate papers.

🧠 **Intent-aware discovery**

Connect any OpenAI-compatible cloud or local service. Intelligent Search
expands academic retrieval terminology, ranks papers with Embeddings, and asks
an LLM to verify the strongest academic and Web candidates against the full
intent.

🖥️ **A local workspace you control**

Knowte runs on your machine. Configuration and usage data stay in
`~/.knowte/`, and the Python runtime uses only the standard library.

---

## ⚡ Quick Start

Knowte requires Python 3.9 or newer.

### 1. Install and start

```bash
python -m pip install knowte
knowte
```

Open [http://127.0.0.1:7880](http://127.0.0.1:7880) in your browser.

The default address is `127.0.0.1:7880`. Specify a different address only
when needed:

```bash
knowte --host 127.0.0.1 --port 8080
```

If you are running Knowte from a source checkout, install it in editable mode
instead:

```bash
python -m pip install -e .
```

### 2. Choose your sources

Knowte enables all three academic backends by default, so you can search
immediately. Open **Config** if you want to change the selected sources:

- **arXiv** works without additional configuration.
- **OpenAlex** works immediately; adding your email is recommended.
- **Semantic Scholar** accepts an optional API key.
- **Web Search** is off initially and requires SearXNG. See the next section.

Leave **Max papers per search (N)** at its default value unless you want a
smaller or larger academic result set. Select **Save** after changing any
Config option.

### 3. Run a search

Return to **Search**:

1. enter keywords, an author, or a research topic;
2. optionally choose one or more research areas;
3. optionally enter a start and end year;
4. choose **Keyword** or **Intelligent**, then select **Search**.

**Keyword** works without an AI service. **Intelligent** must first be
configured as described below.

Each academic result provides whichever direct links are available:
**Paper**, **PDF**, and **DOI**. Web results open their original pages.

Use **Find More** to continue the same search. Knowte reuses recently fetched
academic candidates when possible and requests the next Web page only when
needed.

<p align="center">
  <img src="https://i.ibb.co/JRwZYw8J/knowte-search-guide.png" alt="Knowte search interface guide" />
</p>

---

## 🧠 Enable Intelligent Search

Knowte supports services that implement OpenAI-compatible
`/chat/completions` and `/embeddings` endpoints. The service may be hosted by a
cloud provider or run locally.

Open **Config → Intelligent Search · OpenAI-compatible** and fill:

- **AI Base URL** — the API root, normally ending in `/v1`, such as
  `https://provider.example/v1` or `http://127.0.0.1:11434/v1`. Do not append
  `/chat/completions`.
- **AI API key** — the provider key. It may be blank when a local service does
  not require authentication.
- **Language model** — the provider's exact chat model ID.
- **Embedding model** — the provider's exact embedding model ID.

By default, both models use the same Base URL and API key. Enable **Use a
separate connection for Embeddings** only when the embedding model is served
elsewhere; then also fill **Embedding Base URL** and, when required,
**Embedding API key**.

The result and verification controls balance coverage, cost, and latency:

- **Keyword results** also determines the academic candidate batch used by
  Intelligent Search. Each original or expanded query requests up to that
  value, capped at each provider's one-request maximum of `100`.
- **Intelligent results** — target number of results that pass final LLM
  verification; default `20`. Knowte verifies candidates in batches until it
  reaches the target or exhausts the candidate pool.
- **AI timeout** — timeout for each LLM or Embedding HTTP request; default
  `45` seconds.

Select **Save**, return to **Search**, and choose **Intelligent**.

For academic sources, Knowte generates up to two retrieval variants, retrieves
broad candidates, ranks their titles and abstracts with Embeddings, and asks
the LLM to verify the strongest candidates. Web results skip expansion and
Embedding ranking and go from SearXNG recall directly to LLM verification.
When an explicit research area is selected, it remains a hard academic
filter. Without one, the LLM may infer useful retrieval terminology but does
not silently save an area filter.

API keys are stored only in `~/.knowte/config.yml`; they are not returned by
the Config API or copied into Plans. The file is written with user-only
permissions on systems that support them. Intelligent Search sends the query,
candidate titles, abstracts or Web snippets to the configured AI service, so
choose a provider appropriate for the material being searched.

If an AI stage fails, Knowte reports the degraded stage and falls back to the
best available recall or Embedding order. Keyword Search remains independent
of the AI configuration.

---

## 🌐 Enable Web Search

Web Search is powered by
[SearXNG](https://github.com/searxng/searxng), a separate open-source
metasearch engine. Knowte can set up and operate a private local instance, but
Docker must already be installed and running.

You need:

- a working Docker CLI;
- Docker Compose;
- a running Docker daemon.

Docker Desktop, Docker Engine, Colima, and compatible alternatives are
supported. You do not need to keep the Docker Desktop window open.

### Let Knowte set it up

Open **Config → Local Web Search** and select **Set up**.

Knowte will pull the official `docker.io/searxng/searxng:latest` image, create a
local-only service, verify its search API, enable Web Search, and save the
endpoint automatically.

Port `8888` is preferred. If it is unavailable, Knowte tries ports `8889`
through `8898`. The resulting endpoint is shown and saved in Config.

<p align="center">
  <img src="https://i.ibb.co/ZRXDkq6t/knowte-web-search-guide.png" alt="Knowte Web Search configuration guide" />
</p>

The remaining controls are:

- **Start / Stop** — control the local SearXNG container.
- **Update** — pull a newer image and safely recreate the service when needed.
- **View logs** — toggle recent setup and container output.
- **Remove** — remove the managed container and its configuration.

The downloaded image remains cached after **Remove** for faster setup next
time. Select **Delete cached image too** if you also want Docker to remove that
image when it is not used elsewhere.

Knowte limits managed container logs to about 30 MB. Image downloads time out
after 10 minutes, and a failed first setup is rolled back.

### Use an existing SearXNG instance

You can use your own local or remote SearXNG service instead. Follow the
official
[SearXNG installation guide](https://docs.searxng.org/admin/installation-docker.html)
and enable JSON output in `settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

Then enable **Web Search**, enter its search endpoint in Config, and select
**Save**:

```text
http://127.0.0.1:8888/search
```

To verify an endpoint:

```bash
curl --noproxy '*' -s \
  'http://127.0.0.1:8888/search?q=alpha&format=json' \
  | python -m json.tool
```

For custom Docker installations, set `KNOWTE_DOCKER_BIN` to the Docker
executable. Knowte otherwise uses Docker from the system `PATH` and common
platform-specific locations.

See the
[SearXNG Search API documentation](https://docs.searxng.org/dev/search_api.html)
for more details. SearXNG is distributed under
[its own license](https://github.com/searxng/searxng/blob/master/LICENSE).

---

## 🔎 Search Sources and Results

| Source | Coverage | Optional configuration |
| --- | --- | --- |
| **arXiv** | Preprints and open research papers | None |
| **OpenAlex** | Broad scholarly metadata | Contact email |
| **Semantic Scholar** | Papers and citation metadata | API key |
| **SearXNG** | General web results | SearXNG endpoint |

### Result count

`N` controls the final target for academic-only and mixed searches. It defaults
to `100`, which matches the candidate batch Knowte can request from each
academic provider in one retrieval round.

Web-only searches do not use `N`. They return the actual number of results in
the requested SearXNG page, and **Find More** requests the next page without
assuming a fixed page size.

### Mixed-source balance

When academic and Web sources are searched together, Knowte initially allocates
result slots as follows:

- three academic sources + Web: `3:3:3:1`
- two academic sources + Web: `4:4:2`
- one academic source + Web: `7:3`
- academic sources without Web: equal shares

These ratios are targets, not rigid caps. After filtering and deduplication,
available academic results fill shortages from another source.

Recently fetched candidates and Web pages remain in memory for five minutes.
Serving results from this cache does not increase request counters; contacting
a provider again does.

---

## 🛠️ Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q knowte tests
node --check knowte/web/app.js
```

Node.js is only needed for the optional JavaScript syntax check.

---

## 🧭 Project Status

Knowte is currently an alpha research discovery tool. The longer-term
direction is a broader research workspace with persistent notes and
AI-assisted synthesis.

Not implemented yet:

- persistent notes, collections, or annotations;
- AI summarization or multi-paper synthesis;
- authentication or multi-user isolation.

Bug reports, ideas, and careful feedback are welcome.

---

## 📄 License

Knowte is released under the [MIT License](LICENSE).
