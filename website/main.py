"""
Website scraper — converts a list of URLs to a single markdown file.

## URL discovery workflow (run before this script)

This script reads URLs from `website/urls.json`. That file must be populated
first by a sub-agent that crawls the target website. The recommended steps:

1. Spawn a sub-agent with the property's base URL. The agent should:
   a. Fetch the homepage and extract all internal hrefs.
   b. Recursively follow links (breadth-first, same domain only) until no new
      links are found, keeping only content pages (skip /admin, /login,
      /#anchors, ?query= variants that are duplicates, etc.).
   c. Use its own judgment to filter out irrelevant pages (sitemaps, robots,
      RSS feeds, policy pages) and deduplicate URLs that serve the same content.
   d. Write the final list to `website/urls.json` as a JSON array of strings.

2. Once `website/urls.json` exists, run:
       python website/main.py
   This script reads that file, fetches each page, converts to markdown, strips
   noise, and writes the combined output to `website/exported.md`.

Example urls.json:
    ["https://example.com/", "https://example.com/rooms", "https://example.com/contact"]
"""

import json
import os
import re
import sys

import requests
from html2text import html2text

# The server returns pre-rendered HTML to bot UAs but a thin JS shell to browsers
HEADERS = {"User-Agent": "curl/7.81.0"}

COOKIE_BANNER_RE = re.compile(
    r"Consent\s*\nDetails\s*\nAbout Cookies.*?Update consent\s*\n",
    re.DOTALL
)

URLS_FILE = os.path.join(os.path.dirname(__file__), "urls.json")


def strip_noise(md):
    md = COOKIE_BANNER_RE.sub("", md)
    lines = []
    for l in md.splitlines():
        if re.match(r"^\s*!\[.*?\]\(.*?\)\s*$", l):
            continue
        if re.match(r"^\s*\*\s+\S+\.(webp|jpeg|jpg|png)\s*$", l):
            continue
        if re.match(r"^\s*\*\s+undefined\s*$", l):
            continue
        lines.append(l)
    md = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return md.strip()


def fetch_markdown(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return html2text(resp.text)


def load_urls():
    if not os.path.exists(URLS_FILE):
        print(
            f"Error: {URLS_FILE} not found.\n"
            "Run the URL-discovery sub-agent first to populate it. "
            "See the module docstring for instructions.",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(URLS_FILE) as f:
        urls = json.load(f)
    if not isinstance(urls, list) or not urls:
        print(f"Error: {URLS_FILE} must be a non-empty JSON array of URL strings.", file=sys.stderr)
        sys.exit(1)
    return urls


def main(urls):
    markdowns = []
    for url in urls:
        print(f"Fetching {url} ...")
        md = fetch_markdown(url)
        markdowns.append(strip_noise(md))
    return "\n\n".join(markdowns)


if __name__ == "__main__":
    urls = load_urls()
    markdown = main(urls)
    out = os.path.join(os.path.dirname(__file__), "exported.md")
    with open(out, "w") as f:
        f.write(markdown)
    print(f"Written {out}")
