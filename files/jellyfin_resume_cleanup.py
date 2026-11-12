#!/usr/bin/env python3
"""Reset stale Jellyfin resume positions without changing other user data."""

import argparse
import datetime as dt
import json
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


CONTAINER_DB = "/config/data/jellyfin.db"
TOKEN_QUERY = """
import json, sqlite3, sys
conn = sqlite3.connect('file:/config/data/jellyfin.db?mode=ro', uri=True)
try:
    for (auth,) in conn.execute('SELECT AuthenticationInfo FROM Users'):
        if not auth:
            continue
        try:
            value = json.loads(auth)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get('AccessToken'):
            print(value['AccessToken'])
finally:
    conn.close()
"""


def tokens_from_container(container):
    try:
        result = subprocess.run(
            ["podman", "exec", container, "python3", "-c", TOKEN_QUERY],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return [line for line in result.stdout.splitlines() if line]
    except (OSError, subprocess.SubprocessError):
        return []


def tokens_from_host():
    db_path = Path.home() / ".config/jellyfin/data/jellyfin.db"
    uri = "file:" + urllib.parse.quote(str(db_path), safe="/") + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        try:
            rows = connection.execute("SELECT AuthenticationInfo FROM Users")
            values = []
            for (auth,) in rows:
                if not auth:
                    continue
                try:
                    data = json.loads(auth)
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(data, dict) and data.get("AccessToken"):
                    values.append(data["AccessToken"])
            return values
        finally:
            connection.close()
    except (OSError, sqlite3.Error, ValueError):
        return []


def request_json(base_url, path, token, method="GET", body=None):
    url = base_url.rstrip("/") + path
    headers = {"Accept": "application/json", "X-Emby-Token": token}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()
        return json.loads(content) if content else None


def get_valid_token(base_url, candidates):
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            users = request_json(base_url, "/Users", candidate)
            if isinstance(users, list):
                return candidate, users
        except (OSError, ValueError, urllib.error.URLError):
            continue
    return None, None


def parse_date(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except ValueError:
        return None


def iter_user_items(base_url, token, user_id):
    start = 0
    limit = 500
    while True:
        query = urllib.parse.urlencode(
            {
                "Recursive": "true",
                "Fields": "UserData",
                "StartIndex": start,
                "Limit": limit,
            }
        )
        page = request_json(
            base_url, f"/Users/{urllib.parse.quote(str(user_id), safe='')}/Items?{query}", token
        )
        if not isinstance(page, dict) or not isinstance(page.get("Items"), list):
            raise ValueError("unexpected Jellyfin items response")
        items = page["Items"]
        yield from items
        total = page.get("TotalRecordCount", start + len(items))
        if not items or start + len(items) >= total:
            break
        start += len(items)


def cleanup(base_url, token, users, cutoff, dry_run):
    examined = 0
    changed = 0
    for user in users:
        user_id = user.get("Id")
        if not user_id:
            continue
        for item in iter_user_items(base_url, token, user_id):
            user_data = item.get("UserData")
            if not isinstance(user_data, dict):
                continue
            position = user_data.get("PlaybackPositionTicks", 0)
            try:
                if float(position) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            last_played = parse_date(user_data.get("LastPlayedDate"))
            if last_played is None or last_played >= cutoff:
                continue
            examined += 1
            name = item.get("Name") or item.get("Id") or "(unnamed item)"
            if dry_run:
                print(f"Would reset stale resume position: {name}")
                continue
            payload = dict(user_data)
            payload["PlaybackPositionTicks"] = 0
            item_id = urllib.parse.quote(str(item.get("Id", "")), safe="")
            request_json(
                base_url,
                f"/Users/{urllib.parse.quote(str(user_id), safe='')}/Items/{item_id}/UserData",
                token,
                method="POST",
                body=payload,
            )
            changed += 1
            print(f"Reset stale resume position: {name}")
    return examined, changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.days < 0:
        parser.error("--days must not be negative")

    try:
        result = subprocess.run(
            ["podman", "ps", "--format", "{{.Names}}", "--filter", "name=jellyfin"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        print("Unable to discover the Jellyfin container; no changes made.", file=sys.stderr)
        return 1

    containers = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(containers) != 1:
        print("Expected exactly one running Jellyfin container; no changes made.", file=sys.stderr)
        return 1

    candidates = tokens_from_container(containers[0])
    token, users = get_valid_token(args.base_url, candidates)
    if token is None:
        token, users = get_valid_token(args.base_url, tokens_from_host())
    if token is None:
        print("Unable to retrieve and validate a Jellyfin access token; no changes made.", file=sys.stderr)
        return 1

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    try:
        examined, changed = cleanup(args.base_url, token, users, cutoff, args.dry_run)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        # Do not expose request details or credentials in service logs.
        print(f"Jellyfin cleanup stopped after an API error ({type(exc).__name__}).", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"Dry run: {examined} stale resume position(s) would be reset.")
    else:
        print(f"Reset {changed} stale resume position(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
