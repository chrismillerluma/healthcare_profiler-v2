import os
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
import logging
import re

logging.basicConfig(level=logging.INFO)

DEFAULT_YELP_LIMIT = 5
DEFAULT_YELP_LOCATION = os.getenv("DEFAULT_YELP_LOCATION", "San Francisco, CA")

# -------------------------
# Yelp API fetch
# -------------------------
def fetch_yelp_reviews_api(name: str, city: str = None, api_key: str = None, limit: int = DEFAULT_YELP_LIMIT) -> list[dict]:
    """
    Fetch Yelp reviews using the Yelp Fusion API.
    Returns a list of dicts: {"user", "rating", "text"}.
    """
    if not api_key:
        logging.info("[Yelp API] No API key provided.")
        return []

    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"term": name, "location": city or DEFAULT_YELP_LOCATION, "limit": limit}

    try:
        resp = requests.get("https://api.yelp.com/v3/businesses/search", headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        businesses = data.get("businesses", [])
        if not businesses:
            return []

        # Pick top match by fuzzy name similarity
        businesses.sort(key=lambda b: fuzz.ratio(name.lower(), b["name"].lower()), reverse=True)
        best = businesses[0]

        # Fetch reviews for this business
        review_resp = requests.get(f"https://api.yelp.com/v3/businesses/{best['id']}/reviews", headers=headers, timeout=10)
        review_resp.raise_for_status()
        reviews = review_resp.json().get("reviews", [])
        return [
            {"user": r.get("user", {}).get("name", "Anonymous"), "rating": r.get("rating"), "text": r.get("text", "")}
            for r in reviews[:limit]
        ]

    except Exception as e:
        logging.warning(f"[Yelp API Error] {e}")
        return []

# -------------------------
# Yelp search scraping fallback
# -------------------------
def fetch_yelp_reviews_scrape(name: str, city: str = None, limit: int = DEFAULT_YELP_LIMIT) -> list[dict]:
    """
    Scrape Yelp search page as fallback if API not available.
    Returns a list of dicts: {"user", "rating", "text"}.
    """
    search_location = city or DEFAULT_YELP_LOCATION
    query = f"{name} {search_location}".replace(" ", "+")
    url = f"https://www.yelp.com/search?find_desc={query}"

    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        reviews = []

        # Try p tags with Yelp snippet class
        for div in soup.select("p.comment__09f24__gu0rG")[:limit]:
            reviews.append({"user": "Anonymous", "rating": None, "text": div.get_text()})

        # Fallback: pick any <p> with reasonable length
        if len(reviews) < limit:
            for div in soup.find_all("p"):
                text = div.get_text()
                if len(text) > 30 and len(reviews) < limit:
                    reviews.append({"user": "Anonymous", "rating": None, "text": text})

        return reviews[:limit]

    except Exception as e:
        logging.warning(f"[Yelp Scrape Error] {e}")
        return []

# -------------------------
# Yelp business page scraping
# -------------------------
def fetch_yelp_reviews_scrape_url(url: str, limit: int = DEFAULT_YELP_LIMIT) -> list[dict]:
    """
    Scrape Yelp reviews directly from a Yelp business page URL.
    Returns a list of dicts: {"user", "rating", "text"}.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        reviews = []

        review_divs = soup.select("div.review__09f24__oHr9V") or soup.find_all("div", {"role": "region"})

        for div in review_divs[:limit]:
            text_tag = div.find("span", {"class": "raw__09f24__T4Ezm"})
            text = text_tag.get_text() if text_tag else ""

            rating_tag = div.find("div", {"role": "img"})
            rating = None
            if rating_tag:
                match = re.search(r"(\d\.?\d?) star rating", rating_tag.get("aria-label", ""))
                if match:
                    rating = float(match.group(1))

            user_tag = div.find("span", {"class": "fs-block css-m6anxm"})
            user = user_tag.get_text() if user_tag else "Anonymous"

            reviews.append({"user": user, "rating": rating, "text": text})

        return reviews[:limit]

    except Exception as e:
        logging.warning(f"[Yelp Scrape URL Error] {e}")
        return []

# playwright scraper fetch_yelp_reviews_scroll

def fetch_yelp_reviews(url: str, limit: int = DEFAULT_YELP_LIMIT) -> list[dict]:
    """
    Try multiple Yelp review fetch methods in order:
    1. API
    2. Basic scrape by search
    3. Direct URL scrape
    4. Playwright scroll scrape
    """
    # 1. Try API if URL is not given (optional)
    # reviews = fetch_yelp_reviews_api(name, city, api_key, limit)
    # if reviews:
    #     return reviews

    # 2. Try basic scrape (if URL not available)
    # reviews = fetch_yelp_reviews_scrape(name, city, limit)
    # if reviews:
    #     return reviews

    # 3. Try direct URL scrape
    reviews = fetch_yelp_reviews_scrape_url(url, limit)
    if reviews:
        return reviews

    # 4. Fallback: Playwright scroll scraping
    reviews = fetch_yelp_reviews_scroll(url, limit)
    return reviews
