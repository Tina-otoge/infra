import contextlib
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "firefox_zoom", Path(__file__).parents[1] / "set-firefox-zoom.py"
)
firefox_zoom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(firefox_zoom)


class FirefoxZoomTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db = Path(self.directory.name) / "content-prefs.sqlite"
        self.url = "http://asashio.lan:8123/kitchen-dashboard/0"

    def query(self, sql):
        with contextlib.closing(sqlite3.connect(self.db)) as con, con:
            return con.execute(sql).fetchall()

    def test_first_launch_creates_versioned_database(self):
        self.assertTrue(firefox_zoom.set_zoom(self.db, self.url, 0.9))
        self.assertEqual(self.query("PRAGMA user_version"), [(6,)])
        self.assertEqual(self.query("SELECT name FROM groups"), [("asashio.lan",)])
        self.assertEqual(self.query("SELECT value FROM prefs"), [(0.9,)])

    def test_unchanged_zoom_does_not_write(self):
        firefox_zoom.set_zoom(self.db, self.url, 0.9)
        before = self.db.read_bytes()
        self.assertFalse(firefox_zoom.set_zoom(self.db, self.url, 0.9))
        self.assertEqual(self.db.read_bytes(), before)

    def test_updates_zoom_without_duplicates(self):
        firefox_zoom.set_zoom(self.db, self.url, 0.3)
        self.assertTrue(firefox_zoom.set_zoom(self.db, self.url, 0.9))
        self.assertEqual(self.query("SELECT value FROM prefs"), [(0.9,)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM settings"), [(1,)])

    def test_other_sites_are_preserved(self):
        firefox_zoom.set_zoom(self.db, "https://example.com", 1.2)
        firefox_zoom.set_zoom(self.db, self.url, 0.9)
        self.assertEqual(
            self.query("SELECT value FROM prefs ORDER BY id"), [(1.2,), (0.9,)]
        )

    def test_repairs_unversioned_database(self):
        firefox_zoom.set_zoom(self.db, self.url, 0.9)
        self.query("PRAGMA user_version = 0")
        self.assertTrue(firefox_zoom.set_zoom(self.db, self.url, 0.9))
        self.assertEqual(self.query("PRAGMA user_version"), [(6,)])

    def test_unknown_schema_is_not_modified(self):
        self.query("PRAGMA user_version = 99")
        before = self.db.read_bytes()
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            firefox_zoom.set_zoom(self.db, self.url, 0.9)
        self.assertEqual(self.db.read_bytes(), before)

    def test_invalid_inputs_do_not_create_database(self):
        for zoom in (0, -1, float("nan"), float("inf")):
            with self.subTest(zoom=zoom), self.assertRaises(ValueError):
                firefox_zoom.set_zoom(self.db, self.url, zoom)
        with self.assertRaises(ValueError):
            firefox_zoom.set_zoom(self.db, "not-a-url", 0.9)
        self.assertFalse(self.db.exists())

    def test_database_lock_is_reported(self):
        firefox_zoom.set_zoom(self.db, self.url, 0.9)
        with contextlib.closing(sqlite3.connect(self.db)) as con:
            con.execute("BEGIN EXCLUSIVE")
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                firefox_zoom.set_zoom(self.db, self.url, 0.3)
        self.assertEqual(self.query("SELECT value FROM prefs"), [(0.9,)])


if __name__ == "__main__":
    unittest.main()
