import re
import requests
from bs4 import BeautifulSoup
from rapidfuzz import process, fuzz

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}

def normalize_name(name: str) -> str:
    import re
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    for word in ["hospital", "medical center", "center", "clinic"]:
        name = name.replace(word, "")
    return name.strip()

def google_search_name(name: str, limit: int = 3):
    """Lightweight HTML scrape of Google results (best-effort)."""
    query = requests.utils.quote(name)
    url = f"https://www.google.com/search?q={query}"
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for g in soup.find_all("div", class_="tF2Cxc")[:limit]:
            title = g.find("h3").get_text() if g.find("h3") else ""
            link = g.find("a")["href"] if g.find("a") else ""
            snippet_el = g.find("span", class_="aCOpRe") or g.find("div", class_="VwiC3b")
            snippet = snippet_el.get_text() if snippet_el else ""
            results.append({"title": title, "link": link, "snippet": snippet})
        return results
    except Exception:
        return []

def match_org(name, df, state=None, city=None):
    """Fuzzy match organization in CMS dataframe with optional city/state filtering."""
    df_filtered = df.copy()
    if state and "State" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["State"].str.upper() == state.upper()]
    if city and "City" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["City"].str.upper() == city.upper()]
    if df_filtered.empty:
        return None, None, "No facilities found with specified state/city"

    name_cols = [c for c in df_filtered.columns if "name" in c.lower()]
    if not name_cols:
        return None, None, "No name column in CMS file"
    col = name_cols[0]
    choices = df_filtered[col].dropna().tolist()
    choices_norm = [normalize_name(c) for c in choices]
    name_norm = normalize_name(name)

    best = process.extractOne(name_norm, choices_norm, scorer=fuzz.WRatio, score_cutoff=90)
    if best:
        _, score, idx = best
        return df_filtered.iloc[idx], col, f"Matched '{choices[idx]}' (score {score})"

    subs = df_filtered[df_filtered[col].str.contains(name, case=False, na=False)]
    if not subs.empty:
        return subs.iloc[0], col, f"Substring fallback: '{subs.iloc[0][col]}'"
    return None, col, "No match found"