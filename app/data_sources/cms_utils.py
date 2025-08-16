import os
import io
import pandas as pd
import requests
from config import settings
import streamlit as st

# -------------------------
# Load CMS General Info
# -------------------------
@st.cache_data
def load_cms_general_info():
    backup_path = os.path.join(settings.DATA_DIR, "cms_hospitals_backup.csv")
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
def load_cms_patient_surveys():
    backup_path = os.path.join(settings.DATA_DIR, "cms_patient_surveys_backup.csv")
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
# Example metric extraction
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

    # Example: average a few numeric fields if they exist
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