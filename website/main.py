import requests
import re
from html2text import html2text

# The server returns pre-rendered HTML to bot UAs but a thin JS shell to browsers
HEADERS = {"User-Agent": "curl/7.81.0"}

COOKIE_BANNER_RE = re.compile(
    r"Consent\s*\nDetails\s*\nAbout Cookies.*?Update consent\s*\n",
    re.DOTALL
)

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

def main(urls):
    markdowns = []
    for url in urls:
        print(f"Fetching {url} ...")
        md = fetch_markdown(url)
        markdowns.append(strip_noise(md))
    return "\n\n".join(markdowns)


if __name__ == "__main__":
    urls = [
        "https://www.acasadibiagio.it/home",
        "https://www.acasadibiagio.it/camere",
        "https://www.acasadibiagio.it/servizi",
        "https://www.acasadibiagio.it/contatti",
        "https://www.acasadibiagio.it/informazioni"
    ]

    markdown = main(urls)
    with open('website/exported.md', 'w') as f:
        f.write(markdown)
