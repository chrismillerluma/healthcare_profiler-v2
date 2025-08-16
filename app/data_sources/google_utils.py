import requests
from bs4 import BeautifulSoup
from rapidfuzz import process, fuzz
import re

# -------------------------
# Normalize organization name
# -------------------------
def normalize_name(name: str) -> str:
    """
    Lowercase, remove punctuation, and remove common words like 'hospital' or 'clinic'.
    """
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    for word in ['hospital', 'medical center', 'center', 'clinic']:
        name = name.replace(word, '')
    return name.strip()

# -------------------------
# Google search pre-validation
# -------------------------
def google_search_name(name: str, limit: int = 3) -> list[dict]:
    """
    Performs a Google search and returns the top results as a list of dicts with title, link, and snippet.
    """
    query = requests.utils.quote(name)
    url = f"https://www.google.com/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for g in soup.find_all('div', class_='tF2Cxc')[:limit]:
            title = g.find('h3').get_text() if g.find('h3') else ''
            link = g.find('a')['href'] if g.find('a') else ''
            snippet = g.find('span', class_='aCOpRe').get_text() if g.find('span', class_='aCOpRe') else ''
            results.append({"title": title, "link": link, "snippet": snippet})
        return results
    except Exception:
        return []

# -------------------------
# Match organization to CMS dataset
# -------------------------
def match_org(name: str, df, state: str = None, city: str = None):
    """
    Matches a given organization name to the best candidate in the provided dataframe.
    Returns: matched row, column used, and match message.
    """
    if df.empty:
        return None, None, "No CMS data loaded"

    df_filtered = df.copy()
    if state:
        df_filtered = df_filtered[df_filtered['State'].str.upper() == state.upper()]
    if city:
        df_filtered = df_filtered[df_filtered['City'].str.upper() == city.upper()]
    if df_filtered.empty:
        return None, None, "No facilities found with specified state/city"

    name_cols = [c for c in df.columns if "name" in c.lower()]
    if not name_cols:
        return None, None, "No name column found in dataframe"

    col = name_cols[0]
    choices = df_filtered[col].dropna().tolist()
    choices_norm = [normalize_name(c) for c in choices]
    name_norm = normalize_name(name)

    match = process.extractOne(name_norm, choices_norm, scorer=fuzz.WRatio, score_cutoff=90)
    if match:
        _, score, idx = match
        return df_filtered.iloc[idx], col, f"Matched '{choices[idx]}' (score {score})"

    # Fallback: substring match
    subs = df_filtered[df_filtered[col].str.contains(name, case=False, na=False)]
    if not subs.empty:
        return subs.iloc[0], col, f"Substring fallback: '{subs.iloc[0][col]}'"

    return None, col, "No match found"
