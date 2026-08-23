import json
from datetime import datetime, timezone

import requests

SHOPPING_LIST_CHANNEL_ID = 1301508306275274805

with open(".storage/core.config_entries") as f:
    entries = json.load(f)

for entry in entries["data"]["entries"]:
    if entry["domain"] == "discord":
        token = entry["data"]["api_token"]
        break
else:
    raise Exception("No Discord token found in Home Assistant config entries.")

response = requests.get(
    f"https://discord.com/api/v10/channels/{SHOPPING_LIST_CHANNEL_ID}/messages",
    headers={"Authorization": f"Bot {token}"},
)
DONE_REACTIONS = {"✅", "❌"}


def is_done(msg):
    return any(
        r["emoji"]["name"] in DONE_REACTIONS for r in msg.get("reactions", [])
    )


response.raise_for_status()
messages = response.json()
items = []
for msg in messages:
    if not is_done(msg) and (msg.get("content") or msg.get("attachments")):
        images = [
            a["url"]
            for a in msg.get("attachments", [])
            if a.get("content_type", "").startswith("image/")
        ]
        sent = datetime.fromisoformat(msg["timestamp"])
        days = (datetime.now(timezone.utc) - sent).days
        if days == 0:
            age = "today"
        elif days == 1:
            age = "yesterday"
        elif days <= 14:
            age = f"{days} days ago"
        else:
            age = sent.strftime("%Y-%m-%d")
        items.append(
            {"text": msg.get("content", ""), "images": images, "age": age}
        )
print(json.dumps({"items": items, "count": len(items)}))
