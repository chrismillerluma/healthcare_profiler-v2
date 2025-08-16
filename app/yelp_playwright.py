from playwright.sync_api import sync_playwright
import logging
import time

logging.basicConfig(level=logging.INFO)

def fetch_yelp_reviews_scroll(url: str, limit: int = 20) -> list[dict]:
    """
    Scrape Yelp reviews from a business page using Playwright with scrolling.
    Returns list of dicts: {"user", "rating", "text"}.
    """
    reviews = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            
            # Scroll down to load more reviews
            previous_height = None
            while len(reviews) < limit:
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                time.sleep(2)  # wait for new reviews to load
                current_height = page.evaluate("document.body.scrollHeight")
                if current_height == previous_height:
                    break  # no more content
                previous_height = current_height

                review_divs = page.query_selector_all("div.review__09f24__oHr9V")
                for div in review_divs[len(reviews):]:  # only new reviews
                    text_tag = div.query_selector("span.raw__09f24__T4Ezm")
                    text = text_tag.inner_text().strip() if text_tag else ""

                    user_tag = div.query_selector("span.fs-block.css-m6anxm")
                    user = user_tag.inner_text().strip() if user_tag else "Anonymous"

                    rating_tag = div.query_selector("div.i-stars__09f24__foihJ")
                    rating = None
                    if rating_tag:
                        aria_label = rating_tag.get_attribute("aria-label")
                        if aria_label:
                            try:
                                rating = float(aria_label.split(" ")[0])
                            except:
                                pass

                    reviews.append({"user": user, "rating": rating, "text": text})
                    if len(reviews) >= limit:
                        break

            browser.close()

        return reviews[:limit]

    except Exception as e:
        logging.warning(f"[Playwright Yelp Scroll Error] {e}")
        return []

# Example usage
if __name__ == "__main__":
    url = "https://www.yelp.com/biz/nyu-langone-medical-center-new-york-3#reviews"
    result = fetch_yelp_reviews_scroll(url, limit=15)
    for r in result:
        print(r)
