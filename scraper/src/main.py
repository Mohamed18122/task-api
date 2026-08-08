from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone
import json
import time
import re

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"

USER_AGENT = (
    "FlyRankInternship-A9/1.0 "
    "(+https://github.com/Mohamed18122/task-api)"
)

TIMEOUT = 10
DELAY_SECONDS = 0.5

# Set to True only when testing failure handling.
# Normal run should stay False.
INJECT_FAILURE_FOR_TEST = False

FAKE_FAILURE_URL = (
    "https://books.toscrape.com/catalogue/this-page-does-not-exist_999999/index.html"
)

CACHE_DIR = Path(__file__).parent.parent / "cache"
CATALOGUE_CACHE = CACHE_DIR / "catalogue-page-1.html"
BOOK_CACHE_DIR = CACHE_DIR / "book-pages"

OUTPUT_DIR = Path(__file__).parent.parent / "output"
BOOKS_OUTPUT = OUTPUT_DIR / "books.json"
RUN_REPORT_OUTPUT = OUTPUT_DIR / "run-report.json"


def fetch_page(
    url: str,
    cache_file: Path | None = None,
    stats: dict | None = None,
) -> str:

    if cache_file and cache_file.exists():

        html = cache_file.read_text(
            encoding="utf-8"
        )

        if stats is not None:
            stats["cache_hits"] += 1

        print(
            f"CACHE HIT: {len(html)} bytes"
        )

        return html

    time.sleep(DELAY_SECONDS)

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed: HTTP "
            f"{response.status_code} - {url}"
        )

    html = response.text

    if cache_file:

        cache_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        cache_file.write_text(
            html,
            encoding="utf-8"
        )

    if stats is not None:
        stats["pages_fetched"] += 1

    print(
        f"FETCH: HTTP {response.status_code}, "
        f"{len(html)} bytes"
    )

    return html


def discover_books_from_page(
    html: str,
    page_url: str
) -> list[str]:

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    urls = []

    for article in soup.select(
        "article.product_pod"
    ):

        link = article.select_one(
            "h3 a"
        )

        if link and link.get("href"):

            absolute_url = urljoin(
                page_url,
                link["href"]
            )

            urls.append(
                absolute_url
            )

    return urls


def find_next_page(
    html: str,
    page_url: str
) -> str | None:

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    next_link = soup.select_one(
        "li.next a"
    )

    if next_link and next_link.get("href"):

        return urljoin(
            page_url,
            next_link["href"]
        )

    return None


def discover_three_catalogue_pages(
    stats: dict
) -> list[str]:

    current_url = BASE_URL

    all_book_urls = []

    catalogue_pages = 0

    while current_url and catalogue_pages < 3:

        catalogue_pages += 1

        if catalogue_pages == 1:

            html = fetch_page(
                current_url,
                CATALOGUE_CACHE,
                stats
            )

        else:

            html = fetch_page(
                current_url,
                stats=stats
            )

        book_urls = discover_books_from_page(
            html,
            current_url
        )

        all_book_urls.extend(
            book_urls
        )

        current_url = find_next_page(
            html,
            current_url
        )

    unique_urls = list(
        dict.fromkeys(
            all_book_urls
        )
    )

    print(
        f"catalogue_pages={catalogue_pages}"
    )

    print(
        f"discovered={len(all_book_urls)}"
    )

    print(
        f"unique_urls={len(unique_urls)}"
    )

    stats["catalogue_pages"] = catalogue_pages

    return unique_urls


def book_cache_file(
    url: str
) -> Path:

    match = re.search(
        r"_([0-9]+)/index.html$",
        url
    )

    if match:

        book_id = match.group(1)

    else:

        book_id = str(
            abs(hash(url))
        )

    return (
        BOOK_CACHE_DIR
        / f"{book_id}.html"
    )


def fetch_book_pages(
    book_urls: list[str],
    stats: dict
) -> None:

    BOOK_CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    total = len(book_urls)

    for index, url in enumerate(
        book_urls,
        start=1
    ):

        cache_file = book_cache_file(
            url
        )

        if cache_file.exists():

            cache_file.read_text(
                encoding="utf-8"
            )

            stats["cache_hits"] += 1

            print(
                f"[{index}/{total}] "
                f"CACHE HIT: {url}"
            )

            continue

        success = False

        for attempt in range(2):

            try:

                time.sleep(
                    DELAY_SECONDS
                )

                response = requests.get(
                    url,
                    headers={
                        "User-Agent": USER_AGENT
                    },
                    timeout=TIMEOUT,
                )

                if response.status_code == 200:

                    html = response.text

                    cache_file.write_text(
                        html,
                        encoding="utf-8"
                    )

                    stats["pages_fetched"] += 1

                    success = True

                    print(
                        f"[{index}/{total}] "
                        f"FETCH: HTTP 200, "
                        f"{len(html)} bytes"
                    )

                    break

                # No retry for 403 / 404.
                if response.status_code in (
                    403,
                    404
                ):

                    print(
                        f"[{index}/{total}] "
                        f"FAILED: HTTP "
                        f"{response.status_code}: "
                        f"{url}"
                    )

                    break

                # Retry exactly once for 5xx.
                if 500 <= response.status_code <= 599:

                    if attempt == 0:

                        print(
                            f"[{index}/{total}] "
                            f"HTTP "
                            f"{response.status_code}, "
                            f"retrying once..."
                        )

                        continue

                    print(
                        f"[{index}/{total}] "
                        f"FAILED after retry: "
                        f"HTTP "
                        f"{response.status_code}: "
                        f"{url}"
                    )

                    break

                print(
                    f"[{index}/{total}] "
                    f"FAILED: HTTP "
                    f"{response.status_code}: "
                    f"{url}"
                )

                break

            except requests.exceptions.Timeout:

                if attempt == 0:

                    print(
                        f"[{index}/{total}] "
                        f"TIMEOUT, "
                        f"retrying once..."
                    )

                    continue

                print(
                    f"[{index}/{total}] "
                    f"FAILED after retry: "
                    f"TIMEOUT: {url}"
                )

                break

            except requests.exceptions.RequestException as exc:

                print(
                    f"[{index}/{total}] "
                    f"FAILED: "
                    f"{type(exc).__name__}: "
                    f"{url}"
                )

                break

        if not success:

            stats["failed_pages"] += 1

            stats["failed_page_urls"].append(
                url
            )

    print(
        f"detail_pages={len(book_urls)}"
    )

    print(
        f"fetched={stats['pages_fetched']}"
    )

    print(
        f"cache_hits={stats['cache_hits']}"
    )

    print(
        f"failed={stats['failed_pages']}"
    )


def extract_book_record(
    html: str,
    product_url: str,
    source_page: str
) -> dict:

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    title_element = soup.select_one(
        "div.product_main h1"
    )

    price_element = soup.select_one(
        "div.product_main .price_color"
    )

    availability_element = soup.select_one(
        "div.product_main .availability"
    )

    rating_element = soup.select_one(
        "div.product_main .star-rating"
    )

    description_element = soup.select_one(
        "#product_description + p"
    )

    title = (
        title_element.get_text(
            strip=True
        )
        if title_element
        else None
    )

    price_text = (
        price_element.get_text(
            strip=True
        )
        if price_element
        else None
    )

    availability_text = (
        availability_element.get_text(
            " ",
            strip=True
        )
        if availability_element
        else None
    )

    rating_text = None

    if rating_element:

        rating_text = " ".join(
            rating_element.get(
                "class",
                []
            )
        )

    description = (
        description_element.get_text(
            " ",
            strip=True
        )
        if description_element
        else None
    )

    fetched_at = datetime.now(
        timezone.utc
    ).isoformat()

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


def extract_all_records(
    book_urls: list[str],
    stats: dict
) -> list[dict]:

    records = []

    total = len(book_urls)

    for index, url in enumerate(
        book_urls,
        start=1
    ):

        cache_file = book_cache_file(
            url
        )

        if not cache_file.exists():

            print(
                f"[{index}/{total}] "
                f"SKIPPED: cache missing"
            )

            continue

        try:

            html = cache_file.read_text(
                encoding="utf-8"
            )

            record = extract_book_record(
                html,
                url,
                BASE_URL
            )

            records.append(
                record
            )

            print(
                f"[{index}/{total}] "
                f"EXTRACTED: "
                f"{record['title']}"
            )

        except Exception as exc:

            print(
                f"[{index}/{total}] "
                f"INVALID: {url} - "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            stats["invalid_records"] += 1

    print(
        f"records={len(records)}"
    )

    return records


def clean_price(
    price_text: str | None
) -> float | None:

    if not price_text:
        return None

    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)",
        price_text
    )

    if not match:
        return None

    return float(
        match.group(1)
    )


def clean_availability(
    availability_text: str | None
) -> int | None:

    if not availability_text:
        return None

    match = re.search(
        r"\((\d+)\s+available\)",
        availability_text
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


def clean_rating(
    rating_text: str | None
) -> int | None:

    if not rating_text:
        return None

    rating_map = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5,
    }

    for word, value in rating_map.items():

        if word in rating_text:

            return value

    return None


def normalize_book_record(
    record: dict
) -> dict:

    return {
        "title": record["title"],
        "product_url": record["product_url"],
        "price": clean_price(
            record["price_text"]
        ),
        "availability": clean_availability(
            record["availability_text"]
        ),
        "rating": clean_rating(
            record["rating_text"]
        ),
        "description": record["description"],
        "source_page": record["source_page"],
        "fetched_at": record["fetched_at"],
    }


def validate_record(
    record: dict
) -> bool:

    required_fields = [
        "title",
        "product_url",
        "price",
        "availability",
        "rating",
        "description",
        "source_page",
        "fetched_at",
    ]

    for field in required_fields:

        if field not in record:
            return False

    if not record["title"]:
        return False

    if not record["product_url"]:
        return False

    return True


def save_books(
    records: list[dict]
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with BOOKS_OUTPUT.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"saved books: {BOOKS_OUTPUT}"
    )


def save_run_report(
    stats: dict,
    start_time: datetime,
    end_time: datetime
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    duration = (
        end_time - start_time
    ).total_seconds()

    report = {
        "started_at": start_time.isoformat(),
        "finished_at": end_time.isoformat(),
        "duration_seconds": duration,
        "catalogue_pages": stats[
            "catalogue_pages"
        ],
        "pages_fetched": stats[
            "pages_fetched"
        ],
        "cache_hits": stats[
            "cache_hits"
        ],
        "valid_records": stats[
            "valid_records"
        ],
        "invalid_records": stats[
            "invalid_records"
        ],
        "failed_pages": stats[
            "failed_pages"
        ],
        "failed_page_urls": stats[
            "failed_page_urls"
        ],
    }

    with RUN_REPORT_OUTPUT.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"saved run report: "
        f"{RUN_REPORT_OUTPUT}"
    )


if __name__ == "__main__":

    start_time = datetime.now(
        timezone.utc
    )

    stats = {
        "catalogue_pages": 0,
        "pages_fetched": 0,
        "cache_hits": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "failed_pages": 0,
        "failed_page_urls": [],
    }

    try:

        # Stage 1 + Stage 2
        book_urls = discover_three_catalogue_pages(
            stats
        )

        # Failure-handling test:
        # adds ONE fake URL only when enabled.
        if INJECT_FAILURE_FOR_TEST:

            book_urls.append(
                FAKE_FAILURE_URL
            )

            print(
                "TEST MODE: added one fake "
                "failure URL"
            )

        # Stage 2 / Stage 5
        fetch_book_pages(
            book_urls,
            stats
        )

        # Stage 3
        records = extract_all_records(
            book_urls,
            stats
        )

        # Stage 4
        normalized_records = []

        for record in records:

            clean_record = normalize_book_record(
                record
            )

            if validate_record(
                clean_record
            ):

                normalized_records.append(
                    clean_record
                )

            else:

                stats["invalid_records"] += 1

        stats["valid_records"] = len(
            normalized_records
        )

        print(
            f"normalized_records="
            f"{len(normalized_records)}"
        )

        # Save the 60 valid records.
        save_books(
            normalized_records
        )

        if normalized_records:

            print(
                normalized_records[0]
            )

    finally:

        end_time = datetime.now(
            timezone.utc
        )

        save_run_report(
            stats,
            start_time,
            end_time
        )

        print()
        print("========== RUN SUMMARY ==========")
        print(
            f"valid_records="
            f"{stats['valid_records']}"
        )
        print(
            f"invalid_records="
            f"{stats['invalid_records']}"
        )
        print(
            f"failed_pages="
            f"{stats['failed_pages']}"
        )
        print(
            f"pages_fetched="
            f"{stats['pages_fetched']}"
        )
        print(
            f"cache_hits="
            f"{stats['cache_hits']}"
        )
        print("=================================")

