import os
import requests

# 🔑 Replace with your Yelp API key or set as environment variable
yelp_api_key = os.getenv("YELP_API_KEY") or "YOURAPIKEY"

headers = {"Authorization": f"Bearer {yelp_api_key}"}

# Simple search to test the key
params = {
    "term": "UCSF Medical Center",  # Example org
    "location": "San Francisco, CA",
    "limit": 1
}

resp = requests.get("https://api.yelp.com/v3/businesses/search", headers=headers, params=params)

if resp.status_code == 200:
    data = resp.json()
    businesses = data.get("businesses", [])
    if businesses:
        b = businesses[0]
        print("✅ Yelp API key works! Sample result:")
        print(f"Name: {b['name']}")
        print(f"City: {b['location']['city']}")
        print(f"Address: {b['location'].get('address1')}")
        print(f"Rating: {b['rating']}")
        print(f"URL: {b['url']}")
    else:
        print("✅ Yelp API key works, but no businesses found for that query.")
else:
    print(f"❌ Yelp API key failed! Status code: {resp.status_code}")
    print(resp.text)
