#!/usr/bin/env python3
"""Static checks over site/. Exit 1 with one line per failure, 0 when clean.

Run: python3 -I scripts/check.py
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

REQUIRED_FILES = [
    SITE / "index.html",
    SITE / "en" / "index.html",
    SITE / "ja" / "index.html",
    SITE / "404.html",
    SITE / ".nojekyll",
    ROOT / ".github" / "workflows" / "pages.yml",
]

PAGE_LANG = {
    "index.html": "de",
    "404.html": "de",
    "en/index.html": "en",
    "ja/index.html": "ja",
}
INDEX_PAGES = {"index.html", "en/index.html", "ja/index.html"}
LANG_URL = {
    "de": "https://tokyotranslator.com/",
    "en": "https://tokyotranslator.com/en/",
    "ja": "https://tokyotranslator.com/ja/",
}
HREFLANG = {**LANG_URL, "x-default": LANG_URL["de"]}
LANG_PATH = {"de": "/", "en": "/en/", "ja": "/ja/"}
ALLOWED_EXTERNAL = {
    "https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement",
}
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; "
       "font-src 'self'; base-uri 'self'; form-action 'none'")
REFERRER = "strict-origin-when-cross-origin"
MAILTO = "mailto:quade@tokyotranslator.com"
URL_RE = re.compile(r"https?://[^\s\"'<>)]+")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.html_lang = None
        self.links = []     # dicts of attrs for <link>
        self.metas = []     # dicts of attrs for <meta>
        self.anchors = []   # dicts of attrs for <a>
        self.assets = []    # every src/href value
        self.has_title = False
        self.has_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "link":
            self.links.append(a)
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "a":
            self.anchors.append(a)
        elif tag == "title":
            self.has_title = True
        elif tag == "script":
            self.has_script = True
        for key in ("src", "href"):
            if a.get(key):
                self.assets.append(a[key])


def check_page(path: Path, failures: list[str]) -> None:
    rel = path.relative_to(SITE).as_posix()
    raw = path.read_text(encoding="utf-8")
    page = Page()
    page.feed(raw)

    def fail(msg: str) -> None:
        failures.append(f"{rel}: {msg}")

    if page.has_script:
        fail("contains a <script> tag")

    allowed = set(ALLOWED_EXTERNAL)
    for link in page.links:
        href = link.get("href", "")
        if link.get("rel") in ("alternate", "canonical") and href.startswith("https://tokyotranslator.com/"):
            allowed.add(href)
    for url in URL_RE.findall(raw):
        if url not in allowed:
            fail(f"external URL not allowed: {url}")

    metas = {(m.get("http-equiv") or m.get("name") or "").lower(): m.get("content") for m in page.metas}
    if metas.get("content-security-policy") != CSP:
        fail("CSP meta tag missing or not the exact spec value")
    if metas.get("referrer") != REFERRER:
        fail("referrer meta tag missing or not the exact spec value")

    want_lang = PAGE_LANG.get(rel)
    if want_lang and page.html_lang != want_lang:
        fail(f'<html lang> is {page.html_lang!r}, expected {want_lang!r}')

    if rel in INDEX_PAGES:
        hreflangs = {l.get("hreflang"): l.get("href") for l in page.links if l.get("rel") == "alternate" and l.get("hreflang")}
        for code, url in HREFLANG.items():
            if hreflangs.get(code) != url:
                fail(f"hreflang {code} missing or not {url}")
        if not page.has_title:
            fail("missing <title>")
        if not metas.get("description"):
            fail("missing <meta name=description>")
        if MAILTO not in raw:
            fail(f"missing {MAILTO}")
        for other in LANG_PATH:
            if other == want_lang:
                continue
            if not any(a.get("href") == LANG_PATH[other] and a.get("lang") == other for a in page.anchors):
                fail(f'no language-switcher <a href="{LANG_PATH[other]}" lang="{other}">')

    if not any(l.get("rel") == "icon" and l.get("href") == "/favicon.svg" for l in page.links):
        fail('missing <link rel="icon" href="/favicon.svg">')

    for ref in page.assets:
        if ref.startswith(("/assets/", "/favicon")) and not (SITE / ref.lstrip("/")).is_file():
            fail(f"asset not on disk: {ref}")


def main() -> int:
    failures: list[str] = []
    for f in REQUIRED_FILES:
        if not f.is_file():
            failures.append(f"missing file: {f.relative_to(ROOT).as_posix()}")
    for path in sorted(SITE.rglob("*.html")):
        check_page(path, failures)
    for line in failures:
        print(line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
