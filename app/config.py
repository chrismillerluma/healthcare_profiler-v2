import os

class Settings:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    CMS_GENERAL_URL = (
        "https://data.cms.gov/provider-data/sites/default/files/resources/"
        "893c372430d9d71a1c52737d01239d47_1753409109/Hospital_General_Information.csv"
    )
    CMS_SURVEY_URL = (
        "https://data.medicare.gov/api/views/9a2x-57i7/rows.csv?accessType=DOWNLOAD"
    )
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

settings = Settings()
