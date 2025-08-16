import io
import re
import requests
import pandas as pd
from typing import Optional, Dict

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}

def load_cms_general_info(csv_url: str) -> pd.DataFrame:
    try:
        r = requests.get(csv_url, timeout=15, headers=DEFAULT_HEADERS)
        df = pd.read_csv(io.BytesIO(r.content), dtype=str, on_bad_lines="skip")
        return df
    except Exception:
        return pd.DataFrame()

def find_ccn_column(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        lc = c.lower()
        if "ccn" in lc or "facility id" in lc or "provider id" in lc or "provider number" in lc:
            return c
    return None

def calculate_cms_score(row: pd.Series) -> Optional[float]:
    """Compute a simple average across selected CMS indicators on a 1–5ish scale."""
    score = 0.0
    count = 0
    def nat_comp(v):
        if not isinstance(v, str):
            return None
        v = v.lower()
        if "below" in v: return 5
        if "same" in v: return 3
        if "above" in v: return 1
        return None

    metric_map = {
        "Hospital overall rating": lambda x: float(x) if str(x).strip().replace('.','',1).isdigit() else None,
        "Mortality national comparison": nat_comp,
        "Safety of care national comparison": nat_comp,
        "Readmission national comparison": nat_comp,
        "Patient experience national comparison": nat_comp,
        "Patient experience rating": lambda x: float(x) if str(x).strip().replace('.','',1).isdigit() else None,
    }
    for col, fn in metric_map.items():
        if col in row:
            try:
                val = fn(row[col])
                if val is not None:
                    score += float(val)
                    count += 1
            except Exception:
                pass
    return round(score / count, 2) if count else None

def fetch_hcahps_by_ccn(ccn: str) -> pd.DataFrame:
    """
    Best-effort pull of HCAHPS (patient survey) via CMS provider-data API.
    If the API format or dataset id changes, this will safely return an empty DataFrame.
    """
    # Known dataset: HCAHPS - Hospital (dataset id may change; trying a stable CSV endpoint)
    # As a fallback, query "HCAHPS - Hospital" flat files (older dumps aren’t guaranteed).
    # We keep this resilient: return empty on any failure.
    try:
        # Example endpoint pattern (subject to change by CMS):
        # This is a placeholder; app will handle empty gracefully.
        base = "https://data.cms.gov/data-api/v1/dataset/77hc-e3se/data"  # example dataset id
        params = {"filter": json.dumps({"provider_id": [ccn]}), "size": 2000}
        r = requests.get(base, params=params, timeout=15, headers=DEFAULT_HEADERS)
        if r.ok:
            df = pd.DataFrame(r.json())
            return df
    except Exception:
        pass
    return pd.DataFrame()