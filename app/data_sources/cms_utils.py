import os
import io
import re
import pandas as pd
import requests
import streamlit as st
import logging
from config import settings

# -------------------------
# Setup Logger
# -------------------------
logger = logging.getLogger("cms_loader")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def log_st(msg, level="info", show_in_ui=True):
    """Log message and optionally show in Streamlit UI"""
    log_level = "info" if level == "success" else level
    getattr(logger, log_level)(msg)
    
    if show_in_ui:
        if level == "info":
            st.info(msg)
        elif level == "success":
            st.success(msg)
        elif level == "error":
            st.error(msg)
        else:
            st.write(msg)

# -------------------------
# Load CMS General Info
# -------------------------
@st.cache_data
def load_cms_general_info(csv_path=None, show_ui_messages=True):
    backup_path = os.path.join(settings.DATA_DIR, "cms_hospitals_backup.csv")

    if csv_path:
        try:
            df = pd.read_csv(csv_path, dtype=str, on_bad_lines="skip")
            log_st(f"Loaded CMS general info from CSV path ({len(df)} records)", "success", show_ui_messages)
            return df
        except Exception as e:
            log_st(f"Cannot load CMS general info from {csv_path}: {e}", "error", show_ui_messages)
            return pd.DataFrame()

    try:
        r = requests.get(settings.CMS_GENERAL_URL, timeout=15)
        df = pd.read_csv(io.BytesIO(r.content), dtype=str, on_bad_lines="skip")
        log_st(f"Loaded CMS general info ({len(df)} records)", "success", show_ui_messages)
        return df
    except Exception:
        if os.path.exists(backup_path):
            for enc in ["utf-8", "latin1", "utf-16"]:
                try:
                    df = pd.read_csv(backup_path, dtype=str, encoding=enc, on_bad_lines="skip")
                    log_st(f"Loaded CMS general info from backup ({enc})", "success", show_ui_messages)
                    return df
                except Exception:
                    continue
        log_st("Cannot load CMS general info.", "error", show_ui_messages)
        return pd.DataFrame()

# -------------------------
# Load CMS Patient Surveys
# -------------------------
@st.cache_data
def load_cms_patient_surveys(csv_path=None, show_ui_messages=True):
    backup_path = os.path.join(settings.DATA_DIR, "cms_patient_surveys_backup.csv")

    if csv_path:
        try:
            df = pd.read_csv(csv_path, dtype=str, on_bad_lines="skip")
            log_st(f"Loaded CMS patient surveys from CSV path ({len(df)} records)", "success", show_ui_messages)
            return df
        except Exception as e:
            log_st(f"Cannot load CMS patient surveys from {csv_path}: {e}", "error", show_ui_messages)
            return pd.DataFrame()

    try:
        r = requests.get(settings.CMS_SURVEY_URL, timeout=15)
        df = pd.read_csv(io.BytesIO(r.content), dtype=str, on_bad_lines="skip")
        log_st(f"Loaded CMS patient surveys ({len(df)} records)", "success", show_ui_messages)
        return df
    except Exception:
        if os.path.exists(backup_path):
            for enc in ["utf-8", "latin1", "utf-16"]:
                try:
                    df = pd.read_csv(backup_path, dtype=str, encoding=enc, on_bad_lines="skip")
                    log_st(f"Loaded CMS patient surveys from backup ({enc})", "success", show_ui_messages)
                    return df
                except Exception:
                    continue
        log_st("Cannot load CMS patient surveys.", "error", show_ui_messages)
        return pd.DataFrame()

# -------------------------
# Find CCN Column
# -------------------------
def find_ccn_column(df):
    """Attempt to identify the CCN column in a CMS DataFrame"""
    for col in df.columns:
        if re.search(r'ccn|cms_certification_number', col, re.I):
            return col
    return None

# -------------------------
# Calculate CMS Score
# -------------------------
def calculate_cms_score(hospital_row):
    """
    Example scoring function based on available CMS fields.
    Adjust logic to your scoring rules.
    """
    score = 0
    try:
        rating = hospital_row.get("Hospital overall rating")
        if rating and rating.isdigit():
            score += int(rating) * 10  # Example multiplier
        survey_score = hospital_row.get("Patient survey star rating")
        if survey_score and survey_score.isdigit():
            score += int(survey_score) * 5
    except Exception as e:
        log_st(f"Error calculating CMS score: {e}", "error")
    return score

# -------------------------
# Fetch HCAHPS by CCN
# -------------------------
def fetch_hcahps_by_ccn(ccn, patient_survey_df):
    """Return the survey row for a given CCN"""
    ccn_col = find_ccn_column(patient_survey_df)
    if not ccn_col:
        return None
    row = patient_survey_df.loc[patient_survey_df[ccn_col] == str(ccn)]
    if not row.empty:
        return row.iloc[0].to_dict()
    return None
