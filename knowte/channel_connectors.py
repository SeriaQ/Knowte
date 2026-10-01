"""URL recognition and bounded acquisition; no model calls or implicit subscriptions."""
from __future__ import annotations

from html import unescape
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .subscriptions import parse_feed, validate_feed_url

URL_KEYS = ("rsshub_base_url",)
SECRET_KEYS = ("github_token",)
MAX_BYTES = 2 * 1024 * 1024
RELEASE_PAGE_SIZE = 20
RELEASE_MAX_PAGES = 15


class ChannelResponseTooLarge(ValueError):
    """A safe, credential-free failure message that can be shown in Run history."""


def fetch_scope(kind):
    if kind == "github_repo":
        return "Choose at least one scope. Releases: up to 300; Commits, Issues and Pull Requests: scan up to 100 records each, 20 per page (Issues excludes PRs, so fewer may remain). 2 MiB per response. Bounded recent history, not a full archive; issue/PR replies and code diffs are not fetched."
    if kind == "github_releases":
        return f"Bounded fetch: up to {RELEASE_MAX_PAGES} pages / {RELEASE_PAGE_SIZE * RELEASE_MAX_PAGES} Releases, {RELEASE_PAGE_SIZE} per page, 2 MiB per response. Multiple requests may take time. Older releases may be omitted; this is not a full archive."
    if kind == "github":
        return "Bounded fetch: up to 300 recent public events, 2 MiB per response. Not a complete activity history."
    if kind in {"hn_keyword", "hn_user"}:
        return "HN Search by Algolia: up to 100 posts and 100 comments, fetched separately, 20 per page. Indexed HN text only, not linked-article full text. Results may lag or omit older matches; no model call."
    if kind == "hackernews":
        return "Legacy HN listing is no longer supported. Replace it with a keyword or user Channel."
    return "Feed window only, not a complete archive."


def public_settings(config):
    return {**{key: config.get(key, "") for key in URL_KEYS},
            **{key + "_configured": bool(config.get(key)) for key in SECRET_KEYS}}


def update_settings(config, payload):
    result = dict(config)
    for key in ("werss_mode", "werss_base_url", "werss_token", "rsshub_twitter_auth_token",
                "rsshub_twitter_consumer_key", "rsshub_twitter_consumer_secret"):
        result.pop(key, None)
    for key in URL_KEYS:
        if key in payload:
            value = str(payload[key] or "").strip().rstrip("/")
            if value:
                validate_feed_url(value)
                if urlsplit(value).query or urlsplit(value).fragment:
                    raise ValueError("Service Base URLs cannot contain query strings or fragments")
            result[key] = value
    for key in SECRET_KEYS:
        if payload.get("clear_" + key):
            result.pop(key, None)
        elif payload.get(key):
            value = str(payload[key]).strip()
            if any(ord(c) < 32 for c in value):
                raise ValueError("Credentials cannot contain control characters")
            result[key] = value
    return result


def _read(url, *, token="", method="GET", data=None, request_kind="rss"):
    validate_feed_url(url)
    origin = urlsplit(url)[:2]
    class SameOriginRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            validate_feed_url(newurl)
            if urlsplit(newurl)[:2] != origin:
                raise ValueError("Cross-origin redirect blocked; use the final public URL")
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    headers = {"User-Agent": "Knowte Channels", "Accept": "application/json, application/atom+xml, application/rss+xml, text/html"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = None if data is None else json.dumps(data).encode()
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        handlers = [SameOriginRedirect()]
        if urlsplit(url).hostname in {"127.0.0.1", "localhost", "::1"}:
            handlers.append(ProxyHandler({}))
        from .usage import record_subscription_request
        record_subscription_request(request_kind)
        with build_opener(*handlers).open(Request(url, data=body, headers=headers, method=method), timeout=30) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ChannelResponseTooLarge("Fetch stopped: one response exceeded the 2 MiB safety limit. No partial results from this fetch were saved; existing cached items are unchanged. Use a smaller feed or import specific items separately.")
            return raw
    except HTTPError as error:
        code = error.code
        error.close()
        if code in {401, 403}:
            raise ValueError("Access denied. Check connector authentication and platform restrictions") from None
        if code == 429:
            raise ValueError("Platform rate limit reached. Retry later") from None
        raise ValueError(f"Channel request returned HTTP {code}") from None
    except OSError:
        raise ValueError("Channel connection failed. Check the service address, network and proxy") from None


def _json(url, **kwargs):
    try:
        return json.loads(_read(url, request_kind="subscription_api", **kwargs))
    except (json.JSONDecodeError, UnicodeError):
        raise ValueError("Connector returned invalid JSON") from None


def recognize(url):
    url = validate_feed_url(url)
    parts = urlsplit(url)
    host = parts.hostname.lower()
    path = parts.path.strip("/").split("/")
    if host in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        raise ValueError("X login is not managed by Knowte. Supply a direct RSS / RSSHub feed URL in Others")
    if host == "github.com":
        if path[0].lower() in {"trending", "topics", "collections", "explore", "search", "marketplace", "features", "settings", "login", "signup"}:
            raise ValueError("Use a GitHub account or repository URL. Trending and other directory pages are not supported")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", path[0]):
            raise ValueError("Use a GitHub account or repository URL")
        if len(path) in {2, 3} and re.fullmatch(r"[\w.-]+", path[1]) and (len(path) == 2 or path[2] in {"releases", "commits", "issues", "pulls"}):
            repo = path[0].lower() + "/" + path[1].removesuffix(".git").lower()
            return {"kind": "github_repo", "account": repo, "source_url": "https://github.com/" + repo}
        if len(path) != 1:
            raise ValueError("Use a GitHub account or repository URL")
        return {"kind": "github", "account": path[0].lower(), "source_url": "https://github.com/" + path[0].lower()}
    if host == "news.ycombinator.com":
        if parts.path.strip("/") == "user":
            return hn_spec("user", parse_qs(parts.query).get("id", [""])[0])
        raise ValueError("HN listings are no longer supported. Choose Keyword or User subscription")
    if host == "mp.weixin.qq.com":
        raise ValueError("WeChat login is not managed by Knowte. Supply a direct RSS feed in Others, or import this article")
    return {"kind": "feed", "source_url": url}


class FeedLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and "alternate" in attrs.get("rel", "").lower().split() and attrs.get("type", "").lower() in {"application/rss+xml", "application/atom+xml"}:
            self.links.append((attrs.get("href", ""), attrs.get("title", "Feed")))


def hn_spec(mode, value):
    value = str(value or "").strip()
    if mode == "user":
        if value.startswith(("http://", "https://")):
            parts = urlsplit(value)
            if parts.hostname != "news.ycombinator.com" or parts.path != "/user":
                raise ValueError("Enter an HN username or its user profile URL")
            value = parse_qs(parts.query).get("id", [""])[0]
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
            raise ValueError("Enter a valid HN username")
        return {"kind": "hn_user", "account": value, "source_url": "https://news.ycombinator.com/user?" + urlencode({"id": value})}
    if mode != "keyword" or not value or len(value) > 200 or any(ord(c) < 32 for c in value):
        raise ValueError("Enter keywords (1–200 characters)")
    return {"kind": "hn_keyword", "query": value, "source_url": "https://hn.algolia.com/?" + urlencode({"query": value, "sort": "byDate", "type": "all"})}


def detect(url, config, category=None, hn_mode="keyword"):
    spec = hn_spec(hn_mode, url) if category == "hackernews" else recognize(url)
    kind = spec["kind"]
    expected = {"github": {"github", "github_repo"}, "hackernews": {"hn_keyword", "hn_user"}, "others": {"feed"}}
    if category is not None and (category not in expected or kind not in expected[category]):
        raise ValueError("URL does not match the selected channel type. Choose GitHub, Hacker News or Others")
    if kind in {"hn_keyword", "hn_user"}:
        if kind == "hn_user":
            profile = _json("https://hacker-news.firebaseio.com/v0/user/" + spec["account"] + ".json")
            if not isinstance(profile, dict) or profile.get("id") != spec["account"]:
                raise ValueError("HN user not found; usernames are case-sensitive")
        spec["name"] = "HN · " + (spec.get("query") or "@" + spec["account"])
        return {"choices": [spec], "message": fetch_scope(kind)}
    if kind == "github_repo":
        repo = _json("https://api.github.com/repos/" + spec["account"], token=config.get("github_token", ""))
        if not isinstance(repo, dict) or not repo.get("id") or repo.get("private"):
            raise ValueError("Public GitHub repository could not be verified")
        spec.update(name=repo.get("full_name") or spec["account"], scopes=[], branch="")
        return {"choices": [spec], "message": fetch_scope(kind)}
    if kind == "github":
        profile = _json("https://api.github.com/users/" + spec["account"], token=config.get("github_token", ""))
        if not isinstance(profile, dict) or not profile.get("id"):
            raise ValueError("GitHub profile could not be verified")
        spec.update(name=profile.get("name") or profile["login"], platform_id=str(profile["id"]),
                    event_types=[])
        return {"choices": [spec], "message": "Public account activity, not all repository updates. GitHub exposes up to 300 recent events within 30 days; updates can be delayed."}
    raw = _read(url)
    try:
        parse_feed(raw, url, "Feed")
        return {"choices": [{**spec, "name": urlsplit(url).hostname}], "message": "RSS / Atom feed detected. Test to preview entries."}
    except (ValueError, ET.ParseError):
        pass  # A website may declare feeds instead of being a feed itself.
    parser = FeedLinks()
    parser.feed(raw.decode("utf-8", errors="replace"))
    choices, seen = [], set()
    for href, title in parser.links[:12]:
        candidate = urljoin(url, href)
        if candidate in seen or urlsplit(candidate)[:2] != urlsplit(url)[:2]:
            continue
        seen.add(candidate)
        try:
            parse_feed(_read(candidate), candidate, title)
        except (ValueError, ET.ParseError):
            continue
        choices.append({"kind": "feed", "source_url": candidate, "name": title})
        if len(choices) == 5:
            break
    return {"choices": choices, "message": "Choose a declared feed." if choices else "No usable same-site RSS/Atom feed found. Supply a direct Feed URL or a configured RSSHub route."}


def clean_spec(payload):
    kind = payload.get("kind")
    if kind in {"hn_keyword", "hn_user"}:
        return hn_spec("keyword" if kind == "hn_keyword" else "user", payload.get("query") if kind == "hn_keyword" else payload.get("account"))
    if kind == "hackernews":
        raise ValueError(fetch_scope(kind))
    if kind not in {"github", "github_repo", "github_releases", "feed"}:
        raise ValueError("Unsupported channel connector. Replace old X / WeChat Channels with a direct RSS feed in Others")
    spec = recognize(payload.get("source_url", ""))
    if kind == "github_releases" and spec["kind"] == "github_repo":
        # Preserve explicitly saved pre-scope Release Channels; new Channels never default to Releases.
        spec["kind"] = kind
    if spec["kind"] != kind:
        raise ValueError("Channel URL does not match its connector")
    if kind == "github_repo":
        scopes = payload.get("scopes", [])
        if not isinstance(scopes, list) or not scopes or any(s not in {"releases", "commits", "issues", "pulls"} for s in scopes):
            raise ValueError("Choose at least one repository scope: Releases, Commits, Issues or Pull Requests")
        branch = str(payload.get("branch") or "").strip()
        if len(branch) > 200 or any(ord(c) < 32 for c in branch):
            raise ValueError("Invalid branch name")
        spec.update(scopes=sorted(set(scopes)), branch=branch if "commits" in scopes else "")
    if kind == "github":
        allowed = {"CreateEvent", "ReleaseEvent", "IssuesEvent", "PullRequestEvent", "PushEvent", "WatchEvent", "ForkEvent"}
        events = payload.get("event_types", [])
        if not isinstance(events, list) or not events or any(e not in allowed for e in events):
            raise ValueError("Select supported GitHub event types")
        spec["event_types"] = sorted(set(events))
        spec["platform_id"] = str(payload.get("platform_id", ""))
    return spec


def acquire(spec, config, name):
    spec = clean_spec(spec)
    if spec["kind"] in {"hn_keyword", "hn_user"}:
        return _hackernews(spec, name)
    if spec["kind"] == "github_repo":
        results = []
        for scope in spec["scopes"]:
            results.extend(_releases(spec, config, name) if scope == "releases" else _repository_items(spec, config, name, scope))
        return results
    if spec["kind"] == "github_releases":
        return _releases(spec, config, name)
    if spec["kind"] == "feed":
        url = spec["source_url"]
        return parse_feed(_read(url), url, name)
    results = []
    for page in range(1, 4):
        items = _json(f"https://api.github.com/users/{spec['account']}/events/public?per_page=100&page={page}", token=config.get("github_token", ""))
        if not isinstance(items, list):
            raise ValueError("GitHub returned an invalid event list")
        for event in items:
            if event.get("type") not in spec["event_types"]:
                continue
            repo = (event.get("repo") or {}).get("name", "")
            if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
                continue
            payload = event.get("payload") or {}
            detail = payload.get("release") or payload.get("issue") or payload.get("pull_request") or {}
            url = detail.get("html_url") or f"https://github.com/{repo}"
            head = payload.get("head") or payload.get("after") or ""
            if event["type"] == "PushEvent" and re.fullmatch(r"[a-fA-F0-9]{40}", head):
                url = f"https://github.com/{repo}/commit/{head}"
            if urlsplit(url).hostname != "github.com" or urlsplit(url).scheme != "https":
                continue
            title = f"{event['type'].removesuffix('Event')} · {repo}"
            if detail.get("title") or detail.get("name"):
                title += " · " + str(detail.get("title") or detail.get("name"))
            results.append({"id": str(event.get("id", "")), "title": title, "url": url, "paper_url": url,
                            "authors": spec["account"], "abstract": str(detail.get("body") or payload.get("action") or title)[:20000],
                            "published_at": event.get("created_at", ""), "year": None, "source": name, "result_type": "web"})
        if len(items) < 100:
            break
    return results


def _releases(spec, config, name):
    results = []
    for page in range(1, RELEASE_MAX_PAGES + 1):
        try:
            items = _json(f"https://api.github.com/repos/{spec['account']}/releases?per_page={RELEASE_PAGE_SIZE}&page={page}", token=config.get("github_token", ""))
        except ChannelResponseTooLarge:
            raise ChannelResponseTooLarge(f"GitHub Releases fetch stopped on page {page}: a {RELEASE_PAGE_SIZE}-release response exceeded 2 MiB, often due to asset metadata or long release notes. No partial results from this fetch were saved; existing cached items are unchanged. Import specific release URLs instead.") from None
        if not isinstance(items, list):
            raise ValueError("GitHub returned an invalid release list")
        for item in items:
            url = item.get("html_url", "")
            if item.get("draft") or urlsplit(url).hostname != "github.com" or urlsplit(url).scheme != "https":
                continue
            results.append({"id": str(item["id"]), "title": f"{spec['account']} · {item.get('name') or item.get('tag_name')}",
                            "url": url, "paper_url": url, "authors": (item.get("author") or {}).get("login", ""),
                            "abstract": str(item.get("body") or "")[:20000], "published_at": item.get("published_at", ""),
                            "year": None, "source": name, "result_type": "web"})
        if len(items) < RELEASE_PAGE_SIZE:
            break
    return results


def _repository_items(spec, config, name, scope):
    results = []
    for page in range(1, 6):
        params = {"per_page": 20, "page": page}
        if scope == "commits":
            if spec["branch"]:
                params["sha"] = spec["branch"]
        else:
            params.update(state="all", sort="created", direction="desc")
        items = _json(f"https://api.github.com/repos/{spec['account']}/{scope}?" + urlencode(params),
                      token=config.get("github_token", ""))
        if not isinstance(items, list):
            raise ValueError("GitHub returned an invalid repository item list")
        for item in items:
            # GitHub's Issues API also includes pull requests; never mislabel them.
            if scope == "issues" and "pull_request" in item:
                continue
            url = item.get("html_url", "")
            if urlsplit(url).hostname != "github.com" or urlsplit(url).scheme != "https":
                continue
            commit = item.get("commit") or {}
            text = str(commit.get("message") or "") if scope == "commits" else str(item.get("body") or "")
            title = text.split("\n", 1)[0] if scope == "commits" else str(item.get("title") or "")
            results.append({"id": scope + ":" + str(item.get("sha") or item["id"]),
                            "title": f"{scope.title()} · {spec['account']} · {title}",
                            "url": url, "paper_url": url, "authors": (item.get("user") or item.get("author") or {}).get("login", ""),
                            "abstract": text[:20000], "published_at": (commit.get("committer") or {}).get("date", "") if scope == "commits" else item.get("created_at", ""),
                            "year": None, "source": name, "result_type": "web", "channel_item_type": scope})
        if len(items) < 20:
            break
    return results


def _hackernews(spec, name):
    results = []
    for item_type in ("story", "comment"):
        for page in range(5):
            params = {"tags": item_type, "hitsPerPage": 20, "page": page}
            if spec["kind"] == "hn_user":
                params["tags"] += ",author_" + spec["account"]
            else:
                params["query"] = spec["query"]
                params["restrictSearchableAttributes"] = "comment_text" if item_type == "comment" else "title,story_text,url"
            data = _json("https://hn.algolia.com/api/v1/search_by_date?" + urlencode(params))
            if not isinstance(data, dict) or not isinstance(data.get("hits"), list):
                raise ValueError("HN Search returned invalid results")
            for hit in data["hits"]:
                identity = str(hit.get("objectID") or "")
                if not identity.isdigit():
                    continue
                discussion = "https://news.ycombinator.com/item?id=" + identity
                text = unescape(re.sub(r"<[^>]+>", " ", str((hit.get("comment_text") if item_type == "comment" else hit.get("story_text")) or ""))).strip()
                text = re.sub(r"\s+", " ", text)
                title = unescape(str(hit.get("title") or hit.get("story_title") or "HN discussion"))
                if item_type == "comment":
                    title = "Comment · " + title + " · " + (text[:120] or "by " + str(hit.get("author") or "unknown"))
                url = discussion if item_type == "comment" else hit.get("url") or discussion
                if urlsplit(url).scheme not in {"http", "https"} or not urlsplit(url).hostname:
                    url = discussion
                results.append({"id": identity, "title": title, "url": url, "paper_url": url,
                                "authors": hit.get("author") or "", "abstract": text[:20000],
                                "published_at": hit.get("created_at") or "", "year": None,
                                "source": name, "result_type": "web", "channel_item_type": item_type,
                                "discussion_url": discussion, "parent_story_id": hit.get("story_id")})
            if len(data["hits"]) < 20 or page + 1 >= data.get("nbPages", page + 2):
                break
    return results
