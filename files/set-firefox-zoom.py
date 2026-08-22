#!/usr/bin/env python3

# AI use disclosure, mostly generated

import argparse
import sqlite3
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--url", required=True)
parser.add_argument("--zoom", required=True, type=float)
args = parser.parse_args()

host = args.url.split("://")[1].split("/")[0].split(":")[0]

# Read-only check — avoid touching anything if already correct
try:
    con_ro = sqlite3.connect(
        "file:" + args.db + "?mode=ro", uri=True, timeout=5
    )
    cur = con_ro.cursor()
    cur.execute(
        """SELECT p.value FROM prefs p
                   JOIN groups g ON p.groupID = g.id
                   JOIN settings s ON p.settingID = s.id
                   WHERE g.name = ? AND s.name = ?""",
        (host, "browser.content.full-zoom"),
    )
    row = cur.fetchone()
    con_ro.close()
    if row and abs(float(row[0]) - args.zoom) < 1e-9:
        print("ok")
        sys.exit(0)
except sqlite3.OperationalError as e:
    if "unable to open" not in str(e):
        raise  # locked or other error — do not proceed
    # DB does not exist yet, fall through to write path

# Kill browser-kiosk loop first so firefox won't be restarted
subprocess.run(
    ["pkill", "-u", "kiosk", "-f", "browser-kiosk"], capture_output=True
)
# Kill firefox to release the DB lock
subprocess.run(["pkill", "-u", "kiosk", "firefox-esr"], capture_output=True)
time.sleep(3)

con = sqlite3.connect(args.db)
con.execute("PRAGMA journal_mode=WAL")
cur = con.cursor()
cur.executescript(
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
"""
)
cur.execute(
    "SELECT id FROM settings WHERE name = ?", ("browser.content.full-zoom",)
)
row = cur.fetchone()
setting_id = (
    row[0]
    if row
    else cur.execute(
        "INSERT INTO settings (name) VALUES (?)", ("browser.content.full-zoom",)
    ).lastrowid
)
cur.execute("SELECT id FROM groups WHERE name = ?", (host,))
row = cur.fetchone()
group_id = (
    row[0]
    if row
    else cur.execute("INSERT INTO groups (name) VALUES (?)", (host,)).lastrowid
)
cur.execute(
    "SELECT id, value FROM prefs WHERE groupID = ? AND settingID = ?",
    (group_id, setting_id),
)
row = cur.fetchone()
if row:
    cur.execute(
        "UPDATE prefs SET value = ?, timestamp = ? WHERE id = ?",
        (args.zoom, time.time(), row[0]),
    )
else:
    cur.execute(
        "INSERT INTO prefs (groupID, settingID, value, timestamp) VALUES (?, ?, ?, ?)",
        (group_id, setting_id, args.zoom, time.time()),
    )
con.commit()
con.close()
print("changed")

# Restart sway — autologin respawns the full session including browser-kiosk
subprocess.run(["pkill", "-u", "kiosk", "sway"], capture_output=True)
