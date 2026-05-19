# Install agentmemory for OpenClaw

This records the working OpenClaw-specific setup used on an OpenClaw host where the gateway runs as a user systemd service.

Upstream project: [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory)

## Tested Versions

| Component | Version |
| --- | --- |
| OpenClaw | 2026.5.12 (f066dd2) |
| agentmemory | 0.9.20 |
| @agentmemory/mcp | 0.9.20 |
| Node.js | v22.22.0 |
| npm | 10.9.4 |

## Install agentmemory

Install the package globally:

```bash
npm install -g @agentmemory/agentmemory
```

Verify the installed version:

```bash
npm list -g --depth=0 @agentmemory/agentmemory
```

On this host, the package installed as:

```text
@agentmemory/agentmemory@0.9.20
```

## Run agentmemory with systemd

Create `~/.config/systemd/user/agentmemory.service`:

```ini
[Unit]
Description=agentmemory local memory server
After=network-online.target

[Service]
Type=simple
Environment=AGENTMEMORY_URL=http://localhost:3111
ExecStart=/home/claw/.npm-global/bin/agentmemory --tools all
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Enable and start it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now agentmemory.service
systemctl --user status agentmemory.service
```

The expected local endpoints are:

- REST API: `http://localhost:3111`
- Viewer: `http://localhost:3113`
- Streams: `ws://localhost:3112`

## OpenClaw MCP Configuration

The upstream `agentmemory connect openclaw` command wrote a legacy root-level `mcpServers` config. That is not valid for OpenClaw `2026.5.12`.

Use OpenClaw's `mcp.servers` structure instead:

```json
{
  "mcp": {
    "servers": {
      "agentmemory": {
        "command": "npx",
        "args": ["-y", "@agentmemory/mcp"],
        "env": {
          "AGENTMEMORY_URL": "http://localhost:3111"
        }
      }
    }
  }
}
```

This lets OpenClaw spawn the MCP bridge with:

```bash
npx -y @agentmemory/mcp
```

## OpenClaw Native Plugin

Install the OpenClaw integration from the cloned agentmemory repo:

```bash
openclaw plugins install /mnt/disk_storage/app-data/openclaw/workspace/agentmemory/integrations/openclaw
```

Then set the memory slot in the OpenClaw config:

```json
{
  "plugins": {
    "slots": {
      "memory": "agentmemory"
    },
    "entries": {
      "agentmemory": {
        "enabled": true
      }
    }
  }
}
```

## Restart OpenClaw

Restart the gateway after changing config:

```bash
systemctl --user restart openclaw-gateway.service
```

Verify both services are active:

```bash
systemctl --user status openclaw-gateway.service agentmemory.service
```

On the tested host:

```text
openclaw-gateway.service: active (running)
agentmemory.service: active (running)
```

The restarted OpenClaw gateway spawned `@agentmemory/mcp`, confirming that the memory integration loaded.

## Expose the Viewer on Tailscale

The viewer binds to localhost by default:

```text
127.0.0.1:3113
```

If your user can manage Tailscale Serve, the simplest tailnet-only option is:

```bash
tailscale serve --bg 3113
```

On this host, non-root Serve changes were denied:

```text
Access denied: serve config denied
Use 'sudo tailscale serve --bg 3113'.
```

Because sudo was not available to the agent session, the working fallback was a user-level HTTP proxy bound only to the Tailscale IPv4 address. The proxy rewrites the `Host` header to `localhost:3113`; a plain TCP forward reached the viewer but returned `403 Forbidden` because the viewer rejects the Tailscale IP host header.

Install the helper script:

```bash
install -m 0755 scripts/http-host-proxy.mjs /mnt/disk_storage/app-data/openclaw/workspace/scripts/http-host-proxy.mjs
```

Create `~/.config/systemd/user/agentmemory-viewer-tailscale.service`:

```ini
[Unit]
Description=Expose agentmemory viewer on Tailscale
After=agentmemory.service tailscaled.service
Wants=agentmemory.service

[Service]
Type=simple
Environment=LISTEN_HOST=<tailscale-ipv4>
Environment=LISTEN_PORT=3113
Environment=TARGET_HOST=127.0.0.1
Environment=TARGET_PORT=3113
Environment=TARGET_HOST_HEADER=localhost:3113
ExecStart=/usr/bin/node /mnt/disk_storage/app-data/openclaw/workspace/scripts/http-host-proxy.mjs
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now agentmemory-viewer-tailscale.service
```

Verify:

```bash
curl -I http://<tailscale-ipv4>:3113/
```

The viewer should now be reachable from tailnet devices at:

```text
http://<machine-name>.<tailnet-name>.ts.net:3113/
```

## macOS Multi-Agent Companion Setup

This section records the companion setup used on a macOS workstation where the same `agentmemory` server is shared by Claude Code, Codex CLI, and OpenCode.

### Tested macOS Versions

| Component | Version |
| --- | --- |
| macOS runtime | user LaunchAgent |
| agentmemory | 0.9.20, source checkout linked globally |
| Claude Code | 2.1.144 |
| Codex CLI | 0.130.0 |
| OpenCode | 1.4.10 |
| Node.js | v25.9.0 |
| npm | 11.12.1 |

### Source Install

The upstream package currently has a peer dependency mismatch between `@anthropic-ai/claude-agent-sdk` and `@anthropic-ai/sdk` when installing from source, so use `--legacy-peer-deps`.

```bash
git clone https://github.com/rohitg00/agentmemory.git ~/agentmemory
cd ~/agentmemory
npm install --legacy-peer-deps
npm run build
npm link --legacy-peer-deps
agentmemory --help
```

Seed the default config and skip interactive first-run onboarding for unattended launchd startup:

```bash
agentmemory init
mkdir -p ~/.agentmemory
cat > ~/.agentmemory/preferences.json <<'JSON'
{
  "schemaVersion": 1,
  "lastAgent": null,
  "lastAgents": [],
  "lastProvider": null,
  "skipSplash": true,
  "skipNpxHint": true,
  "skipGlobalInstall": true,
  "skipConsoleInstall": true,
  "firstRunAt": "2026-05-19T07:10:00.000Z"
}
JSON
```

### Run agentmemory with launchd

Create `~/.agentmemory/start-agentmemory.sh`:

```zsh
#!/bin/zsh
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export AGENTMEMORY_TOOLS="${AGENTMEMORY_TOOLS:-core}"

cd /Users/s/agentmemory
exec /opt/homebrew/bin/node /Users/s/agentmemory/dist/cli.mjs
```

Create `~/Library/LaunchAgents/dev.agentmemory.server.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>dev.agentmemory.server</string>

  <key>ProgramArguments</key>
  <array>
    <string>/Users/s/.agentmemory/start-agentmemory.sh</string>
  </array>

  <key>WorkingDirectory</key>
  <string>/Users/s/agentmemory</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>AGENTMEMORY_TOOLS</key>
    <string>core</string>
  </dict>

  <key>StandardOutPath</key>
  <string>/Users/s/.agentmemory/launchd.out.log</string>

  <key>StandardErrorPath</key>
  <string>/Users/s/.agentmemory/launchd.err.log</string>
</dict>
</plist>
```

Enable and start it:

```bash
chmod +x ~/.agentmemory/start-agentmemory.sh
plutil -lint ~/Library/LaunchAgents/dev.agentmemory.server.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.agentmemory.server.plist
launchctl enable gui/$(id -u)/dev.agentmemory.server
launchctl kickstart -k gui/$(id -u)/dev.agentmemory.server
```

Verify:

```bash
curl http://localhost:3111/agentmemory/livez
agentmemory status
```

Expected health response:

```json
{"service":"agentmemory","status":"ok"}
```

This is a user LaunchAgent, so it restarts after login on macOS reboot.

### Claude Code Usage

Upstream README path: `README.md#claude-code-one-block-paste-it`.

Install both the MCP bridge and the full Claude Code plugin:

```bash
agentmemory connect claude-code --force
claude plugin marketplace add rohitg00/agentmemory
claude plugin install agentmemory
```

What this gives Claude Code:

- `@agentmemory/mcp` stdio server.
- Full `agentmemory@agentmemory` plugin.
- 12 Claude Code hooks.
- 4 skills.
- MCP memory tools such as `memory_smart_search`, `memory_save`, and `memory_sessions`.

Verify:

```bash
claude plugin list
claude mcp list
```

Expected entries:

```text
agentmemory@agentmemory  Status: enabled
agentmemory: npx -y @agentmemory/mcp - Connected
```

Restart Claude Code, or run `/mcp` inside a Claude Code session, to pick up the new server.

### Codex CLI Usage

Upstream README path: `README.md#codex-cli-codex-plugin-platform`.

Wire the MCP server:

```bash
agentmemory connect codex --force
```

This writes the following shape to `~/.codex/config.toml`:

```toml
[mcp_servers.agentmemory]
command = "npx"
args = ["-y", "@agentmemory/mcp"]

[mcp_servers.agentmemory.env]
AGENTMEMORY_URL = "http://localhost:3111"
```

Register the plugin marketplace:

```bash
codex plugin marketplace add rohitg00/agentmemory
```

The upstream README also lists:

```bash
codex plugin install agentmemory
```

On Codex CLI `0.130.0`, `codex plugin install` is not available yet (`unrecognized subcommand 'install'`). The MCP setup above is still active and verified with:

```bash
codex mcp list
```

Expected entry:

```text
agentmemory  npx  -y @agentmemory/mcp  AGENTMEMORY_URL=*****  enabled
```

Restart Codex CLI or open a new session to load the MCP server.

### OpenCode Usage

Upstream README paths:

- `README.md#other-agents`, OpenCode rows.
- `plugin/opencode/README.md`.

Install the OpenCode MCP bridge, plugin, and slash commands globally:

```bash
mkdir -p ~/.config/opencode/plugins ~/.config/opencode/commands
cp ~/agentmemory/plugin/opencode/agentmemory-capture.ts ~/.config/opencode/plugins/
cp ~/agentmemory/plugin/opencode/commands/recall.md ~/.config/opencode/commands/
cp ~/agentmemory/plugin/opencode/commands/remember.md ~/.config/opencode/commands/
```

Create or merge `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "agentmemory": {
      "type": "local",
      "command": ["npx", "-y", "@agentmemory/mcp"],
      "enabled": true
    }
  },
  "plugin": ["./plugins/agentmemory-capture.ts"]
}
```

What this gives OpenCode:

- MCP memory tools through `@agentmemory/mcp`.
- 22 auto-capture hooks from `agentmemory-capture.ts`.
- `/recall` and `/remember` slash commands.
- Direct memory/context injection through OpenCode's system-transform hook.

Verify:

```bash
opencode mcp list
```

Expected entry:

```text
agentmemory connected
npx -y @agentmemory/mcp
```

Restart OpenCode or open a new session after changing config.

## Notes

- Keep `agentmemory.service` running before restarting OpenClaw, so the MCP bridge has a live REST API at `http://localhost:3111`.
- On macOS, keep the LaunchAgent loaded before opening Claude Code, Codex CLI, or OpenCode.
- Do not leave the legacy root-level `mcpServers` key in OpenClaw config for OpenClaw `2026.5.12`; use `mcp.servers`.
- Claude Code and Codex CLI use `agentmemory connect`; OpenCode currently needs the manual `opencode.json` plus plugin-file copy flow from upstream docs.
- The documented paths are from the tested hosts. Adjust `/home/claw/.npm-global/bin/agentmemory`, `/Users/s/agentmemory`, and the agentmemory checkout path if your install uses different locations.
