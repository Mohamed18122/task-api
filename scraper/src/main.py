from pathlib import Path

import requests


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_FILE = Path(__file__).parent.parent / "cache" / "catalogue-page-1.html"

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Mohamed18122/task-api)"
TIMEOUT = 10


def fetch_catalogue_page() -> str:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if CACHE_FILE.exists():
        html = CACHE_FILE.read_text(encoding="utf-8")
        print(f"CACHE HIT: {len(html)} bytes")
        return html

    headers = {
        "User-Agent": USER_AGENT,
    }

    response = requests.get(
        BASE_URL,
        headers=headers,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed: HTTP {response.status_code}"
        )

    html = response.text
    CACHE_FILE.write_text(html, encoding="utf-8")

    print(f"FETCH: HTTP {response.status_code}, {len(html)} bytes")

    return html


if __name__ == "__main__":
    fetch_catalogue_page()

