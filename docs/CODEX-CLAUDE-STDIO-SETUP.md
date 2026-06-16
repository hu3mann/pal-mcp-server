# PAL MCP — Codex & Claude Code (stdio via Docker)

This guide documents the **stdio + `docker exec`** integration used when PAL runs as a
long-lived container and Codex or Claude Code spawn `server.py` per session.

PAL is **stdio-only**. It does not expose HTTP/SSE on port 3003. Configuring
`"type": "sse"` with `http://localhost:3003/sse` will always fail handshake.

## Architecture

```
Codex / Claude Code
    │  stdio
    ▼
docker exec -i pal-mcp-server /opt/venv/bin/python server.py
    │
    ▼
pal-mcp-server container (sleep infinity, env from .env)
```

The container stays alive with `sleep infinity`. Each MCP session runs a **new**
`server.py` process via `docker exec -i`.

## Quick start

### 1. Create `.env`

```bash
cd ~/code/pal-mcp-server
cp .env.example .env
# Add at least one API key (OPENAI_API_KEY, XAI_API_KEY, OPENROUTER_API_KEY, etc.)
# Do not put inline comments on the same line as a key value.
```

### 2. Start the container

```bash
docker compose up -d --build
docker ps --filter name=pal-mcp-server
# Expect: Up (healthy)
```

### 3. Verify handshake

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n' \
  | docker exec -i pal-mcp-server /opt/venv/bin/python server.py \
  | head -1
# Expect JSON with "serverInfo":{"name":"PAL",...}
```

## Client configuration

### Codex (`~/.codex/config.toml`)

```toml
[mcp_servers.pal]
command = "docker"
args = ["exec", "-i", "pal-mcp-server", "/opt/venv/bin/python", "server.py"]
required = true
startup_timeout_sec = 60
tool_timeout_sec = 300

[mcp_servers.pal.env]
PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
```

**Important:** Python path is `/opt/venv/bin/python` (image venv), not `/app/.venv/bin/python`.

Restart Codex after editing this file.

### Claude Code (`~/.claude.json` → `mcpServers.pal`)

```json
"pal": {
  "type": "stdio",
  "command": "docker",
  "args": [
    "exec",
    "-i",
    "pal-mcp-server",
    "/opt/venv/bin/python",
    "server.py"
  ]
}
```

## docker-compose.yml changes (why they matter)

| Change | Reason |
|--------|--------|
| `container_name: pal-mcp-server` | Matches `docker exec` target in client configs |
| `env_file: .env` | Loads API keys into the container reliably |
| `command: ["sleep", "infinity"]` | Keeps container up; `server.py` as PID 1 exits without stdin |
| `stdin_open: true` / `tty: true` | Compatible with interactive `docker exec` |
| Removed fixed `172.20.0.0/16` subnet | Avoids "Pool overlaps" network errors on busy Docker hosts |
| Healthcheck imports `mcp`, `openai` | Works when `server.py` is not the main process |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Cannot connect to docker.sock` / container not found | Container not running or wrong name | `docker compose up -d`; name must be `pal-mcp-server` |
| `At least one API configuration is required` | Empty keys in container | Fill `.env`, then `docker compose up -d --force-recreate` |
| Connection refused on `:3003` | SSE config against stdio-only server | Switch client config to stdio `docker exec` (above) |
| `No such file: /app/.venv/bin/python` | Wrong venv path in client config | Use `/opt/venv/bin/python` |
| Container restart loop | `server.py` as CMD without stdin | Use `sleep infinity` compose command |
| Network create fails (pool overlap) | Fixed subnet collides | Use default bridge network (no custom ipam) |

## Dopemux `compose.yml` note

The Dopemux monorepo also defines `mcp-pal` (HTTP, port 3003) and `mcp-pal-stdio`.
That stack is **separate** from this standalone `~/code/pal-mcp-server` checkout.
Codex config in this setup targets **`pal-mcp-server`** from this repo's `docker compose`.

## Security

- Never commit `.env` (gitignored).
- Rotate keys if they were pasted into chat or logs.
- `docker exec` grants the MCP client the same API keys present in the container environment.