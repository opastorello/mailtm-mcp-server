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

The server runs as an **HTTP MCP server** (`streamable-http`) on port `8000`, endpoint `/mcp`.

This makes it compatible with:
- [mcpjungle](https://github.com/mcpjungle/mcpjungle) and other HTTP-based MCP hosts
- Any MCP client that supports the `streamable-http` or `http` transport

## Quick Start

### Docker Compose (recommended)

```bash
curl -O https://raw.githubusercontent.com/opastorello/mailtm-mcp-server/master/docker-compose.yml
docker compose up -d
```

The server will be available at `http://localhost:8000/mcp`.

### Docker (manual)

```bash
docker pull ghcr.io/opastorello/mailtm-mcp-server:latest
docker run -d -p 8000:8000 -v mailtm-session:/tmp ghcr.io/opastorello/mailtm-mcp-server:latest
```

### Local (no Docker)

```bash
pip install -r requirements.txt
python mailtm_server.py
```

Requires Python 3.11+.

## Register with mcpjungle

```bash
cat > /tmp/mailtm.json << 'EOF'
{
  "name": "mailtm",
  "transport": "http",
  "url": "http://localhost:8000/mcp"
}
EOF

mcpjungle register -c /tmp/mailtm.json
```

## Configure in Claude Desktop

```json
{
  "mcpServers": {
    "mailtm": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-p", "8000:8000", "ghcr.io/opastorello/mailtm-mcp-server:latest"]
    }
  }
}
```

Or pointing to an already-running instance:

```json
{
  "mcpServers": {
    "mailtm": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Session Management

The server stores the active session in `/tmp/mailtm_session.json`:

- Session persists between tool calls automatically within the same run.
- Mount `/tmp` as a Docker volume to survive container restarts.
- `logout()` clears the session without deleting the account.
- `delete_account()` deletes the account and clears the session.

## Example Workflow

```
1. create_temp_email()           → generates a random address like abc123@dollicons.com
2. get_inbox()                   → check for new messages
3. read_email(message_id="...")  → read the content
4. delete_account()              → clean up when done
```

## Dependencies

- [`mcp[cli]`](https://pypi.org/project/mcp/) >= 1.2.0 — FastMCP server framework
- [`requests`](https://pypi.org/project/requests/) >= 2.31.0 — HTTP client for the mail.tm API

## License

MIT
