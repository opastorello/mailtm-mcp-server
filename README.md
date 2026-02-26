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

## Usage

### Pull from GitHub Container Registry (recommended)

```bash
docker pull ghcr.io/opastorello/mailtm-mcp-server:latest
docker run --rm -i ghcr.io/opastorello/mailtm-mcp-server:latest
```

To persist the session across container restarts, mount a volume:

```bash
docker run --rm -i -v mailtm-session:/tmp ghcr.io/opastorello/mailtm-mcp-server:latest
```

### Build locally

```bash
docker build -t mailtm-mcp-server .
docker run --rm -i mailtm-mcp-server
```

### Run locally (no Docker)

```bash
pip install -r requirements.txt
python mailtm_server.py
```

Requires Python 3.11+.

## Configure in Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mailtm": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "ghcr.io/opastorello/mailtm-mcp-server:latest"]
    }
  }
}
```

Or if running locally:

```json
{
  "mcpServers": {
    "mailtm": {
      "command": "python",
      "args": ["/path/to/mailtm_server.py"]
    }
  }
}
```

## Session Management

The server stores the active session in `/tmp/mailtm_session.json`. This means:

- Within the same container run, session persists between tool calls automatically.
- If you mount `/tmp` as a Docker volume, the session survives container restarts.
- Calling `logout()` clears the session file without deleting the account.
- Calling `delete_account()` deletes the account and clears the session.

## Example Workflow

```
1. create_temp_email()           → generates a random address like abc123@mailnull.com
2. get_inbox()                   → check for new messages
3. read_email(message_id="...")  → read the content
4. delete_account()              → clean up when done
```

## Dependencies

- [`mcp[cli]`](https://pypi.org/project/mcp/) >= 1.2.0 — FastMCP server framework
- [`requests`](https://pypi.org/project/requests/) >= 2.31.0 — HTTP client for the mail.tm API

## License

MIT
