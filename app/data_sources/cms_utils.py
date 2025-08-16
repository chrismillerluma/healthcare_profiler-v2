import os
import io
import pandas as pd
import requests
import streamlit as st
from config import settings

# -------------------------
# Load CMS General Info
# -------------------------
@st.cache_data
def load_cms_general_info(csv_path=None):
    """
    Load CMS general info from URL or backup.
    If csv_path is provided, load from local CSV instead.
    """
    backup_path = os.path.join(settings.DATA_DIR, "cms_hospitals_backup.csv")

    # Use CSV path if provided
    if csv_path is not None:
        try:
            df = pd.read_csv(csv_path, dtype=str, on_bad_lines="skip")
            st.success(f"Loaded CMS general info from CSV path ({len(df)} records)")
            return df
        except Exception as e:
            st.error(f"Cannot load CMS general info from {csv_path}: {e}")
            return pd.DataFrame()

    # Otherwise try URL
    try:
        r = requests.get(settings.CMS_GENERAL_URL, timeout=15)
        df = pd.read_csv(io.BytesIO(r.content), dtype=str, on_bad_lines="skip")
        st.success(f"Loaded CMS general info ({len(df)} records)")
        return df
    except Exception:
        if os.path.exists(backup_path):
            for enc in ["utf-8", "latin1", "utf-16"]:
                try:
                    df = pd.read_csv(backup_path, dtype=str, encoding=enc, on_bad_lines="skip")
                    st.success(f"Loaded CMS general info from backup ({enc})")
                    return df
                except Exception:
                    continue
        st.error("Cannot load CMS general info.")
        return pd.DataFrame()

# -------------------------
# Load CMS Patient Survey Data
# -------------------------
@st.cache_data
def load_cms_patient_surveys(csv_path=None):
    """
    Load CMS patient surveys from URL or backup.
    If csv_path is provided, load from local CSV instead.
    """
    backup_path = os.path.join(settings.DATA_DIR, "cms_patient_surveys_backup.csv")

    if csv_path is not None:
        try:
            df = pd.read_csv(csv_path, dtype=str, on_bad_lines="skip")
            st.success(f"Loaded CMS patient surveys from CSV path ({len(df)} records)")
            return df
        except Exception as e:
            st.error(f"Cannot load CMS patient surveys from {csv_path}: {e}")
            return pd.DataFrame()

    try:
        r = requests.get(settings.CMS_SURVEY_URL, timeout=15)
        df = pd.read_csv(io.BytesIO(r.content), dtype=str, on_bad_lines="skip")
        st.success(f"Loaded CMS patient surveys ({len(df)} records)")
        return df
    except Exception:
        if os.path.exists(backup_path):
            for enc in ["utf-8", "latin1", "utf-16"]:
                try:
                    df = pd.read_csv(backup_path, dtype=str, encoding=enc, on_bad_lines="skip")
                    st.success(f"Loaded CMS patient surveys from backup ({enc})")
                    return df
                except Exception:
                    continue
        st.error("Cannot load CMS patient surveys.")
        return pd.DataFrame()

# -------------------------
# Extract Patient Survey Metrics
# -------------------------
def get_patient_survey_metrics(df_survey, hospital_name):
    """Return dictionary of key patient survey scores for a hospital"""
    if df_survey.empty:
        return {}
    row = df_survey[df_survey['Hospital Name'].str.contains(hospital_name, case=False, na=False)]
    if row.empty:
        return {}
    row = row.iloc[0]
    metrics = {
        "HCAHPS_Overall_Rating": row.get("HCAHPS_Overall_Rating"),
        "Communication_Doctors": row.get("Communication_Doctors"),
        "Communication_Nurses": row.get("Communication_Nurses"),
        "Cleanliness": row.get("Cleanliness"),
        "Pain_Management": row.get("Pain_Management"),
    }
    return metrics

# -------------------------
# Calculate CMS Score
# -------------------------
def calculate_cms_score(hospital_row):
    """
    Compute a CMS score (0–5 scale) from a CMS hospital row.
    hospital_row: a pandas Series representing a hospital
    """
    if hospital_row is None or hospital_row.empty:
        return None

    try:
        scores = []
        for col in ["HCAHPS_Overall_Rating", "Communication_Doctors", 
                    "Communication_Nurses", "Cleanliness", "Pain_Management"]:
            val = hospital_row.get(col)
            if val is not None:
                try:
                    scores.append(float(val))
                except ValueError:
                    continue
        if scores:
            return round(sum(scores) / len(scores), 2)
        return None
    except Exception:
        return None

# -------------------------
# Utility: Find CCN Column
# -------------------------
def find_ccn_column(df):
    """
    Identify which column in CMS dataframe contains the CCN (CMS Certification Number)
    """
    for col in df.columns:
        if "CCN" in col.upper() or "CMS Certification Number".upper() in col.upper():
            return col
    return None

# -------------------------
# Placeholder: Fetch HCAHPS by CCN
# -------------------------
def fetch_hcahps_by_ccn(ccn):
    """
    Fetch CMS HCAHPS patient survey data for a given CCN
    Placeholder: return empty DataFrame or implement API call
    """
    return pd.DataFrame()
