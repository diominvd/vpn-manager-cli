# vpn-manager-cli

Minimalist CLI manager for [mihomo](https://wiki.metacubex.one) (Clash Meta) proxy with transparent TUN mode and subscription auto-update.

## Table of Contents
* [Features](#features)
* [Requirements](#requirements)
* [Installation & Setup](#installation--setup)
* [Quick Start](#quick-start)
* [Usage](#usage)
* [Configuration](#configuration)
* [Architecture](#architecture)
* [Troubleshooting](#troubleshooting)
* [Acknowledgments](#acknowledgments)
* [Disclaimer](#disclaimer)
* [License](#license)

## Features
* Transparent proxy via TUN mode — all system traffic routes through mihomo automatically.
* Subscription management: fetch and update proxy provider configs from remote sources.
* Single source of truth — `subscriptions.json` drives both the downloads and the runtime config; `config.yaml` is a rendered artefact, never edited by hand.
* Systemd user service control (start / stop / restart / status).
* Fake-ip DNS for fast domain resolution without leaks.
* Mixed-port (HTTP + SOCKS5) for manual proxy usage at `127.0.0.1:7890`.
* TUI dashboard via [mihomo-tui](https://github.com/MetaCubeX/mihomo-tui) for real-time traffic monitoring and proxy switching.
* Drop-in integration with the Quickshell bar widget (`mihomo.sh` calls `vpn --update` and reloads mihomo).

## Requirements
* Linux with `systemd` (the daemon commands use `systemctl --user`)
* `uv` (Fast Python package and project manager)
* `mihomo` installed and available on `$PATH`
* Root capabilities for TUN and DNS (port 53):

```bash
sudo setcap cap_net_admin,cap_net_bind_service=ep /usr/bin/mihomo
```

Python dependency (`requests`) is declared inline in `manager.py`
and resolved automatically by `uv` on first run — no manual install required.

## Installation & Setup

### 1. Install uv

Ensure `uv` is installed on your system (e.g., `yay -S uv` on Arch Linux).

### 2. Install mihomo

```bash
# Arch Linux
yay -S mihomo

# or download from https://github.com/MetaCubeX/mihomo/releases
```

### 3. Grant capabilities

TUN mode and DNS binding (port 53) require elevated privileges. Instead of
running as root, grant the binary the needed capabilities:

```bash
sudo setcap cap_net_admin,cap_net_bind_service=ep /usr/bin/mihomo
```

> This persists across reboots. If you reinstall mihomo, re-run this command.

### 4. Install the systemd service

The repo includes a user-level systemd unit file. Install it:

```bash
mkdir -p ~/.config/systemd/user
cp mihomo.service ~/.config/systemd/user/mihomo.service
systemctl --user daemon-reload
```

### 5. Set up the mihomo config

Copy the template files to `~/.config/mihomo/`:

```bash
mkdir -p ~/.config/mihomo/providers
cp config.template.yaml ~/.config/mihomo/config.template.yaml
```

`config.template.yaml` is the source of truth for the static parts of the
mihomo config (`tun`, `dns`, `rules`, `proxy-groups`, and everything else that
does not change per subscription). `config.yaml` is generated from it — do not
edit `config.yaml` directly.

### 6. Configure subscriptions

Copy the example subscriptions file and fill in your credentials:

```bash
cp subscriptions.json.example subscriptions.json
```

Edit `subscriptions.json` and replace `YOUR_TOKEN` and `YOUR_HARDWARE_ID` with
your subscription credentials.

### 7. Create the `vpn` command

Create a zsh function that wraps the script:

```bash
vpn() {
    uv run /path/to/vpn/manager.py --"$1"
}
```

## Quick Start

After setup, the typical first-run sequence is:

```bash
vpn --update   # fetch proxy configs, then render config.yaml
vpn --start    # start the mihomo user service (TUN + DNS + mixed-port)
```

Check that it works:

```bash
vpn --status   # verify the service is running without errors
curl -x http://127.0.0.1:7890 https://ifconfig.me  # test proxy
```

Open [mihomo-tui](https://github.com/MetaCubeX/mihomo-tui) in a separate terminal to monitor traffic and switch proxies in real time.

## Usage

```bash
vpn [ COMMAND ]
```

### Daemon
| Command | Description |
| --- | --- |
| `--start` | Start the mihomo user service. |
| `--stop` | Stop the mihomo user service. |
| `--restart` | Restart the mihomo user service. |
| `--status` | Show the mihomo service status. |

### Subscriptions
| Command | Description |
| --- | --- |
| `--update` | Fetch the latest proxy configs from all configured subscriptions, save them to the providers directory, and regenerate `config.yaml` from `config.template.yaml`. |
| `--render` | Regenerate `config.yaml` from `config.template.yaml` without touching the network. Useful after editing the template by hand. |

## Configuration

### Subscriptions config

Subscriptions are defined in `subscriptions.json` (git-ignored). See `subscriptions.json.example` for the format:

```json
{
    "headers": {
        "User-Agent": "ClashMeta/2.11.27",
        "x-hwid": "YOUR_HARDWARE_ID"
    },
    "subscriptions": [
        {
            "name": "provider-name",
            "url": "https://example.com/YOUR_TOKEN",
            "path": "~/.config/mihomo/providers/provider-name.yaml",
            "decode": false
        }
    ]
}
```

| Field | Description |
| --- | --- |
| `headers` | HTTP headers sent with subscription requests (User-Agent, hardware ID, etc.). |
| `subscriptions[].name` | Provider name. Also used as the key in `proxy-providers` and in the policy group's `use:` list in the rendered `config.yaml`. |
| `subscriptions[].url` | Subscription URL to fetch proxy configs from. |
| `subscriptions[].path` | Local path to save the downloaded config. Supports `~`. Must match the `path:` that `vpn --render` writes into `config.yaml` — the renderer uses this field, so you never type the path twice. |
| `subscriptions[].decode` | Set `true` if the response is base64-encoded. |

Run `vpn --update` after changing subscriptions. This fetches every URL with
the headers above, writes each provider file to its `path`, and then re-renders
`config.yaml` so mihomo picks up the new provider list on the next reload.

### Template config

`config.template.yaml` is the source of truth for the static parts of the
mihomo config. Two placeholders are filled in by `vpn --render`:

| Placeholder | Replaced with |
| --- | --- |
| `{{PROVIDERS}}` | One `type: file` block per entry in `subscriptions.json`, pointing at the yaml file the downloader writes. |
| `{{PROVIDER_NAMES}}` | The same names as a `use:` list under the policy group. |

Key sections:

| Section | Description |
| --- | --- |
| `mixed-port` | HTTP + SOCKS5 proxy port (default: `7890`). |
| `tun` | Transparent proxy settings — enable, stack, auto-route, DNS hijack. |
| `dns` | Fake-ip DNS with fallback resolvers. |
| `proxy-providers` | Filled in from `subscriptions.json` — one `type: file` block per subscription. mihomo never fetches: the downloader does. |
| `proxy-groups` | Filled in from `subscriptions.json` — the `use:` list under the policy group. |
| `rules` | Routing rules (default: `MATCH,Proxies` — send everything through proxy). |

### Generated config

`config.yaml` is a rendered artefact. It is rebuilt by `vpn --update` and
`vpn --render` from `config.template.yaml` plus `subscriptions.json`. Edits to
`config.yaml` are overwritten on the next render — if you want to change
something, edit the template.

### TUN mode

TUN captures all system traffic transparently. The binary needs capabilities:

```bash
sudo setcap cap_net_admin,cap_net_bind_service=ep /usr/bin/mihomo
```

If you prefer not to use TUN, disable it in `config.template.yaml` and use the
mixed-port as a regular HTTP/SOCKS5 proxy (`127.0.0.1:7890`).

## Architecture

Three roles, no overlap:

```
subscriptions.json  ──►  vpn --update  ──►  providers/*.yaml
        │                    │                    │
        │                    │                    ▼
        │                    ▼             mihomo (type: file)
        │             config.template.yaml         │
        │                    │                    │
        │                    ▼                    ▼
        └──────────►  config.yaml  ────────►  systemd --user
                           ▲
                           │
                    mihomo.sh --update
                           ▲
                           │
                    Quickshell widget
```

* **`subscriptions.json`** — single source of truth for providers. Every URL,
  header, and target path lives here. Adding or removing a provider is one
  edit in this file followed by `vpn --update`.
* **`config.template.yaml`** — single source of truth for statics. Everything
  that does not depend on a subscription (`tun`, `dns`, `rules`, ports, log
  level) lives here.
* **`config.yaml`** — never edited by hand. Rebuilt from the two sources above
  by `vpn --render`.
* **`providers/*.yaml`** — written by `vpn --update`. mihomo reads these
  directly (`type: file`), so it never talks to subscription URLs itself.

### Why this shape

Before, `config.yaml` had `type: http` providers with their own URLs and
headers, and `vpn --update` wrote the same files in parallel. Two downloaders,
two places to keep headers in sync, and a real chance of mihomo and the
downloader writing to the same file at the same time. Now there is exactly one
downloader and one file per provider.

### Integration with Quickshell

The `mihomo.sh` bridge (used by the Quickshell Wi-Fi / Mihomo widget) delegates
to this CLI:

* `mihomo.sh --update` → `vpn --update` → reload mihomo.
* `mihomo.sh --add-provider <name> <url>` → append to `subscriptions.json` →
  `vpn --update` → reload mihomo. It never touches `config.yaml`; the renderer
  does.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `--start` fails with `operation not permitted` | Run `sudo setcap cap_net_admin,cap_net_bind_service=ep /usr/bin/mihomo` and restart. |
| DNS error `bind: permission denied` | Same fix — capabilities are needed for port 53. Or change `dns.listen` to `0.0.0.0:5353` and disable TUN. |
| `--update` fails to fetch subscription | Check your `subscriptions.json` and network connection. Verify headers match your provider's requirements. |
| `config not found` | Copy `subscriptions.json.example` to `subscriptions.json` and fill in your credentials. |
| `template not found` | Copy `config.template.yaml` into `~/.config/mihomo/`. |
| No traffic going through proxy | Check `vpn --status` for errors. Verify the service is active and TUN started. Test with `curl -x http://127.0.0.1:7890 https://ifconfig.me`. |
| Service runs but websites don't load | Your proxy nodes may be down. Check the mihomo dashboard at `http://127.0.0.1:9090` or via `curl http://127.0.0.1:9090/proxies`. |
| `vpn: command not found` | Ensure the zsh function is autoloaded — check `fpath` and `autoload` in `~/.zshenv`. |
| mihomo updated and TUN stopped working | Re-run `sudo setcap` — package updates reset file capabilities. |
| "Limit exceeded" after changing subscription | Delete the cached provider file and re-run update: `rm ~/.config/mihomo/providers/<name>.yaml && vpn --update`. The cached file may contain stale "limit exceeded" dummy nodes from the old token. |
| Subscription URL changed | Edit `subscriptions.json` and run `vpn --update`. Do not edit `config.yaml` — it is regenerated from the template on every update. |
| `config.yaml` edits disappeared | Expected — it is a rendered artefact. Move the change into `config.template.yaml` and re-render. |
| `--render` produces an empty `proxy-providers:` block | `subscriptions.json` has no entries. Add one and run `vpn --update`. |
| The Quickshell widget shows "No providers" | mihomo has not reloaded after the render. `vpn --restart` or press UPDATE in the widget (it calls `vpn --update` + reload). |

## Acknowledgments

* [mihomo](https://github.com/MetaCubeX/mihomo) — the proxy kernel (Clash Meta).
* [mihomo-tui](https://github.com/MetaCubeX/mihomo-tui) — terminal UI for real-time monitoring and proxy management.
* [Metacubex Wiki](https://wiki.metacubex.one) — configuration reference.
* [uv](https://github.com/astral-sh/uv) — fast Python package and project manager.

## Disclaimer

This is a personal management script for a self-hosted proxy setup. Use it
responsibly and in compliance with your local laws and network policies.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
