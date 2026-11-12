#!/usr/bin/env python3
"""Clear stale Jellyfin episode resume positions through the HTTP API."""

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


class ApiError(Exception):
    """An HTTP or response error from Jellyfin."""


class AuthenticationError(ApiError):
    """Jellyfin rejected the API key."""


class JellyfinApi:
    def __init__(self, base_url, api_key, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def request(self, method, path, query=None, data=None):
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        body = None
        headers = {
            "Accept": "application/json",
            "X-Emby-Token": self.api_key,
        }
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url, data=body, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise AuthenticationError(
                    "Jellyfin rejected the API key (HTTP {}).".format(error.code)
                ) from error
            raise ApiError(
                "Jellyfin returned HTTP {} for {} {}.".format(
                    error.code, method, path
                )
            ) from error
        except urllib.error.URLError as error:
            raise ApiError("Jellyfin request failed: {}".format(error.reason)) from error

        if not payload:
            return None
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApiError("Jellyfin returned invalid JSON for {}.".format(path)) from error


def parse_date(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def positive_days(value):
    days = int(value)
    if days < 1:
        raise argparse.ArgumentTypeError("days must be at least 1")
    return days


def print_summary(stats):
    print(
        "Jellyfin resume cleanup: users_scanned={users_scanned} "
        "disabled_users={disabled_users} episodes_scanned={episodes_scanned} "
        "candidates={candidates} reset_count={reset_count} errors={errors}".format(
            **stats
        )
    )


def fetch_episodes(api, user_id, page_size):
    start = 0
    while True:
        result = api.request(
            "GET",
            "/Users/{}/Items".format(urllib.parse.quote(user_id, safe="")),
            query={
                "IncludeItemTypes": "Episode",
                "Recursive": "true",
                "Filters": "IsResumable",
                "EnableUserData": "true",
                "Fields": "UserData",
                "StartIndex": start,
                "Limit": page_size,
            },
        )
        if not isinstance(result, dict) or not isinstance(
            result.get("Items"), list
        ):
            raise ApiError("Jellyfin returned an invalid episode page.")
        items = result["Items"]
        for item in items:
            yield item
        start += len(items)
        total = result.get("TotalRecordCount")
        if not items or len(items) < page_size:
            break
        if total is not None and start >= int(total):
            break


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--days", type=positive_days, required=True)
    parser.add_argument("--api-key-file", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stats = {
        "users_scanned": 0,
        "disabled_users": 0,
        "episodes_scanned": 0,
        "candidates": 0,
        "reset_count": 0,
        "errors": 0,
    }
    try:
        with open(args.api_key_file, encoding="utf-8") as key_file:
            api_key = key_file.read().strip()
    except OSError as error:
        print("ERROR: cannot read Jellyfin API key file: {}".format(error),
              file=sys.stderr)
        stats["errors"] += 1
        print_summary(stats)
        return 1
    if not api_key:
        print("ERROR: Jellyfin API key is empty.", file=sys.stderr)
        stats["errors"] += 1
        print_summary(stats)
        return 1

    parsed_url = urllib.parse.urlsplit(args.base_url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        print("ERROR: invalid Jellyfin base URL.", file=sys.stderr)
        stats["errors"] += 1
        print_summary(stats)
        return 1

    api = JellyfinApi(args.base_url, api_key)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    candidates = []

    # Complete all authenticated reads before the first update.
    try:
        users = api.request("GET", "/Users")
        if not isinstance(users, list):
            raise ApiError("Jellyfin returned an invalid users list.")
        for user in users:
            if not isinstance(user, dict) or not user.get("Id"):
                raise ApiError("Jellyfin returned a user without an ID.")
            if user.get("IsDisabled") is True:
                stats["disabled_users"] += 1
                continue
            stats["users_scanned"] += 1
            user_id = str(user["Id"])
            for item in fetch_episodes(api, user_id, 200):
                stats["episodes_scanned"] += 1
                if not isinstance(item, dict) or not item.get("Id"):
                    raise ApiError("Jellyfin returned an episode without an ID.")
                user_data = item.get("UserData")
                if not isinstance(user_data, dict):
                    raise ApiError("Jellyfin episode is missing its UserData DTO.")
                position = user_data.get("PlaybackPositionTicks", 0)
                try:
                    position = int(position)
                except (TypeError, ValueError):
                    stats["errors"] += 1
                    print("ERROR: invalid resume position for item {}.".format(
                        item["Id"]
                    ), file=sys.stderr)
                    continue
                if position == 0:
                    continue
                last_played = user_data.get("LastPlayedDate")
                if last_played is None:
                    continue
                try:
                    played_at = parse_date(last_played)
                except (TypeError, ValueError):
                    stats["errors"] += 1
                    print("ERROR: invalid LastPlayedDate for item {}.".format(
                        item["Id"]
                    ), file=sys.stderr)
                    continue
                if played_at < cutoff:
                    updated_data = dict(user_data)
                    updated_data["PlaybackPositionTicks"] = 0
                    candidates.append((user_id, str(item["Id"]), updated_data))
    except ApiError as error:
        stats["errors"] += 1
        print("ERROR: {}".format(error), file=sys.stderr)
        print_summary(stats)
        return 1

    stats["candidates"] = len(candidates)
    if not args.dry_run:
        for user_id, item_id, user_data in candidates:
            path = "/Users/{}/Items/{}/UserData".format(
                urllib.parse.quote(user_id, safe=""),
                urllib.parse.quote(item_id, safe=""),
            )
            try:
                api.request("POST", path, data=user_data)
                stats["reset_count"] += 1
            except AuthenticationError as error:
                stats["errors"] += 1
                print("ERROR: {}".format(error), file=sys.stderr)
                break
            except ApiError as error:
                stats["errors"] += 1
                print("ERROR: {}".format(error), file=sys.stderr)

    print_summary(stats)
    return 1 if stats["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
