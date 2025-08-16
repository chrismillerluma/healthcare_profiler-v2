# yelp_utils.py
import requests
import logging
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

YELP_SEARCH_URL = "https://api.yelp.com/v3/businesses/search"
YELP_REVIEWS_URL = "https://api.yelp.com/v3/businesses/{id}/reviews"

# -------------------------
# Fetch Yelp Reviews via API
# -------------------------
def fetch_yelp_reviews_api(name, city, api_key, limit=5):
    """
    Query Yelp API for business by name + city, then fetch reviews.
    Uses fuzzy matching to pick the closest business name.
    """
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {
            "term": name,
            "location": city if city else "United States",
            "limit": 10  # get a batch to fuzzy match
        }
        resp = requests.get(YELP_SEARCH_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        businesses = resp.json().get("businesses", [])

        if not businesses:
            logger.warning(f"No businesses found for {name}, {city}")
            return []

        # Fuzzy match CMS hospital name to Yelp results
        candidates = [(biz["name"], biz) for biz in businesses]
        best_match = process.extractOne(
            name,
            [c[0] for c in candidates],
            scorer=fuzz.token_sort_ratio
        )

        if not best_match:
            logger.warning(f"No fuzzy match found for {name}, {city}")
            return []

        _, score, idx = best_match
        best = candidates[idx][1]

        biz_id = best["id"]

        # Fetch reviews for best match
        reviews_resp = requests.get(YELP_REVIEWS_URL.format(id=biz_id), headers=headers, timeout=10)
        reviews_resp.raise_for_status()
        reviews = reviews_resp.json().get("reviews", [])

        results = []
        for r in reviews[:limit]:
            results.append({
                "name": best.get("name"),
                "location": ", ".join(best.get("location", {}).get("display_address", [])),
                "rating": r.get("rating"),
                "review_text": r.get("text"),
                "url": r.get("url"),
            })
        return results

    except Exception as e:
        logger.error(f"Yelp API error for {name}, {city}: {e}")
        return []

# -------------------------
# Fallback Scraper (if no API key)
# -------------------------
def fetch_yelp_reviews_scrape(name, location=None, limit=3):
    """
    Placeholder scraper logic — currently just returns empty list.
    You can expand later if needed.
    """
    logger.info(f"Scraper fallback not implemented for {name}, {location}")
    return []
