from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone
import time
import re

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Mohamed18122/task-api)"
TIMEOUT = 10
DELAY_SECONDS = 0.5

CACHE_DIR = Path(__file__).parent.parent / "cache"
CATALOGUE_CACHE = CACHE_DIR / "catalogue-page-1.html"
BOOK_CACHE_DIR = CACHE_DIR / "book-pages"


def fetch_page(url: str, cache_file: Path | None = None) -> str:
    if cache_file and cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        print(f"CACHE HIT: {len(html)} bytes")
        return html

    time.sleep(DELAY_SECONDS)

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed: HTTP {response.status_code} - {url}"
        )

    html = response.text

    if cache_file:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
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
            cache_file = CATALOGUE_CACHE
            html = fetch_page(current_url, cache_file)
        else:
            html = fetch_page(current_url)

        book_urls = discover_books_from_page(html, current_url)
        all_book_urls.extend(book_urls)

        current_url = find_next_page(html, current_url)

    unique_urls = list(dict.fromkeys(all_book_urls))

    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(all_book_urls)}")
    print(f"unique_urls={len(unique_urls)}")

    return unique_urls


def book_cache_file(url: str) -> Path:
    match = re.search(r"_([0-9]+)/index\.html$", url)

    if match:
        book_id = match.group(1)
    else:
        book_id = str(abs(hash(url)))

    return BOOK_CACHE_DIR / f"{book_id}.html"


def fetch_book_pages(book_urls: list[str]) -> None:
    BOOK_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    fetched = 0
    cache_hits = 0
    failed = 0

    for index, url in enumerate(book_urls, start=1):
        cache_file = book_cache_file(url)

        if cache_file.exists():
            html = cache_file.read_text(encoding="utf-8")
            cache_hits += 1
            print(f"[{index}/60] CACHE HIT: {url}")
            continue

        success = False

        for attempt in range(2):
            try:
                time.sleep(DELAY_SECONDS)

                response = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=TIMEOUT,
                )

                if response.status_code == 200:
                    html = response.text
                    cache_file.write_text(html, encoding="utf-8")

                    fetched += 1
                    success = True

                    print(
                        f"[{index}/60] FETCH: HTTP 200, "
                        f"{len(html)} bytes"
                    )

                    break

                if response.status_code in (403, 404):
                    print(
                        f"[{index}/60] FAILED: HTTP "
                        f"{response.status_code}: {url}"
                    )
                    break

                if 500 <= response.status_code <= 599:
                    if attempt == 0:
                        print(
                            f"[{index}/60] HTTP {response.status_code}, "
                            f"retrying once..."
                        )
                        continue

                    print(
                        f"[{index}/60] FAILED after retry: "
                        f"HTTP {response.status_code}: {url}"
                    )
                    break

                print(
                    f"[{index}/60] FAILED: HTTP "
                    f"{response.status_code}: {url}"
                )
                break

            except requests.exceptions.Timeout:
                if attempt == 0:
                    print(
                        f"[{index}/60] TIMEOUT, retrying once..."
                    )
                    continue

                print(
                    f"[{index}/60] FAILED after retry: TIMEOUT: {url}"
                )
                break

            except requests.exceptions.RequestException as exc:
                print(
                    f"[{index}/60] FAILED: {type(exc).__name__}: {url}"
                )
                break

        if not success:
            failed += 1

    print(f"detail_pages={len(book_urls)}")
    print(f"fetched={fetched}")
    print(f"cache_hits={cache_hits}")
    print(f"failed={failed}")

def extract_book_record(
    html: str,
    product_url: str,
    source_page: str
) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_element = soup.select_one("div.product_main h1")
    price_element = soup.select_one("div.product_main .price_color")
    availability_element = soup.select_one("div.product_main .availability")
    rating_element = soup.select_one("div.product_main .star-rating")
    description_element = soup.select_one("#product_description + p")

    title = (
        title_element.get_text(strip=True)
        if title_element
        else None
    )

    price_text = (
        price_element.get_text(strip=True)
        if price_element
        else None
    )

    if price_text and "Â" in price_text:
        price_text = price_text.encode("latin1").decode("utf-8")

    availability_text = (
        availability_element.get_text(" ", strip=True)
        if availability_element
        else None
    )

    rating_text = None
    if rating_element:
        classes = rating_element.get("class", [])
        rating_text = " ".join(classes)

    description = (
        description_element.get_text(" ", strip=True)
        if description_element
        else None
    )

    fetched_at = datetime.now(timezone.utc).isoformat()

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def extract_all_books(book_urls: list[str]) -> list[dict]:
    records = []

    for index, product_url in enumerate(book_urls, start=1):
        cache_file = book_cache_file(product_url)

        if not cache_file.exists():
            print(f"[{index}/60] SKIP: missing cache")
            continue

        html = cache_file.read_text(encoding="utf-8")

        record = extract_book_record(
            html,
            product_url,
            BASE_URL,
        )

        records.append(record)

        print(
            f"[{index}/60] EXTRACTED: "
            f"{record['title']}"
        )

    return records


if __name__ == "__main__":
    book_urls = discover_three_catalogue_pages()

    fetch_book_pages(book_urls)

    records = extract_all_books(book_urls)

    print(f"records={len(records)}")

    if records:
        print(records[0])