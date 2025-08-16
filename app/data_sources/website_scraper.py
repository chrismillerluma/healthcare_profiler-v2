import requests
from bs4 import BeautifulSoup
import logging

def scrape_about(website_url: str) -> dict:
    """
    Scrape basic info from a website: title, meta description, first H1.
    Returns dict with keys: title, meta_description, h1, url.
    """
    if not website_url:
        return {}

    try:
        resp = requests.get(
            website_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Meta description
        desc_tag = (
            soup.find("meta", attrs={"name": "description"}) or
            soup.find("meta", attrs={"property": "og:description"})
        )
        meta_desc = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""

        # First H1
        h1_tag = soup.find("h1")
        h1_text = h1_tag.get_text().strip() if h1_tag else ""

        return {
            "title": title,
            "meta_description": meta_desc,
            "h1": h1_text,
            "url": website_url
        }

    except Exception as e:
        logging.warning(f"[Scrape About Error] {e} | URL: {website_url}")
        return {}
