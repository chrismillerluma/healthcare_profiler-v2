import os
import sys
from dotenv import load_dotenv
import json
import re
from datetime import datetime

import pandas as pd
import streamlit as st

# Add parent folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import modules
from config import settings
from data_sources.google_utils import google_search_name, match_org, normalize_name
from data_sources.cms_utils import load_cms_general_info, calculate_cms_score, find_ccn_column, fetch_hcahps_by_ccn
from data_sources.news_utils import fetch_news
from data_sources.website_scraper import scrape_about
from data_sources.usnews import fetch_usnews_rankings
from data_sources.yelp_utils import fetch_yelp_reviews_scrape, fetch_yelp_reviews_api
from export_utils import export_to_excel
from rapidfuzz import fuzz
from datetime import timezone

# Load environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY", "")
yelp_api_key = os.getenv("YELP_API_KEY", "")
default_location = os.getenv("DEFAULT_YELP_LOCATION", "San Francisco, CA")

# Streamlit page config
st.set_page_config(
    page_title="Healthcare Profiler (CMS + Reviews + News + Business Profile)",
    layout="wide"
)
st.title("Healthcare Organization Discovery Profiler — v2.0")

# Input API keys and location
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    gkey = st.text_input("Google Places API Key (optional)", value=google_api_key, type="password", key="google_api_key_input")
with col2:
    yelp_key = st.text_input("Yelp API Key (optional)", value=yelp_api_key, type="password", key="yelp_api_key_input")
with col3:
    default_loc = st.text_input("Default Location for Yelp (city, state)", value=default_location, key="default_loc_input")

# Cache CMS data
@st.cache_data
def load_cms():
    return load_cms_general_info(settings.CMS_GENERAL_INFO_CSV)

df_cms = load_cms()

# Organization input
org = st.text_input("Organization Name", placeholder="e.g., UCSF Medical Center")
search_button = st.button("Search")

# Main workflow
if org and search_button:
    # 1) Pre-validate via Google Search
    with st.spinner("Validating via Google search..."):
        google_hits = google_search_name(org, limit=settings.GOOGLE_SEARCH_PREVALIDATION_RESULTS)
        st.subheader("Top Google Search Hits")
        if google_hits:
            for hit in google_hits:
                st.markdown(f"- [{hit['title']}]({hit['link']}) — {hit['snippet']}")
        else:
            st.info("No results from Google pre-validation. Continuing with CMS match.")

        city, state = None, None
        for hit in google_hits or []:
            snippet = hit.get("snippet","")
            match_loc = re.search(r"\b([A-Za-z\s]+),\s([A-Z]{2})\b", snippet)
            if match_loc:
                city, state = match_loc.group(1), match_loc.group(2)
                break

    # 2) Fuzzy match to CMS
    with st.spinner("Matching organization with CMS..."):
        match, name_col, msg = match_org(org, df_cms, state=state, city=city)
        st.info(msg)

    if match is None:
        st.error("No match could be found in CMS. Try adjusting the name or adding city/state.")
        st.stop()

    st.subheader("Facility Info (CMS)")
    st.json(match.to_dict())

    # 3) News
    @st.cache_data
    def get_news(name):
        return fetch_news(name, limit=5)

    with st.spinner("Fetching Google News..."):
        news = get_news(match.get("Hospital Name") or match[name_col])
    st.subheader("Recent News")
    if news:
        for n in news:
            st.markdown(f"- [{n.get('title','No Title')}]({n.get('link','#')}) — {n.get('date','N/A')}")
    else:
        st.info("No recent news found.")

    # 4) Reviews & Google Business Profile
    from bs4 import BeautifulSoup
    import requests

    @st.cache_data
    def fetch_reviews(name, api_key=None, max_reviews=settings.DEFAULT_REVIEW_LIMIT):
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
            except Exception as e:
                st.warning(f"Failed to fetch reviews from Google Places API: {e}")

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

    with st.spinner("Fetching Google Reviews & Business Profile..."):
        revs, place_info = fetch_reviews(org, gkey, max_reviews=settings.DEFAULT_REVIEW_LIMIT)

    st.subheader("Reviews (Top 25, worst first if ratings exist)")
    if revs:
        df_revs = pd.DataFrame(revs)
        expected_cols = ["name", "author_name", "rating", "user_ratings_total", "address", "review_text", "time"]
        for c in expected_cols:
            if c not in df_revs.columns:
                df_revs[c] = None
        if "rating" in df_revs.columns and df_revs["rating"].notna().any():
            try:
                df_revs["rating"] = pd.to_numeric(df_revs["rating"], errors="coerce")
                df_revs = df_revs.sort_values("rating", ascending=True)
            except Exception:
                pass
        st.dataframe(df_revs[expected_cols].head(25))
    else:
        st.info("No reviews found.")

    st.subheader("Google Business Profile Info")
    if place_info:
        st.json({
            "name": place_info.get("name"),
            "address": place_info.get("formatted_address"),
            "rating": place_info.get("rating"),
            "user_ratings_total": place_info.get("user_ratings_total"),
            "phone": place_info.get("formatted_phone_number"),
            "international_phone": place_info.get("international_phone_number"),
            "website": place_info.get("website"),
            "opening_hours": place_info.get("opening_hours"),
            "geometry": place_info.get("geometry"),
            "types": place_info.get("types"),
            "place_id": place_info.get("place_id")
        })

    # 5) About (website scrape)
    about_data = {}
    if place_info:
        with st.spinner("Scraping website for About info..."):
            about_data = scrape_about(place_info.get("website"))
    if about_data:
        st.subheader("About (from Website)")
        st.json(about_data)

    # 6) CMS + Combined Score
    cms_score = calculate_cms_score(match)
    google_score = place_info.get("rating") if place_info else None
    combined_score = None
    if cms_score and google_score:
        combined_score = round(0.5*float(google_score) + 0.5*float(cms_score), 2)
    elif cms_score:
        combined_score = float(cms_score)
    elif google_score:
        combined_score = float(google_score)

    st.subheader("Business / Reputation Score")
    if combined_score is not None:
        st.metric("Score (0–5 scale)", combined_score)
    else:
        st.info("Insufficient data to compute combined score.")

    # --- 7) U.S. News ---
    st.subheader("U.S. News & World Report")
    @st.cache_data
    def get_usnews(name):
        return fetch_usnews_rankings(name)

    try:
        with st.spinner("Fetching U.S. News & World Report rankings..."):
            usnews_data = get_usnews(match.get("Hospital Name") or match[name_col])
        if usnews_data and "error" not in usnews_data:
            st.write(f"**Ranking:** {usnews_data.get('ranking','N/A')}")
            if usnews_data.get("specialties"):
                st.write("**Top Specialties:**")
                for sp in usnews_data["specialties"][:10]:
                    st.write(f"- {sp}")
        else:
            st.info("U.S. News data not available for this facility at this time.")
    except Exception as e:
        st.info(f"U.S. News data not available: {e}")

# --- 8) Yelp Reviews ---
st.subheader("Yelp Reviews (sample)")

@st.cache_data
def get_yelp(name, city=None, key=None):
    """
    Fetch Yelp reviews, preferring API if key is present, otherwise fallback to scraper.
    """
    if key:
        # Use CMS hospital name + city for better match
        return fetch_yelp_reviews_api(name, city, key, limit=5)
    else:
        return fetch_yelp_reviews_scrape(name, location=city, limit=5)

if org and search_button:
    try:
        cms_name = match.get("Hospital Name") if match is not None else org
        cms_city = match.get("City") if match is not None else default_loc

        with st.spinner("Fetching Yelp reviews..."):
            yelp_reviews = get_yelp(cms_name, city=cms_city, key=yelp_key)

        if yelp_reviews:
            for r in yelp_reviews:
                st.markdown(f"**{r.get('name','Unknown')}** ({r.get('location','N/A')}) ⭐ {r.get('rating','N/A')}")
                if r.get("review_text"):
                    st.caption(r["review_text"])
                st.markdown("---")
        else:
            st.info("No Yelp reviews found for this facility.")
    except Exception as e:
        st.info(f"Yelp reviews not available: {e}")

    # --- 9) CMS HCAHPS ---
    st.subheader("CMS Patient Survey (HCAHPS)")
    ccn_col = find_ccn_column(df_cms)
    hcahps_df = None
    if ccn_col and (ccn := match.get(ccn_col)):
        try:
            with st.spinner("Fetching CMS Patient Survey (HCAHPS) data..."):
                hcahps_df = fetch_hcahps_by_ccn(ccn)
            if hcahps_df is not None and not hcahps_df.empty:
                st.dataframe(hcahps_df.head(50))
            else:
                st.info("HCAHPS data not available via API for this facility.")
        except Exception as e:
            st.info(f"HCAHPS data not available: {e}")
    else:
        st.info("No CCN found in CMS data; cannot fetch HCAHPS.")

    # --- 10) Export ---
    st.subheader("Download")
    excel_data = export_to_excel(
        match=match,
        news=news,
        reviews=revs,
        place_info=place_info,
        about_data=about_data,
        usnews_data=usnews_data,
        yelp_reviews=yelp_reviews,
        hcahps_df=hcahps_df if hcahps_df is not None else pd.DataFrame(),
        org=org
    )
    st.download_button(
        label="Download Full Profile (Excel)",
        data=excel_data,
        file_name=f"{normalize_name(org)}_profile.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
