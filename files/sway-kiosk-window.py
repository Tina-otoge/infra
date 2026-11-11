#!/usr/bin/env python3

import json
import subprocess


def keep_keyboard_accessible(node: dict) -> None:
    if (node.get("app_id") or "").startswith("firefox") and node.get("fullscreen_mode"):
        subprocess.run(
            ["swaymsg", f"[con_id={node['id']}] fullscreen disable"], check=True
        )
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        keep_keyboard_accessible(child)


def main() -> None:
    with subprocess.Popen(
        ["swaymsg", "-m", "-r", "-t", "subscribe", '["window", "tick"]'],
        stdout=subprocess.PIPE,
        text=True,
    ) as events:
        assert events.stdout is not None
        for line in events.stdout:
            event = json.loads(line)
            # The initial tick confirms subscription before we scan existing windows.
            if event.get("first"):
                keep_keyboard_accessible(
                    json.loads(
                        subprocess.check_output(["swaymsg", "-r", "-t", "get_tree"])
                    )
                )
            elif event.get("change") in ("new", "fullscreen_mode"):
                keep_keyboard_accessible(event["container"])
        if events.wait() != 0:
            raise subprocess.CalledProcessError(events.returncode, events.args)


if __name__ == "__main__":
    main()
