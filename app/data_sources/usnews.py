import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_usnews_rankings(hospital_name: str):
    url = f"https://health.usnews.com/best-hospitals/search?hospital_name={hospital_name.replace(' ', '+')}"
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        ranking = None
        ranking_el = soup.find("div", {"data-test-id":"search-result"})
        if ranking_el:
            badge = ranking_el.find("span")
            ranking = badge.get_text(strip=True) if badge else None
        specialties = []
        for s in soup.select("[data-test-id='specialty']"):
            txt = s.get_text(strip=True)
            if txt:
                specialties.append(txt)
        return {"ranking": ranking or "N/A", "specialties": specialties}
    except Exception as e:
        return {"error": f"Failed to fetch U.S. News data: {e}"}