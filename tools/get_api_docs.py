"""Download the CollegeFootballData API spec (public, no key) to tools/cfbd_api_docs.json."""
import os, urllib.request
here = os.path.dirname(os.path.abspath(__file__))
url = "https://api.collegefootballdata.com/api-docs.json"
with urllib.request.urlopen(url, timeout=60) as r:
    data = r.read()
open(os.path.join(here, "cfbd_api_docs.json"), "wb").write(data)
print(f"Saved {len(data):,} bytes")
