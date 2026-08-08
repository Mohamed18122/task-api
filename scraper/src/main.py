from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Mohamed18122/task-api)"
TIMEOUT = 10

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_FILE = CACHE_DIR / "catalogue-page-1.html"


def fetch_catalogue_page(url: str, cache_file: Path) -> str:
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        print(f"CACHE HIT: {len(html)} bytes")
        return html

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed: HTTP {response.status_code}"
        )

    html = response.text
    cache_file.write_text(html, encoding="utf-8")

    print(f"FETCH: HTTP {response.status_code}, {len(html)} bytes")

    return html


def discover_books_from_page(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    urls = []

    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")

        if link and link.get("href"):
            absolute_url = urljoin(page_url, link["href"])
            urls.append(absolute_url)

    return urls


def find_next_page(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one("li.next a")

    if next_link and next_link.get("href"):
        return urljoin(page_url, next_link["href"])

    return None


def discover_three_catalogue_pages() -> list[str]:
    current_url = BASE_URL
    all_book_urls = []
    catalogue_pages = 0

    while current_url and catalogue_pages < 3:
        catalogue_pages += 1

        if catalogue_pages == 1:
            cache_file = CACHE_FILE
            html = fetch_catalogue_page(current_url, cache_file)
        else:
            response = requests.get(
                current_url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Fetch failed: HTTP {response.status_code}"
                )

            html = response.text

        book_urls = discover_books_from_page(html, current_url)
        all_book_urls.extend(book_urls)

        current_url = find_next_page(html, current_url)

    unique_urls = list(dict.fromkeys(all_book_urls))

    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(all_book_urls)}")
    print(f"unique_urls={len(unique_urls)}")

    return unique_urls


if __name__ == "__main__":
    discover_three_catalogue_pages()