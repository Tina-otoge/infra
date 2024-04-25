import os
from dataclasses import dataclass
from pathlib import Path

import requests
import yaml

CONFIG_FILE = Path(os.environ.get("CONFIG_FILE", "/etc/healthcheck.yml"))


with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

KUMA_URL = config.get("kuma_url")


@dataclass
class Item:
    name: str
    kuma: str
    user: str = None

    @property
    def status(self):
        if self.user:
            extra_args = f"--machine {self.user}@.host --user"
        else:
            extra_args = ""
        cmd = (
            f"systemctl is-active {extra_args} --quiet {self.name} 2>/dev/null"
        )
        return os.system(cmd) == 0

    def report(self):
        requests.get(
            f"{KUMA_URL}/api/push/{self.kuma}",
            params={
                "status": ["down", "up"][self.status],
            },
        )


for item in config.get("items", []):
    item = Item(**item)
    print(item, item.status)
    item.report()
