import os
import sys
from dotenv import load_dotenv
import json
import re
from datetime import datetime, timezone
import asyncio

import pandas as pd
import streamlit as st
import aiohttp
from aiolimiter import AsyncLimiter
import nest_asyncio
from bs4 import BeautifulSoup

# Add parent folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import modules
from config import settings
from data_sources.google_utils import google_search_name, match_org, normalize_name
from data_sources.cms_utils import load_cms_general_info, calculate_cms_score
from data_sources.website_scraper import scrape_about
from data_sources.yelp_utils import fetch_yelp_reviews_scrape_url
from export_utils import export_to_excel

# Load environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY", "")
default_location = os.getenv("DEFAULT_YELP_LOCATION", "San Francisco, CA")

# Streamlit page config
st.set_page_config(
    page_title="Healthcare Profiler (CMS + Reviews + News + Business Profile)",
    layout="wide"
)
st.title("Healthcare Org Discovery Profiler — v2.0")

# Input API keys and location
col1, col2 = st.columns([1,1])
with col1:
    gkey = st.text_input("Google Places API Key (optional)", value=google_api_key, type="password")
with col2:
    default_loc = st.text_input("Default Location for Yelp (city, state)", value=default_location)

# Cache CMS data
@st.cache_data
def load_cms():
    return load_cms_general_info(settings.CMS_GENERAL_INFO_CSV)

df_cms = load_cms()

# Organization input
org_input = st.text_input("Organization Name", placeholder="e.g., UCSF Medical Center")
search_button = st.button("Search")

# --- Async Limiters ---
google_limiter = AsyncLimiter(max_rate=5, time_period=1)

# --- Async fetch wrappers ---
async def limited_google_search(query, api_key):
    async with google_limiter:
        async with aiohttp.ClientSession() as session:
            url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={api_key}"
            async with session.get(url, timeout=10) as resp:
                return await resp.json()

async def limited_google_details(place_id, api_key):
    async with google_limiter:
        async with aiohttp.ClientSession() as session:
            url = (
                f"https://maps.googleapis.com/maps/api/place/details/json?"
                f"place_id={place_id}&fields=name,reviews,formatted_address,rating,"
                f"user_ratings_total,formatted_phone_number,international_phone_number,"
                f"website,opening_hours,geometry,types,place_id&key={api_key}"
            )
            async with session.get(url, timeout=10) as resp:
                return await resp.json()

# Streamlit-friendly async
nest_asyncio.apply()

# --- Main workflow ---
if org_input and search_button:
    # 1) Pre-validate via Google Search
    with st.spinner("Validating via Google search..."):
        google_hits = google_search_name(org_input, limit=settings.GOOGLE_SEARCH_PREVALIDATION_RESULTS)
        st.subheader("Top Google Search Hits")
        if google_hits:
            for hit in google_hits:
                st.markdown(f"- [{hit['title']}]({hit['link']}) — {hit['snippet']}")
        else:
            st.info("No results from Google pre-validation. Continuing with CMS match.")

        # Extract city/state from snippet if possible
        city, state = None, None
        for hit in google_hits or []:
            snippet = hit.get("snippet","")
            match_loc = re.search(r"\b([A-Za-z\s]+),\s([A-Z]{2})\b", snippet)
            if match_loc:
                city, state = match_loc.group(1), match_loc.group(2)
                break

    # 2) Match CMS
    with st.spinner("Matching organization with CMS..."):
        match, name_col, msg = match_org(org_input, df_cms, state=state, city=city)
        st.info(msg)

    if match is None:
        st.error("No match could be found in CMS. Try adjusting the name or adding city/state.")
        st.stop()

    st.subheader("Facility Info (CMS)")
    st.json(match.to_dict())

    # Normalize org name and location for Google API
    org_name_for_api = normalize_name(match.get("Hospital Name") or org_input)
    cms_city = match.get("City") or city or "San Francisco"

    st.write(f"Fetching Google Business Profile for: {org_name_for_api}, {cms_city}")

    # --- Async fetch Google ---
    async def fetch_google_profile(org_name):
        google_reviews = []
        place_info = {}
        if gkey:
            search_data = await limited_google_search(org_name, gkey)
            results = search_data.get("results", [])
            if results:
                place = results[0]
                place_id = place.get("place_id")
                if place_id:
                    details = await limited_google_details(place_id, gkey)
                    place_info = details.get("result", {})
                    for r in place_info.get("reviews", []):
                        google_reviews.append({
                            "name": place_info.get("name"),
                            "address": place_info.get("formatted_address"),
                            "rating": r.get("rating"),
                            "user_ratings_total": place_info.get("user_ratings_total"),
                            "author_name": r.get("author_name"),
                            "review_text": r.get("text"),
                            "time": datetime.fromtimestamp(r.get("time"), tz=timezone.utc).isoformat() if r.get("time") else None
                        })
        return google_reviews, place_info

    google_reviews, place_info = asyncio.run(fetch_google_profile(org_name_for_api))

    # 3) Display Google Reviews
    st.subheader("Google Reviews (Top 25)")
    if google_reviews:
        df_revs = pd.DataFrame(google_reviews)
        expected_cols = ["name","author_name","rating","user_ratings_total","address","review_text","time"]
        for c in expected_cols:
            if c not in df_revs.columns:
                df_revs[c] = None
        if "rating" in df_revs.columns and df_revs["rating"].notna().any():
            df_revs["rating"] = pd.to_numeric(df_revs["rating"], errors="coerce")
            df_revs = df_revs.sort_values("rating", ascending=True)
        st.dataframe(df_revs[expected_cols].head(25))
    else:
        st.info("No Google reviews found.")

    # 4) Google Business Profile
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

    # 5) Website About
    about_data = {}
    if place_info.get("website"):
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
        combined_score = round(0.5*float(google_score) + 0.5*float(cms_score),2)
    elif cms_score:
        combined_score = float(cms_score)
    elif google_score:
        combined_score = float(google_score)

    st.subheader("CMS & Combined Scores")
    st.write("CMS Score:", cms_score)
    st.write("Google Rating:", google_score)
    st.write("Combined Score:", combined_score)

    # 7) Yelp Reviews Manual URL
    st.subheader("Fetch Yelp Reviews via Manual URL")
    if "yelp_reviews_manual" not in st.session_state:
        st.session_state.yelp_reviews_manual = []

    st.session_state.manual_yelp_url = st.text_input("Enter Yelp Business URL (optional)", value="")
    if st.button("Fetch Yelp Reviews Manually"):
        if st.session_state.manual_yelp_url:
            try:
                st.session_state.yelp_reviews_manual = fetch_yelp_reviews_scrape_url(
                    st.session_state.manual_yelp_url
                )
                st.success(f"Fetched {len(st.session_state.yelp_reviews_manual)} Yelp reviews manually.")
            except Exception as e:
                st.error(f"Failed to fetch Yelp reviews: {e}")

    if st.session_state.yelp_reviews_manual:
        st.subheader("Yelp Reviews (Manual URL)")
        st.dataframe(pd.DataFrame(st.session_state.yelp_reviews_manual))

# --- 8) OTHER DATA / Manual Paste ---
st.subheader("Manual Data Entry (US News, Yelp, Other)")

if "manual_data" not in st.session_state:
    st.session_state.manual_data = {"usnews": {}, "yelp": [], "other": {}}

# --- US News Manual Input (Merged) ---
usnews_text = st.text_area("Paste US News text/HTML or rank info here", height=150)
if st.button("Parse US News Data"):
    if usnews_text:
        try:
            soup = BeautifulSoup(usnews_text, "html.parser")
            rank_tag = soup.find(string=lambda t: t and "rank" in t.lower())
            st.session_state.manual_data["usnews"] = {
                "rank_text": rank_tag.strip() if rank_tag else usnews_text.strip(),
                "raw_html": usnews_text
            }
            st.success("US News data parsed and saved.")
        except Exception as e:
            st.warning(f"Failed to parse US News: {e}")
            st.session_state.manual_data["usnews"] = {"raw_html": usnews_text.strip()}

# --- Yelp Manual HTML ---
yelp_html = st.text_area("Paste Yelp HTML here", height=150)
if st.button("Parse Yelp Data"):
    if yelp_html:
        try:
            soup = BeautifulSoup(yelp_html, "html.parser")
            yelp_reviews_parsed = []
            review_blocks = soup.find_all("div", class_="review")
            for r in review_blocks:
                author = r.find("span", class_="fs-block").get_text(strip=True) if r.find("span", class_="fs-block") else None
                rating = r.find("div", role="img")["aria-label"].split()[0] if r.find("div", role="img") else None
                text = r.find("p").get_text(strip=True) if r.find("p") else None
                date = r.find("span", class_="css-e81eai").get_text(strip=True) if r.find("span", class_="css-e81eai") else None
                yelp_reviews_parsed.append({"author": author, "rating": rating, "text": text, "date": date})
            st.session_state.manual_data["yelp"] = yelp_reviews_parsed
            st.success(f"Parsed {len(yelp_reviews_parsed)} Yelp reviews.")
        except Exception as e:
            st.warning(f"Failed to parse Yelp HTML: {e}")
            st.session_state.manual_data["yelp"] = []

# --- Other Free Paste ---
other_html = st.text_area("Paste any other HTML or text data here", height=100)
if st.button("Save Other Data"):
    if other_html:
        st.session_state.manual_data["other"] = {"raw_html": other_html}
        st.success("Other data saved.")

# --- 9) Export All Data ---
if st.button("Export All Data to Excel (including manual HTML)"):
    yelp_reviews_combined = st.session_state.yelp_reviews_manual + st.session_state.manual_data.get("yelp", [])
    export_to_excel(
        org_name_for_api,
        cms_data=match,
        google_reviews=google_reviews,
        yelp_reviews=yelp_reviews_combined,
        about_data=about_data,
        other_data=st.session_state.manual_data
    )
    st.success("Exported all data (including manual HTML) to Excel successfully!")
