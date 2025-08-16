import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}

def fetch_usnews_rankings(hospital_name: str, city: str = None):
    """
    Fetch US News rankings for a hospital.
    Optionally include city for more accurate results.
    Returns a dict with:
      - ranking: string ("N/A" if not found)
      - specialties: list of strings
      - error: optional string if any problem occurred
    """
    if not hospital_name or not hospital_name.strip():
        return {"ranking": "N/A", "specialties": [], "error": "No hospital name provided"}

    try:
        # Build search query
        query = hospital_name.strip()
        if city and city.strip():
            query += f" {city.strip()}"
        query = query.replace(" ", "+")

        url = f"https://health.usnews.com/best-hospitals/search?hospital_name={query}"

        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        if r.status_code != 200:
            return {"ranking": "N/A", "specialties": [], "error": f"HTTP {r.status_code}"}

        soup = BeautifulSoup(r.text, "html.parser")

        # Try to find the first search result
        ranking = "N/A"
        ranking_el = soup.find("div", {"data-test-id": "search-result"})
        if ranking_el:
            badge = ranking_el.find("span")
            if badge and badge.get_text(strip=True):
                ranking = badge.get_text(strip=True)

        # Collect specialties
        specialties = []
        for s in soup.select("[data-test-id='specialty']"):
            txt = s.get_text(strip=True)
            if txt:
                specialties.append(txt)

        return {"ranking": ranking, "specialties": specialties}

    except Exception as e:
        return {"ranking": "N/A", "specialties": [], "error": f"Failed to fetch U.S. News data: {e}"}

# manual scrape workflow items
def fetch_usnews_rankings_url(url: str) -> dict:
    """Scrape US News ranking info directly from a hospital URL."""
    # Your existing US News scraping logic adapted to accept full URL
    pass