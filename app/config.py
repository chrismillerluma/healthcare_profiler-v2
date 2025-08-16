from dataclasses import dataclass

@dataclass
class Settings:
    CMS_GENERAL_INFO_CSV: str = (
        "https://data.cms.gov/provider-data/sites/default/files/resources/"
        "893c372430d9d71a1c52737d01239d47_1753409109/Hospital_General_Information.csv"
    )
    GOOGLE_SEARCH_UA: str = "Mozilla/5.0"
    DEFAULT_REVIEW_LIMIT: int = 25
    GOOGLE_SEARCH_PREVALIDATION_RESULTS: int = 3

settings = Settings()
