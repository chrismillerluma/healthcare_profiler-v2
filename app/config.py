import os

class Settings:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    
    # CMS URLs
    CMS_GENERAL_URL = (
        "https://data.cms.gov/provider-data/sites/default/files/resources/"
        "893c372430d9d71a1c52737d01239d47_1753409109/Hospital_General_Information.csv"
    )
    CMS_SURVEY_URL = (
        "https://data.medicare.gov/api/views/9a2x-57i7/rows.csv?accessType=DOWNLOAD"
    )
    
    # Local data folder
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
    
    # Local CSV paths
    CMS_GENERAL_INFO_CSV = os.path.join(DATA_DIR, "Hospital_General_Information.csv")
    CMS_PATIENT_SURVEYS_CSV = os.path.join(DATA_DIR, "Hospital_Patient_Surveys.csv")
    
    # Limits / defaults
    GOOGLE_SEARCH_PREVALIDATION_RESULTS = 5
    DEFAULT_REVIEW_LIMIT = 25

# Instantiate
settings = Settings()
