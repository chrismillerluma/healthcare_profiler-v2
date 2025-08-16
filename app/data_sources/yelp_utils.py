import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_yelp_reviews_scrape(hospital_name: str, location: str = "", limit: int = 5):
    """Best-effort HTML scraping fallback when no Yelp API key is provided."""
    q = f"{hospital_name} {location} reviews".strip().replace(" ", "+")
    url = f"https://www.yelp.com/search?find_desc={q}"
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        reviews = []
        # Yelp DOM changes often; this is a heuristic selector
        for review in soup.find_all("p"):
            txt = review.get_text(" ", strip=True)
            if txt and len(txt) > 40:
                reviews.append(txt)
                if len(reviews) >= limit:
                    break
        return reviews
    except Exception as e:
        return [f"Failed to fetch Yelp reviews: {e}"]

def fetch_yelp_reviews_api(hospital_name: str, location: str, api_key: str, limit: int = 5):
    """Yelp Fusion API (requires API key)."""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"term": hospital_name, "location": location, "limit": 1}
        srch = requests.get("https://api.yelp.com/v3/businesses/search", headers=headers, params=params, timeout=15)
        srchj = srch.json()
        if not srchj.get("businesses"):
            return []
        biz_id = srchj["businesses"][0]["id"]
        rev = requests.get(f"https://api.yelp.com/v3/businesses/{biz_id}/reviews", headers=headers, timeout=15)
        items = rev.json().get("reviews", [])
        out = []
        for it in items[:limit]:
            out.append(f"{it.get('rating','?')}★ — {it.get('user',{}).get('name','Anon')}: {it.get('text','')}")
        return out
    except Exception as e:
        return [f"Failed Yelp API: {e}"]