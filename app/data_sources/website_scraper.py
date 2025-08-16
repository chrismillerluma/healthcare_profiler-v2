import requests
from bs4 import BeautifulSoup

def scrape_about(website_url):
    if not website_url:
        return {}
    try:
        r = requests.get(website_url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
        meta_desc = ""
        desc_tag = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
        if desc_tag and desc_tag.get("content"):
            meta_desc = desc_tag["content"].strip()
        h1_text = soup.find("h1").get_text().strip() if soup.find("h1") else ""
        return {"title": title, "meta_description": meta_desc, "h1": h1_text, "url": website_url}
    except Exception:
        return {}
