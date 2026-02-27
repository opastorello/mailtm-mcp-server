# Mail.tm MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that lets AI assistants manage temporary email addresses via the [mail.tm](https://mail.tm) API. Create disposable inboxes, read messages, and manage accounts — all from your AI chat.

[![Docker Image](https://ghcr-badge.egpl.dev/opastorello/mailtm-mcp-server/size)](https://github.com/opastorello/mailtm-mcp-server/pkgs/container/mailtm-mcp-server)
[![GitHub release](https://img.shields.io/github/v/release/opastorello/mailtm-mcp-server)](https://github.com/opastorello/mailtm-mcp-server/releases)

## Tools

| Tool | Description |
|------|-------------|
| `list_domains` | List available domains for creating temp addresses |
| `create_temp_email` | Create a new disposable email account (random or custom) |
| `login` | Log in to an existing mail.tm account |
| `get_inbox` | List messages in the current inbox (paginated) |
| `read_email` | Read the full content of an email by ID |
| `mark_as_read` | Mark a message as read |
| `delete_email` | Permanently delete a message |
| `get_account_info` | Get current account details and storage usage |
| `delete_account` | Permanently delete the account and all its messages |
| `logout` | Clear the current session without deleting the account |

## Transport

The server runs as a **streamable-http** MCP server on port `8000`, endpoint `/mcp`.

Compatible with:
- [mcpjungle](https://github.com/mcpjungle/mcpjungle)
- Claude Desktop (HTTP mode)
- Any MCP client that supports `streamable-http`

---

## Quick Start

### Docker Compose (recommended)

```bash
curl -O https://raw.githubusercontent.com/opastorello/mailtm-mcp-server/master/docker-compose.yml
docker compose up -d
```

Server available at `http://localhost:8000/mcp`.

### Docker (manual)

```bash
docker pull ghcr.io/opastorello/mailtm-mcp-server:latest
docker run -d -p 8000:8000 -v mailtm-session:/tmp --name mailtm ghcr.io/opastorello/mailtm-mcp-server:latest
```

### Local (no Docker)

```bash
pip install -r requirements.txt
python mailtm_server.py
```

Requires Python 3.11+.

---

## Register with mcpjungle

### Standalone (mcpjungle on the host)

```bash
cat > /tmp/mailtm.json << 'EOF'
{
  "name": "mailtm",
  "transport": "streamable_http",
  "url": "http://localhost:8000/mcp"
}
EOF

mcpjungle register -c /tmp/mailtm.json
```

### mcpjungle running in Docker (same host)

When mcpjungle runs inside Docker, `localhost` doesn't resolve to the host. You need both containers on the same Docker network.

The included `docker-compose.yml` handles this automatically — it joins the `opt_default` network (mcpjungle's default network) and sets a fixed container name `mailtm` so the hostname never changes across restarts.

```bash
# Download and start
curl -O https://raw.githubusercontent.com/opastorello/mailtm-mcp-server/master/docker-compose.yml
docker compose up -d

# Register using the container hostname
cat > /tmp/mailtm.json << 'EOF'
{
  "name": "mailtm",
  "transport": "streamable_http",
  "url": "http://mailtm:8000/mcp"
}
EOF

mcpjungle register -c /tmp/mailtm.json
```

> **Note:** The transport value is `streamable_http` (underscore), not `http` — this is mcpjungle-specific.

> **Note:** `host.docker.internal` does not work on Linux. Use the container name or a fixed IP instead.

To re-register after changes:

```bash
mcpjungle deregister mailtm
mcpjungle register -c /tmp/mailtm.json
```

### Invoke tools via mcpjungle CLI

```bash
mcpjungle invoke mailtm__create_temp_email
mcpjungle invoke mailtm__get_inbox
mcpjungle invoke mailtm__list_domains
```

---

## Configure in Claude Desktop

Pointing to a running instance:

```json
{
  "mcpServers": {
    "mailtm": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

## Session Management

The server stores the active session in `/tmp/mailtm_session.json`:

- Session persists between tool calls automatically within the same run.
- Mount `/tmp` as a Docker volume to survive container restarts.
- `logout()` clears the session without deleting the account.
- `delete_account()` deletes the account and clears the session.

---

## Example Workflow

```
1. create_temp_email()           → generates a random address like abc123@dollicons.com
2. get_inbox()                   → check for new messages
3. read_email(message_id="...")  → read the content
4. delete_account()              → clean up when done
```

---

## Dependencies

- [`mcp[cli]`](https://pypi.org/project/mcp/) >= 1.2.0 — FastMCP server framework
- [`requests`](https://pypi.org/project/requests/) >= 2.31.0 — HTTP client for the mail.tm API

---

## License

MIT — [Nícolas Pastorello](https://github.com/opastorello)
