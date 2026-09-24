"""Bounded document-site link discovery and one model page-selection call."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from xml.etree import ElementTree

from .stage_skills import skill_prompt

MAX_PAGES = 10
MAX_CANDIDATES = 200


def page_url(value):
    parts = urlsplit(str(value or ""))
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("Related pages requires an HTTP(S) webpage")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def in_scope(url, seed):
    url, seed = page_url(url), page_url(seed)
    target, origin = urlsplit(url), urlsplit(seed)
    if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
        return False
    # Keep documentation language/version, even when chapters are sibling paths.
    version = re.match(r"^/(?:[a-z]{2}(?:-[A-Za-z]{2})?/)?(?:latest|stable|v?\d[\w.-]*)/", origin.path)
    if version and not target.path.startswith(version[0]):
        return False
    return not re.search(r"(?:\.(?:png|jpe?g|svg|gif|webp|zip|gz|mp4|css|js)$|/(?:login|logout|signin|search)(?:/|$))", target.path, re.I)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.href, self.text = [], "", []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href") or ""
            self.text = []

    def handle_data(self, data):
        if self.href:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            self.links.append((self.href, " ".join(" ".join(self.text).split())[:250]))
            self.href = ""


def _read(url, seed):
    class ScopedRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if not in_scope(newurl, seed):
                raise ValueError("Redirect leaves the selected site/version")
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    with build_opener(ScopedRedirect()).open(Request(url, headers={"User-Agent": "Knowte"}), timeout=15) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("Page directory exceeds 2 MB")
        if "html" not in response.headers.get_content_type() and "xml" not in response.headers.get_content_type():
            raise ValueError("Related pages requires an HTML page or sitemap")
        return raw.decode("utf-8", errors="replace")


def discover_pages(sources):
    pages, warnings, seen = [], [], set()
    def add(url, title, source):
        try:
            url = page_url(url)
            if not in_scope(url, source["url"]) or url in seen:
                return
        except ValueError:
            return
        seen.add(url)
        if len(pages) < MAX_CANDIDATES:
            pages.append({"id": hashlib.sha256(url.encode()).hexdigest()[:32],
                          "url": url, "title": title or urlsplit(url).path,
                          "parent_source_id": source["id"]})
    for source in sources:
        seed = page_url(source.get("url") or source.get("paper_url"))
        source = {**source, "url": seed}
        add(seed, source["title"], source)
        try:
            parser = _Links(); parser.feed(_read(seed, seed)); parser.close()
            for href, title in parser.links:
                add(urljoin(seed, href), title, source)
        except (OSError, ValueError) as error:
            warnings.append(f"{source['title']}: link discovery failed: {error}")
            continue
        # One bounded directory supplement; no unbounded crawl or sitemap-index recursion.
        sitemap = urljoin(seed, "/sitemap.xml")
        try:
            xml = _read(sitemap, sitemap)
            if "<!DOCTYPE" in xml or "<!ENTITY" in xml:
                raise ValueError("Unsupported sitemap XML")
            root = ElementTree.fromstring(xml)
            if root.tag.rsplit("}", 1)[-1] == "urlset":
                for loc in root.iter():
                    if loc.tag.rsplit("}", 1)[-1] == "loc":
                        add(loc.text, "", source)
        except (OSError, ValueError, ElementTree.ParseError):
            pass  # Sitemap is optional; discovered navigation links remain useful.
    if len(seen) > MAX_CANDIDATES:
        warnings.append(f"Page directory limited to the first {MAX_CANDIDATES} unique in-scope URLs; discovery is not exhaustive.")
    return pages, warnings


def select_pages(client, pages, focus, limit, skills_dir):
    result = client.chat_json(
        skill_prompt("evidence_page_selection", skills_dir),
        json.dumps({"focus": focus, "max_pages": limit, "pages": pages}, ensure_ascii=False),
        temperature=0.1, max_tokens=1600,
    )
    if result.get("_structured_output_degraded"):
        raise ValueError("Page selection could not be parsed; no extraction was started. Model response:\n" + str(result.get("answer") or ""))
    ids = result.get("page_ids")
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids) or len(ids) > limit or len(set(ids)) != len(ids):
        raise ValueError("Page selector returned an invalid page count; no extraction was started")
    known = {page["id"]: page for page in pages}
    if any(value not in known for value in ids):
        raise ValueError("Page selector returned an unknown URL; no extraction was started")
    return [known[value] for value in ids], str(result.get("summary") or "")[:2000]
