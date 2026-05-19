# Install agentmemory for OpenClaw

This records the working OpenClaw-specific setup used on an OpenClaw host where the gateway runs as a user systemd service.

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

## Notes

- Keep `agentmemory.service` running before restarting OpenClaw, so the MCP bridge has a live REST API at `http://localhost:3111`.
- Do not leave the legacy root-level `mcpServers` key in OpenClaw config for OpenClaw `2026.5.12`; use `mcp.servers`.
- The documented paths are from the tested host. Adjust `/home/claw/.npm-global/bin/agentmemory` and the agentmemory checkout path if your install uses different locations.
