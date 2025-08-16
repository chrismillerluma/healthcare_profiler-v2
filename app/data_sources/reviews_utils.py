import requests
from bs4 import BeautifulSoup
from datetime import datetime

def fetch_reviews(name, api_key=None, max_reviews=25):
    reviews_data = []
    place = {}

    if api_key:
        try:
            search_url = (
                f"https://maps.googleapis.com/maps/api/place/textsearch/json?"
                f"query={requests.utils.quote(name)}&key={api_key}"
            )
            search_resp = requests.get(search_url, timeout=10).json()
            results = search_resp.get("results", [])
            if results:
                place = results[0]
                place_id = place.get("place_id")
                if place_id:
                    details_url = (
                        f"https://maps.googleapis.com/maps/api/place/details/json?"
                        f"place_id={place_id}&fields=name,reviews,formatted_address,rating,"
                        f"user_ratings_total,formatted_phone_number,international_phone_number,"
                        f"website,opening_hours,geometry,types,place_id&key={api_key}"
                    )
                    details_resp = requests.get(details_url, timeout=10).json()
                    place = details_resp.get("result", {})
                    for r in place.get("reviews", []):
                        reviews_data.append({
                            "name": place.get("name"),
                            "address": place.get("formatted_address"),
                            "rating": r.get("rating"),
                            "user_ratings_total": place.get("user_ratings_total"),
                            "author_name": r.get("author_name"),
                            "review_text": r.get("text"),
                            "time": datetime.utcfromtimestamp(r.get("time")).isoformat() if r.get("time") else None
                        })
        except Exception:
            pass

    if len(reviews_data) < max_reviews:
        try:
            remaining = max_reviews - len(reviews_data)
            query = requests.utils.quote(name + " reviews")
            r = requests.get(f"https://www.google.com/search?q={query}", headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            snippets = [span.get_text() for span in soup.find_all("span") if len(span.get_text()) > 20][:remaining]
            for s in snippets:
                reviews_data.append({
                    "name": place.get("name") if place else None,
                    "address": place.get("formatted_address") if place else None,
                    "rating": None,
                    "user_ratings_total": place.get("user_ratings_total") if place else None,
                    "author_name": None,
                    "review_text": s,
                    "time": None
                })
        except Exception:
            pass

    return reviews_data[:max_reviews], place
