# Healthcare Profiler v2.0

A Streamlit app to build an at-a-glance profile of a U.S. hospital/health system by combining:
- CMS Hospital General Info (official CSV)
- Google pre-validation & Google Places details + reviews (optional API key)
- Website "About" scrape
- Google News (RSS)
- U.S. News & World Report (best-effort scrape)
- Yelp reviews (Yelp API if provided, else best-effort scrape)
- CMS Patient Survey (HCAHPS) (best-effort via CMS data API — falls back gracefully)

## Quickstart

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

## Optional API Keys
- **Google Places API Key**: enhances reviews and business profile.
- **Yelp API Key**: if provided, uses Yelp Fusion API; otherwise falls back to scraping.

Keys are entered in the UI. Nothing is stored.

## Notes & Caveats
- Scraping Google/Yelp/USNews can be brittle if their markup changes.
- HCAHPS API endpoint can change; the app fails gracefully and continues even if the dataset is unavailable.
- Always respect the sites’ terms of service for scraping.

## Export
Click “Download Full Profile (Excel)” to export all collected sections into a multi-sheet workbook.

## Project Layout

```
healthcare-profiler-v2/
├── app/
│   ├── main.py
│   ├── export_utils.py
│   └── data_sources/
│       ├── cms_utils.py
│       ├── google_utils.py
│       ├── news_utils.py
│       ├── usnews.py
│       └── yelp_utils.py
├── config.py
├── requirements.txt
└── README.md
```

## License
For internal/demo use. Validate data licensing before redistribution.