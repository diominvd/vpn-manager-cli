# vpn-manager-cli

Minimalist CLI manager for [mihomo](https://wiki.metacubex.one) (Clash Meta) proxy with transparent TUN mode and subscription auto-update.

## Table of Contents
* [Features](#features)
* [Requirements](#requirements)
* [Installation & Setup](#installation--setup)
* [Quick Start](#quick-start)
* [Usage](#usage)
* [Configuration](#configuration)
* [Troubleshooting](#troubleshooting)
* [Acknowledgments](#acknowledgments)
* [Disclaimer](#disclaimer)
* [License](#license)

## Features
* Transparent proxy via TUN mode — all system traffic routes through mihomo automatically.
* Subscription management: fetch and update proxy provider configs from remote sources.
* Systemd user service control (start / stop / restart / status).
* Fake-ip DNS for fast domain resolution without leaks.
* Mixed-port (HTTP + SOCKS5) for manual proxy usage at `127.0.0.1:7890`.
* TUI dashboard via [mihomo-tui](https://github.com/MetaCubeX/mihomo-tui) for real-time traffic monitoring and proxy switching.

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

Copy the template config to `~/.config/mihomo/`:

```bash
mkdir -p ~/.config/mihomo/providers
cp config.yaml ~/.config/mihomo/config.yaml
```

### 6. Configure subscriptions

Copy the example subscriptions file and fill in your credentials:

```bash
cp subscriptions.json.example subscriptions.json
```

Edit `subscriptions.json` and replace `YOUR_TOKEN` and `YOUR_HARDWARE_ID` with your subscription credentials.

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
vpn --update   # fetch proxy configs from your subscription
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
| `--update` | Fetch latest proxy configs from all configured subscriptions and save them to the providers directory. |

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
| `subscriptions[].name` | Provider name (used for logging). |
| `subscriptions[].url` | Subscription URL to fetch proxy configs from. |
| `subscriptions[].path` | Local path to save the downloaded config. Supports `~`. |
| `subscriptions[].decode` | Set `true` if the response is base64-encoded. |

Run `vpn --update` after changing subscriptions to fetch the latest configs.

### Mihomo config

The main config lives at `~/.config/mihomo/config.yaml`. Key sections:

| Section | Description |
| --- | --- |
| `mixed-port` | HTTP + SOCKS5 proxy port (default: `7890`). |
| `tun` | Transparent proxy settings — enable, stack, auto-route, DNS hijack. |
| `dns` | Fake-ip DNS with fallback resolvers. |
| `proxy-providers` | Remote subscription URLs for proxy server lists. |
| `proxy-groups` | Groups for selecting / load-balancing proxies. |
| `rules` | Routing rules (default: `MATCH,Proxies` — send everything through proxy). |

### TUN mode

TUN captures all system traffic transparently. The binary needs capabilities:

```bash
sudo setcap cap_net_admin,cap_net_bind_service=ep /usr/bin/mihomo
```

If you prefer not to use TUN, disable it in `config.yaml` and use the mixed-port
as a regular HTTP/SOCKS5 proxy (`127.0.0.1:7890`).

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `--start` fails with `operation not permitted` | Run `sudo setcap cap_net_admin,cap_net_bind_service=ep /usr/bin/mihomo` and restart. |
| DNS error `bind: permission denied` | Same fix — capabilities are needed for port 53. Or change `dns.listen` to `0.0.0.0:5353` and disable TUN. |
| `--update` fails to fetch subscription | Check your `subscriptions.json` and network connection. Verify headers match your provider's requirements. |
| `config not found` | Copy `subscriptions.json.example` to `subscriptions.json` and fill in your credentials. |
| No traffic going through proxy | Check `vpn --status` for errors. Verify the service is active and TUN started. Test with `curl -x http://127.0.0.1:7890 https://ifconfig.me`. |
| Service runs but websites don't load | Your proxy nodes may be down. Check the mihomo dashboard at `http://127.0.0.1:9090` or via `curl http://127.0.0.1:9090/proxies`. |
| `vpn: command not found` | Ensure the zsh function is autoloaded — check `fpath` and `autoload` in `~/.zshenv`. |
| mihomo updated and TUN stopped working | Re-run `sudo setcap` — package updates reset file capabilities. |
| "Limit exceeded" after changing subscription | Delete the cached provider file and restart: `rm ~/.config/mihomo/providers/<name>.yaml && vpn --restart`. The cached file may contain stale "limit exceeded" dummy nodes from the old token. |
| Subscription URL changed | Update **both** `subscriptions.json` (for `vpn --update`) and `config.yaml` `proxy-providers` section (for mihomo runtime fetching). |

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
