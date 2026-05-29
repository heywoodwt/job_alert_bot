import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def strip_html(html_string: str) -> str:
    """Remove HTML tags from a string."""
    text = re.sub(r"<[^>]+>", "", html_string)
    return text.strip()


def _clean_job_url(url: str) -> str:
    """Remove tracking query params from a LinkedIn job URL, keeping the clean path."""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def parse_job_cards(html: str) -> list[dict]:
    """Parse LinkedIn guest API HTML and return a list of job entry dicts."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="job-search-card")
    entries = []
    for card in cards:
        job_id = card.get("data-entity-urn", "")

        link_tag = card.find("a", class_="base-card__full-link")
        raw_link = link_tag["href"].strip() if link_tag and link_tag.get("href") else ""
        link = _clean_job_url(raw_link)

        title_tag = card.find("h3", class_="base-search-card__title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        company_tag = card.find("h4", class_="base-search-card__subtitle")
        company = company_tag.get_text(strip=True) if company_tag else ""

        location_tag = card.find("span", class_="job-search-card__location")
        location = location_tag.get_text(strip=True) if location_tag else ""

        time_tag = card.find("time", class_="job-search-card__listdate")
        if not time_tag:
            time_tag = card.find("time", class_="job-search-card__listdate--new")
        pub_date = time_tag.get("datetime", "") if time_tag else ""

        description = f"{company} - {location}" if company and location else company or location

        entries.append({
            "job_id": job_id,
            "title": title,
            "link": link,
            "description": description,
            "pub_date": pub_date,
        })
    return entries


def fetch_and_parse_feeds(feed_urls: list[str]) -> list[dict]:
    """Fetch LinkedIn guest API URLs and return combined parsed job entries."""
    all_entries = []
    for url in feed_urls:
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            response.raise_for_status()
            all_entries.extend(parse_job_cards(response.text))
        except Exception as e:
            print(f"Error fetching {url}: {e}")
    return all_entries
