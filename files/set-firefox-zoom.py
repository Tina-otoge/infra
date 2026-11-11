#!/usr/bin/env python3

import argparse
import contextlib
import math
import sqlite3
import time
from pathlib import Path
from urllib import parse


def set_zoom(db: Path, url: str, zoom: float) -> bool:
    """Set site zoom while Firefox is stopped, as the profile's owner."""
    host = parse.urlsplit(url).hostname
    if not host:
        raise ValueError("The kiosk URL must include a hostname")
    if not math.isfinite(zoom) or zoom <= 0:
        raise ValueError("Zoom must be a finite positive number")

    with contextlib.closing(sqlite3.connect(db, timeout=5)) as con, con:
        version = con.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 6):
            raise ValueError(f"Unsupported Firefox content preferences schema: {version}")
        if version == 0:
            # Firefox discards an unversioned database instead of using its prefs.
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS prefs (
                    id INTEGER PRIMARY KEY,
                    groupID INTEGER REFERENCES groups(id),
                    settingID INTEGER NOT NULL REFERENCES settings(id),
                    value BLOB,
                    timestamp INTEGER NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS groups_idx ON groups(name);
                CREATE INDEX IF NOT EXISTS settings_idx ON settings(name);
                CREATE INDEX IF NOT EXISTS prefs_idx ON prefs(timestamp, groupID, settingID);
                PRAGMA user_version = 6;
                """
            )

        row = con.execute(
            """SELECT p.id, p.value FROM prefs p
               JOIN groups g ON p.groupID = g.id
               JOIN settings s ON p.settingID = s.id
               WHERE g.name = ? AND s.name = ?""",
            (host, "browser.content.full-zoom"),
        ).fetchone()
        if row:
            if abs(float(row[1]) - zoom) < 1e-9:
                return version == 0
            con.execute(
                "UPDATE prefs SET value = ?, timestamp = ? WHERE id = ?",
                (zoom, time.time(), row[0]),
            )
        else:
            con.execute(
                """INSERT INTO settings (name)
                   SELECT ? WHERE NOT EXISTS (SELECT 1 FROM settings WHERE name = ?)""",
                ("browser.content.full-zoom", "browser.content.full-zoom"),
            )
            con.execute(
                """INSERT INTO groups (name)
                   SELECT ? WHERE NOT EXISTS (SELECT 1 FROM groups WHERE name = ?)""",
                (host, host),
            )
            con.execute(
                """INSERT INTO prefs (groupID, settingID, value, timestamp)
                   VALUES ((SELECT id FROM groups WHERE name = ?),
                           (SELECT id FROM settings WHERE name = ?), ?, ?)""",
                (host, "browser.content.full-zoom", zoom, time.time()),
            )
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--url", required=True)
    parser.add_argument("--zoom", required=True, type=float)
    args = parser.parse_args()
    print("changed" if set_zoom(args.db, args.url, args.zoom) else "ok")


if __name__ == "__main__":
    main()
