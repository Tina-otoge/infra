import json
import sys
from datetime import datetime, timedelta

import requests

DAYS_AHEAD = 30

with open(".storage/core.config_entries") as f:
    entries = json.load(f)

sonarr_entry = None
for entry in entries["data"]["entries"]:
    if entry["domain"] == "sonarr":
        sonarr_entry = entry
        break
else:
    raise Exception(
        "No Sonarr integration found in Home Assistant config entries."
    )

base_url = sonarr_entry["data"]["url"].rstrip("/")
api_key = sonarr_entry["data"]["api_key"]

start = datetime.now().strftime("%Y-%m-%d")
end = (datetime.now() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")

response = requests.get(
    f"{base_url}/api/v3/calendar",
    headers={"X-Api-Key": api_key},
    params={
        "start": start,
        "end": end,
        "unmonitored": "false",
        "includeSeries": "true",
    },
    timeout=10,
)
response.raise_for_status()
episodes = response.json()

by_date = {}
for ep in episodes:
    date = ep.get("airDate", "")
    series = ep.get("series", {})
    entry = {
        "series": series.get("title", ""),
        "episode": f"S{ep.get('seasonNumber', 0):02d}E{ep.get('episodeNumber', 0):02d}",
        "title": ep.get("title", ""),
        "network": series.get("network", ""),
        "has_file": ep.get("hasFile", False),
        "finale_type": ep.get("finaleType"),
    }
    by_date.setdefault(date, []).append(entry)

json.dump(
    {
        "count": len(episodes),
        "by_date": by_date,
        "days": sorted(by_date.keys()),
    },
    sys.stdout,
)
