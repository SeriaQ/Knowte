# 📡 Following channels

Use **Discover → Subscribe** to save Channels, then add them directly to a Plan.
Choose **GitHub**, **Hacker News**, or **Others**, then enter its address (HN also accepts keywords or a username). Identification
starts automatically after a short pause, without an LLM call. Review the scope,
optionally **Test & preview**, then **Save Channel**. A preview shows up to five
examples per group and never advances Plan consumption state.

## GitHub

Channels also appear under **Plans → Actions**. Select Search / Channel Actions,
switch to Plans and **Open Plan**, then use the right panel's **Add selected Actions
to this Plan**. Existing entries are skipped and new ones append to the order.

Use **Edit** on a Channel to change connector-specific scope, name, Focus or model.
Choose **No model** to disable verification, or a model to filter unconsumed items against Focus in Plan Runs, using the same
Strong / Possible / Excluded tiers as Search (Strong and Possible continue).
It sees titles and provided excerpts / comment text, not automatically full articles.
Preview / Test Fetch does not call a model. Set the suggested model in
**Config → Model roles → Subscribe · AI Verify**, or select one on Subscribe.
Saved Channels retain their chosen model until edited.

Edits affect every Plan referencing the Channel. Existing Run snapshots and per-Plan
consumption remain; changing Focus does not reverify already-consumed items. Scope
edits reset the shared fetch cache, not consumption history. Active Runs must finish
before editing the Channel.

- Account URL, such as `https://github.com/SeriaQ`: public account activity.
  Choose event types such as issues, pull requests, pushes or stars. This is not
  a feed of all changes in every repository owned by that account.
- Repository URL, such as `https://github.com/pytest-dev/pytest/`: choose
  **Releases**, **Commits**, **Issues**, and/or **Pull Requests**. All start
  unchecked; select at least one before previewing or saving. Commits optionally
  take a branch name; blank uses the repository default branch. Releases include
  prereleases but not drafts or bare tags. Issue/PR replies and code diffs are not fetched.

Both use the official API. Config's optional token raises rate limits; no private
repository or write permissions are needed. Account events expose at most 300
recent events within 30 days. Releases read at most 15 pages of 20 per fetch.
Commits, Issues and Pull Requests each scan at most five pages of 20. The Issues
API includes PRs, which Knowte removes from that stream, so fewer than 100 Issues
may remain. These are bounded recent windows, not full archives. Account event
types also start unchecked.

Each API response is limited to 2 MiB. Oversized responses stop the fetch and
show an explanation in Subscribe or Plan Run warnings; partial results are not
saved and the failed channel's checkpoint does not advance. Existing cached
items remain intact. Identification, preview and saved Channels display the
bounded retrieval scope so a successful fetch is not mistaken for a full archive.

## Hacker News

There are exactly two modes:

- **Keywords**: enter a query such as `reinforcement learning`.
- **User**: enter a case-sensitive username or its HN profile URL, such as
  `https://news.ycombinator.com/user?id=simonw`.

Both use HN Search by Algolia to fetch **Posts** and **Comments** separately,
newest first, up to 100 each (five pages of 20). Previews show separate groups.
No account, key or model call is required. User existence is checked through the
official HN API. Keyword matching searches indexed HN text, not linked articles'
full text or semantic topics; indexing may be delayed or incomplete.

Posts link to their external article when available. Comments retain their own
HN item URL and excerpt, so multiple comments on a post do not merge into it.
If either stream fails, no partial fetch is committed.

Bounded windows can roll over between Runs. Persistent caching
and independent per-Plan deduplication prevent repeat consumption, but cannot
recover entries never fetched. Choose a schedule appropriate for channel volume.

## Others · RSS / RSSHub

Paste a complete RSS/Atom URL, a complete RSSHub feed URL, or a website URL.
Websites are checked for declared same-site feeds, not crawled exhaustively.
Multiple feeds offer a choice; if none is found, supply a direct Feed URL.

**Config → Subscription Connectors → RSSHub** provides Base URL and optional
local Docker Setup/Start/Stop/Remove and **Reinstall**. **Use local address** selects
`http://127.0.0.1:1200`; append the desired route when supplying a complete feed
URL in Subscribe.

Knowte does not install Docker. Managed setup uses a library-owned loopback-only
container with memory caching and no social-login credentials. Removal preserves
Channels, Sources, config and downloaded image layers. The service keeps running
after Knowte closes. Port 1200 must be free; multiple libraries cannot each bind
their own managed instance to that same port simultaneously.

For routes requiring credentials, click **Create environment file** in Config.
Use the dialog to create or edit the file using Docker env-file syntax,
one `KEY=value` per line, without shell `export` or surrounding quotes. For X,
the variable is `TWITTER_AUTH_TOKEN`. Keep the file private. Knowte does not obtain
browser cookies or manage the upstream login. Docker administrators can inspect
container environment variables.

Save in the dialog, then **Reinstall** to rebuild the existing managed RSSHub using
its installed image and the saved file. Setup also loads this file. **Delete file**
asks for confirmation; reinstalling afterward removes custom variables. The service briefly stops and loses
temporary feed cache; Channels, Sources and Plans remain. The old container is
retained if replacement startup fails. Test the Feed afterward: container startup
does not guarantee that platform authentication works. The file contents are never in
config exports. Legacy external paths are no longer loaded: copy their settings into
the dialog before reinstalling; the original file is not modified. Docker networking is separate from model
API proxy settings. Managed port and memory-cache settings cannot be overridden.

## Safety and existing installations

Knowte no longer manages WeRSS, WeChat authorization or X login cookies. Old
dedicated X/WeChat Channels show an unsupported-connector error; replace them with
direct feeds in Others if available. Existing RSS Channels, Sources, Run history
and independent Plan consumption state are retained.

Previously saved GitHub Releases Channels keep their original scope. Old HN
listing Channels are explicitly unsupported; replace them with keyword or user
Channels. An existing Channel's scope is never silently overwritten by saving a
duplicate address; use its explicit Edit action.

Saving Config removes obsolete WeRSS/X fields. This does **not** stop/remove
previously created containers, local data, sessions or `rsshub/service.env`
files. Clean those up separately if you enabled those unreleased integrations.
Recreate old RSSHub containers to remove their injected credentials.

The optional GitHub token stays in local config and is not returned in Config
responses. Blank input preserves it; **Remove saved token** clears it on save.
Use masked config export for sharing, and never share private feed URLs.

## Upstream references

- [RSSHub deployment](https://docs.rsshub.app/deploy/)
- [GitHub activity events](https://docs.github.com/en/rest/activity/events)
- [GitHub Releases](https://docs.github.com/en/rest/releases/releases#list-releases)
- [GitHub Commits](https://docs.github.com/en/rest/commits/commits#list-commits)
- [GitHub Issues](https://docs.github.com/en/rest/issues/issues#list-repository-issues)
- [GitHub Pull Requests](https://docs.github.com/en/rest/pulls/pulls#list-pull-requests)
- [HN Search API](https://hn.algolia.com/api)
- [Official Hacker News API](https://github.com/HackerNews/API)
