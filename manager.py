#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["requests"]
# ///
"""Mihomo (Clash Meta) manager."""

import base64
import json
import subprocess
import sys
from pathlib import Path

import requests

CONFIG_PATH = Path(__file__).resolve().parent / "subscriptions.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"[!] config not found: {CONFIG_PATH}")
        print("    copy subscriptions.json.example to subscriptions.json and fill in your data")
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def decode_base64(data: str) -> str:
    data += "=" * (-len(data) % 4)
    return base64.b64decode(data).decode("utf-8")


def systemd(action: str) -> None:
    try:
        subprocess.run(["systemctl", "--user", action, "mihomo"], check=True)
    except subprocess.CalledProcessError:
        print(f"[!] failed to {action} mihomo")


def update() -> None:
    cfg = load_config()
    headers = cfg.get("headers", {})
    for sub in cfg.get("subscriptions", []):
        print(f"updating {sub['name']}...")
        try:
            response = requests.get(sub["url"], headers=headers, timeout=15)
            response.raise_for_status()
            content = response.text.strip()
            if sub.get("decode"):
                content = decode_base64(content)
            path = Path(sub["path"]).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"saved to {path}")
        except Exception as e:
            print(f"[!] {sub['name']}: {e}")


COMMANDS = {
    "--start": lambda: systemd("start"),
    "--stop": lambda: systemd("stop"),
    "--restart": lambda: systemd("restart"),
    "--status": lambda: systemd("status"),
    "--update": update,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: vpn [ {' | '.join(COMMANDS)} ]")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
