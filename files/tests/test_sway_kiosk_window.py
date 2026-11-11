import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest import mock


spec = importlib.util.spec_from_file_location(
    "sway_kiosk_window", Path(__file__).parents[1] / "sway-kiosk-window.py"
)
sway_kiosk_window = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sway_kiosk_window)


class KioskWindowTests(unittest.TestCase):
    @mock.patch.object(sway_kiosk_window.subprocess, "Popen")
    @mock.patch.object(sway_kiosk_window.subprocess, "check_output")
    @mock.patch.object(sway_kiosk_window.subprocess, "run")
    def test_scans_on_initial_tick_and_handles_late_fullscreen(self, run, output, popen):
        output.return_value = b'{"nodes": []}'
        events = popen.return_value.__enter__.return_value
        events.stdout = io.StringIO(
            json.dumps({"first": True, "payload": ""}) + "\n"
            + json.dumps({
                "change": "fullscreen_mode",
                "container": {"id": 5, "app_id": "firefox-esr", "fullscreen_mode": 1},
            }) + "\n"
        )
        events.wait.return_value = 0
        sway_kiosk_window.main()
        output.assert_called_once_with(["swaymsg", "-r", "-t", "get_tree"])
        run.assert_called_once_with(
            ["swaymsg", "[con_id=5] fullscreen disable"], check=True
        )

    @mock.patch.object(sway_kiosk_window.subprocess, "run")
    def test_disables_firefox_fullscreen(self, run):
        sway_kiosk_window.keep_keyboard_accessible(
            {"id": 5, "app_id": "firefox-esr", "fullscreen_mode": 1}
        )
        run.assert_called_once_with(
            ["swaymsg", "[con_id=5] fullscreen disable"], check=True
        )

    @mock.patch.object(sway_kiosk_window.subprocess, "run")
    def test_ignores_other_apps_and_already_windowed_firefox(self, run):
        for app_id, mode in ((None, 1), ("other", 1), ("firefox-esr", 0)):
            sway_kiosk_window.keep_keyboard_accessible(
                {"id": 5, "app_id": app_id, "fullscreen_mode": mode}
            )
        run.assert_not_called()

    @mock.patch.object(sway_kiosk_window.subprocess, "run")
    def test_initial_scan_includes_nested_and_floating_windows(self, run):
        sway_kiosk_window.keep_keyboard_accessible(
            {"nodes": [{"floating_nodes": [
                {"id": 6, "app_id": "firefox-esr", "fullscreen_mode": 1}
            ]}]}
        )
        run.assert_called_once_with(
            ["swaymsg", "[con_id=6] fullscreen disable"], check=True
        )


if __name__ == "__main__":
    unittest.main()
