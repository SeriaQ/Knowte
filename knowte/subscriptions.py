"""Shared RSS/Atom fetching; Plan consumption remains in PlanActionSeen."""
from __future__ import annotations

import hashlib
import html
import json
import re
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from .automation import _database, ensure_channel_action
from .plans import _now

_LOCKS = {}
_LOCKS_GUARD = threading.Lock()
_MAX_BYTES = 2 * 1024 * 1024


def validate_feed_url(value):
    value = str(value or "").strip()
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password or any(ord(c) < 32 for c in value):
        raise ValueError("Enter an HTTP(S) feed address without embedded credentials")
    return value


def list_subscriptions(path):
    from .channel_connectors import fetch_scope
    with _database(path) as connection:
        items = [dict(row) for row in connection.execute("""SELECT s.id, s.name, s.url, s.last_fetched_at,
            COALESCE((SELECT json_extract(c.spec_json, '$.kind') FROM subscription_connections c WHERE c.subscription_id = s.id), 'feed') AS connector,
            (SELECT count(*) FROM subscription_items i WHERE i.subscription_id = s.id) AS cached_count,
            (SELECT count(DISTINCT pa.plan_id) FROM subscribe_action_subscriptions a
             JOIN plan_actions pa ON pa.action_id = a.action_id WHERE a.subscription_id = s.id) AS used_by
            FROM subscriptions s ORDER BY s.name COLLATE NOCASE""")]
        for item in items:
            spec = connection.execute("SELECT spec_json FROM subscription_connections WHERE subscription_id = ?", (item["id"],)).fetchone()
            action = connection.execute("SELECT config_json, version FROM actions WHERE id = ?", ("channel-" + item["id"],)).fetchone()
            item.update(spec=json.loads(spec[0]) if spec else {"kind": "feed", "source_url": item["url"]},
                        processing=json.loads(action[0]) if action else {}, version=action[1] if action else 1)
    return [{**item, "fetch_scope": fetch_scope(item["connector"])} for item in items]


def save_subscription(payload, path, rsshub_base="", *, config=None):
    name = str(payload.get("name") or "").strip()[:120]
    if not name:
        raise ValueError("Channel name is required")
    if payload.get("id"):
        from .channel_connectors import clean_spec
        from .automation import _action_config
        item_id = str(payload["id"])
        spec = clean_spec(payload.get("spec") or {})
        with _database(path) as connection:
            old = connection.execute("SELECT * FROM subscriptions WHERE id = ?", (item_id,)).fetchone()
            action_id = "channel-" + item_id
            action = connection.execute("SELECT version FROM actions WHERE id = ?", (action_id,)).fetchone()
            if not old or not action or action[0] != payload.get("version"):
                raise ValueError("Channel changed or was removed. Reload before editing")
            if connection.execute("""SELECT 1 FROM action_runs ar JOIN plan_runs r ON r.id = ar.run_id
                JOIN subscribe_action_subscriptions s ON s.action_id = ar.action_id
                WHERE s.subscription_id = ? AND r.status IN ('queued','running')""", (item_id,)).fetchone():
                raise ValueError("Wait for active Plans using this Channel to finish before editing")
            previous = connection.execute("SELECT spec_json FROM subscription_connections WHERE subscription_id = ?", (item_id,)).fetchone()
            previous = json.loads(previous[0]) if previous else {"kind": "feed", "source_url": old["url"]}
            if spec["kind"] != previous["kind"] and not (previous["kind"] == "github_releases" and spec["kind"] == "github_repo"):
                raise ValueError("Create a new Channel to change its connector type")
            processing = _action_config(connection, {**(payload.get("processing") or {}), "subscription_ids": [item_id]}, "subscribe")
            key = spec["kind"] + ":" + spec.get("account", spec["source_url"])
            if connection.execute("SELECT 1 FROM subscriptions WHERE url = ? AND id != ?", (spec["source_url"], item_id)).fetchone():
                raise ValueError("This address already belongs to another Channel")
            connection.execute("UPDATE subscriptions SET name = ?, url = ? WHERE id = ?", (name, spec["source_url"], item_id))
            connection.execute("INSERT INTO subscription_connections VALUES (?, ?, ?) ON CONFLICT(subscription_id) DO UPDATE SET channel_key=excluded.channel_key, spec_json=excluded.spec_json", (item_id, key, json.dumps(spec)))
            connection.execute("UPDATE actions SET name=?, config_json=?, version=version+1, updated_at=? WHERE id=?", (name, json.dumps(processing), _now(), action_id))
            if spec != previous:
                connection.execute("DELETE FROM subscription_items WHERE subscription_id = ?", (item_id,))
                connection.execute("UPDATE subscriptions SET last_fetched_at=NULL, etag='', last_modified='' WHERE id=?", (item_id,))
        return item_id
    spec = None
    if payload.get("spec"):
        from .channel_connectors import clean_spec
        spec = clean_spec(payload["spec"])
        key = spec["kind"] + ":" + spec.get("account", spec["source_url"])
        with _database(path) as connection:
            existing = connection.execute("SELECT subscription_id, spec_json FROM subscription_connections WHERE channel_key = ?", (key,)).fetchone()
        if existing:
            previous = json.loads(existing[1])
            if any(previous.get(field) != spec.get(field) for field in ("event_types", "scopes", "branch")):
                raise ValueError("This account is already saved with a different scope. Use Edit on its existing Channel; its Plan state was kept")
            if "processing" in payload:
                from .automation import _action_config
                with _database(path) as connection:
                    saved = connection.execute("SELECT config_json FROM actions WHERE id=?", ("channel-" + existing[0],)).fetchone()
                    requested = _action_config(connection, {**payload["processing"], "subscription_ids": [existing[0]]}, "subscribe")
                    current = _action_config(connection, json.loads(saved[0]), "subscribe") if saved else None
                    if requested != current:
                        raise ValueError("Channel already exists with different verification settings. Use Edit on the existing Channel")
            return existing[0]
        payload = {**payload, "url": spec["source_url"], "connector": "feed"}
    address = str(payload.get("url") or "").strip()
    if payload.get("connector") == "rsshub":
        base = validate_feed_url(rsshub_base)
        if not address.startswith("/") or address.startswith("//") or ".." in address.split("/"):
            raise ValueError("RSSHub route must start with a single / and stay under the configured base")
        address = base.rstrip("/") + address
    url = validate_feed_url(address)
    with _database(path) as connection:
        existing = connection.execute("SELECT id FROM subscriptions WHERE url = ?", (url,)).fetchone()
        if existing:
            if spec:
                saved = connection.execute("SELECT spec_json FROM subscription_connections WHERE subscription_id = ?", (existing["id"],)).fetchone()
                if not saved or json.loads(saved[0]) != spec:
                    raise ValueError("This URL already has a Channel with another scope. Its existing settings were kept. Remove it from Plans and delete it before saving a replacement")
            return existing["id"]
        item_id = uuid4().hex
        connection.execute("INSERT INTO subscriptions (id, name, url, created_at) VALUES (?, ?, ?, ?)", (item_id, name, url, _now()))
        if spec:
            connection.execute("INSERT INTO subscription_connections VALUES (?, ?, ?)", (item_id, key, json.dumps(spec)))
        ensure_channel_action(connection, item_id, name)
        from .automation import _action_config
        processing = _action_config(connection, {**(payload.get("processing") or {}), "subscription_ids": [item_id]}, "subscribe")
        connection.execute("UPDATE actions SET config_json=? WHERE id=?", (json.dumps(processing), "channel-" + item_id))
        return item_id


def delete_subscription(item_id, path):
    with _database(path) as connection:
        adapter_id = "channel-" + item_id
        if connection.execute("SELECT 1 FROM plan_actions WHERE action_id = ?", (adapter_id,)).fetchone() or connection.execute(
            "SELECT 1 FROM subscribe_action_subscriptions WHERE subscription_id = ? AND action_id != ?", (item_id, adapter_id)).fetchone():
            raise ValueError("Remove this channel from its Plans or legacy Subscribe Actions before deleting it")
        connection.execute("DELETE FROM subscribe_action_subscriptions WHERE action_id = ?", (adapter_id,))
        connection.execute("DELETE FROM actions WHERE id = ?", (adapter_id,))
        if not connection.execute("DELETE FROM subscriptions WHERE id = ?", (item_id,)).rowcount:
            raise ValueError("Subscription not found")


def parse_feed(data, base_url, name):
    if len(data) > _MAX_BYTES or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Feed too large or contains unsupported XML declarations")
    root = ET.fromstring(data)
    atom = "{http://www.w3.org/2005/Atom}"
    if root.tag == atom + "feed":
        entries = root.findall(atom + "entry")
        prefix = atom
    elif root.tag == "rss" and root.find("channel") is not None:
        entries = root.findall("channel/item")
        prefix = ""
    else:
        raise ValueError("This address is not an RSS 2.0 or Atom feed")
    results = []
    for entry in entries:
        def text(tag):
            element = entry.find(prefix + tag)
            return "" if element is None else "".join(element.itertext()).strip()
        title = text("title")
        if prefix:
            link = next((node.get("href", "") for node in entry.findall(atom + "link") if node.get("rel", "alternate") == "alternate"), "")
            identity = text("id")
            published = text("published") or text("updated")
            description = text("content") or text("summary")
            author = text("author")
        else:
            link = text("link")
            identity = text("guid")
            published = text("pubDate")
            description = text("{http://purl.org/rss/1.0/modules/content/}encoded") or text("description")
            author = text("author")
        if not link and identity.startswith(("https://", "http://")):
            link = identity
        url = urljoin(base_url, link)
        if not title or not link or urlsplit(url).scheme not in {"http", "https"}:
            continue
        key = identity or url
        feed_text = html.unescape(re.sub(r"<[^>]+>", " ", description)).strip()[:20000]
        results.append({"id": key, "title": title[:1000], "url": url, "paper_url": url,
            "feed_content": {"text": feed_text, "feed_url": base_url, "scope": "Feed-provided content; may be an excerpt, not the complete article"},
            "authors": author[:1000], "abstract": feed_text,
            "published_at": published, "year": None, "source": name, "result_type": "web"})
    if entries and not results:
        raise ValueError("Feed entries have no readable HTTP(S) article links")
    return results


def fetch_subscription(item_id, path, *, force=False, expected_url=None, expected_spec=None, config=None):
    with _LOCKS_GUARD:
        lock = _LOCKS.setdefault((str(path.resolve()), item_id), threading.Lock())
    with lock:
        with _database(path) as connection:
            row = connection.execute("SELECT * FROM subscriptions WHERE id = ?", (item_id,)).fetchone()
            if not row:
                raise ValueError("Subscription not found")
            sub = dict(row)
            connector = connection.execute("SELECT spec_json FROM subscription_connections WHERE subscription_id = ?", (item_id,)).fetchone()
            spec = json.loads(connector[0]) if connector else None
        if spec:
            from .channel_connectors import clean_spec
            clean_spec(spec)
        if expected_url and expected_url != sub["url"]:
            raise ValueError("Subscription changed after this Run was queued")
        if expected_spec is not None and expected_spec != spec:
            raise ValueError("Channel scope changed after this Run was queued")
        now = datetime.now(timezone.utc)
        fresh = sub["last_fetched_at"] and (now - datetime.fromisoformat(sub["last_fetched_at"])).total_seconds() < 300
        if force or not fresh:
            headers = {"User-Agent": "Knowte Feed Reader", "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml"}
            if sub["etag"]:
                headers["If-None-Match"] = sub["etag"]
            if sub["last_modified"]:
                headers["If-Modified-Since"] = sub["last_modified"]
            not_modified = False
            try:
                if spec and spec["kind"] != "feed":
                    from .channel_connectors import acquire
                    items = acquire(spec, config or {}, sub["name"])
                    etag = modified = ""
                else:
                    from .usage import record_subscription_request
                    record_subscription_request("rss")
                    with urlopen(Request(sub["url"], headers=headers), timeout=20) as response:
                        items = parse_feed(response.read(_MAX_BYTES + 1), response.geturl(), sub["name"])
                        etag = response.headers.get("ETag", "")
                        modified = response.headers.get("Last-Modified", "")
            except HTTPError as error:
                if error.code != 304:
                    raise
                error.close()
                not_modified = True
            with _database(path) as connection:
                current = connection.execute("SELECT spec_json FROM subscription_connections WHERE subscription_id=?", (item_id,)).fetchone()
                if (json.loads(current[0]) if current else None) != spec:
                    raise ValueError("Channel changed during fetch; retry with its new settings")
                if not not_modified:
                    for item in items:
                        key = hashlib.sha256(item["id"].encode()).hexdigest()
                        connection.execute("INSERT INTO subscription_items VALUES (?, ?, ?, ?) ON CONFLICT(subscription_id, item_key) DO UPDATE SET metadata_json = excluded.metadata_json",
                            (item_id, key, json.dumps(item), _now()))
                    connection.execute("UPDATE subscriptions SET etag = ?, last_modified = ? WHERE id = ?", (etag, modified, item_id))
                connection.execute("UPDATE subscriptions SET last_fetched_at = ? WHERE id = ?", (_now(), item_id))
        # Return the durable cache, not just the current feed window. Another Plan
        # may not yet have consumed entries that have rolled off the upstream feed.
        with _database(path) as connection:
            return [json.loads(row[0]) for row in connection.execute("SELECT metadata_json FROM subscription_items WHERE subscription_id = ? ORDER BY first_seen_at, rowid", (item_id,))]
