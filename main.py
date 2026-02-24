import requests, json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

def scrape_links(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        return {a['href'] for a in soup.find_all('a', href=True)}
    except Exception:
        return set()

def start_scrape(base_url):
    visited = set()
    to_visit = {base_url}

    while to_visit:
        print(f"Scraping {len(to_visit)} links in parallel...")
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(scrape_links, url): url for url in to_visit}
            visited.update(to_visit)

            new_links = set()
            for future in as_completed(futures):
                new_links.update(future.result())

        to_visit = {
            link for link in new_links
            if link.startswith(base_url) and link not in visited
        }

    
    with open('scraped_links.json', 'w') as f:
        json.dump(sorted(visited), f, indent=4)

    print(f"Done. {len(visited)} links saved to scraped_links.json.")
    return visited

def return_markdown(link):
    response = requests.post(
        "http://localhost:11235/md",
        json={"url": link, "f": "fit"}
    )
    return response.json()["markdown"]

def main(base_url):
    links = start_scrape(base_url)

    markdowns = []
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(return_markdown, link): link for link in links}
        for future in as_completed(futures):
            try:
                markdowns.append(future.result())
            except Exception:
                pass

    with open('all_markdown.md', 'w') as f:
        f.write("\n\n".join(markdowns))


if __name__ == "__main__":
    BASE_URL = "https://www.lachiusella.it/"
    main(BASE_URL)