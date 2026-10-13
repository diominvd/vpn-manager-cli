#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["requests"]
# ///
"""Mihomo (Clash Meta) manager.

Single source of truth: subscriptions.json.

  vpn --update   download every subscription into providers/*.yaml, then
                 regenerate config.yaml from config.template.yaml
  vpn --render   regenerate config.yaml only (no network)
  vpn --start / --stop / --restart / --status   control mihomo.service

config.yaml is never edited by hand — it is a rendered artefact. To add or
change a provider, edit subscriptions.json and run `vpn --update`.
"""

import base64
import json
import subprocess
import sys
from pathlib import Path

import requests

MIHOMO_DIR = Path.home() / ".config" / "mihomo"
CONFIG_PATH = MIHOMO_DIR / "subscriptions.json"
TEMPLATE_PATH = MIHOMO_DIR / "config.template.yaml"
RENDERED_PATH = MIHOMO_DIR / "config.yaml"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"[!] config not found: {CONFIG_PATH}")
        print("    create it with a subscriptions.json file")
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


def render() -> None:
    """Regenerate config.yaml from the template and subscriptions.json."""
    if not TEMPLATE_PATH.exists():
        print(f"[!] template not found: {TEMPLATE_PATH}")
        sys.exit(1)

    cfg = load_config()
    subs = cfg.get("subscriptions", [])

    providers_lines = []
    names_lines = []
    for sub in subs:
        name = sub["name"]
        path = Path(sub["path"]).expanduser()
        providers_lines.append(
            f"  {name}:\n"
            f"    type: file\n"
            f"    path: {path}\n"
            f"    health-check:\n"
            f"      enable: true\n"
            f"      interval: 600\n"
            f"      url: http://www.gstatic.com/generate_204"
        )
        names_lines.append(f"      - {name}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = (
        template
        .replace("{{PROVIDERS}}", "\n".join(providers_lines))
        .replace("{{PROVIDER_NAMES}}", "\n".join(names_lines))
    )

    RENDERED_PATH.write_text(rendered, encoding="utf-8")
    print(f"rendered {RENDERED_PATH} ({len(subs)} provider(s))")


def update() -> None:
    """Download every subscription, then render config.yaml."""
    cfg = load_config()
    headers = cfg.get("headers", {})
    failed = False

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
            failed = True
            print(f"[!] {sub['name']}: {e}")

    render()

    if failed:
        sys.exit(1)


COMMANDS = {
    "--start": lambda: systemd("start"),
    "--stop": lambda: systemd("stop"),
    "--restart": lambda: systemd("restart"),
    "--status": lambda: systemd("status"),
    "--update": update,
    "--render": render,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: vpn [ {' | '.join(COMMANDS)} ]")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
