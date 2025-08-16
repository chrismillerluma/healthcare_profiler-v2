import io
import pandas as pd

def export_to_excel(match, news, reviews, place_info, about_data, usnews_data, yelp_reviews, hcahps_df, org):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Facility Info
        if match is not None:
            pd.DataFrame([match.to_dict()]).to_excel(writer, sheet_name="Facility Info", index=False)
        # News
        if news:
            pd.DataFrame(news).to_excel(writer, sheet_name="News", index=False)
        # Reviews
        if reviews:
            df_revs = pd.DataFrame(reviews)
            expected_cols = ["name","author_name","rating","user_ratings_total","address","review_text","time"]
            for col in expected_cols:
                if col not in df_revs.columns:
                    df_revs[col] = None
            df_revs.to_excel(writer, sheet_name="Reviews", index=False)
        # Business Profile
        if place_info:
            pd.DataFrame([place_info]).to_excel(writer, sheet_name="Business Profile", index=False)
        # About
        if about_data:
            pd.DataFrame([about_data]).to_excel(writer, sheet_name="About", index=False)
        # US News
        if usnews_data:
            pd.DataFrame([usnews_data]).to_excel(writer, sheet_name="USNews", index=False)
        # Yelp
        if yelp_reviews:
            pd.DataFrame({"reviews": yelp_reviews}).to_excel(writer, sheet_name="Yelp", index=False)
        # HCAHPS
        if hcahps_df is not None and not hcahps_df.empty:
            hcahps_df.to_excel(writer, sheet_name="HCAHPS", index=False)
        writer.close()
    return output.getvalue()