#!/usr/bin/env python3
"""
Mail.tm MCP Server - Manage temporary email addresses via the mail.tm API
"""
import sys
import json
import os
import logging
import random
import string
import requests
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("mailtm-server")

mcp = FastMCP("mailtm")

BASE_URL = "https://api.mail.tm"
SESSION_FILE = "/tmp/mailtm_session.json"

# In-memory session state
_session: dict = {
    "token": None,
    "account_id": None,
    "address": None,
}


def _load_session():
    """Load session from file (survives container restarts if volume is mounted)."""
    global _session
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                _session.update(data)
                logger.info(f"Session restored from file: {_session.get('address')}")
        except Exception as e:
            logger.warning(f"Could not load session file: {e}")


def _save_session():
    """Persist session to file."""
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(_session, f)
    except Exception as e:
        logger.warning(f"Could not save session file: {e}")


def _clear_session():
    """Clear session state from memory and file."""
    _session.update({"token": None, "account_id": None, "address": None})
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        pass


def _auth_headers() -> dict:
    _load_session()
    if _session["token"]:
        return {"Authorization": f"Bearer {_session['token']}"}
    return {}


def _require_session() -> str | None:
    """Returns an error string if no active session, else None."""
    _load_session()
    if not _session["token"]:
        return "No active session. Use create_temp_email or login first."
    return None


# === TOOLS ===

@mcp.tool()
def list_domains() -> str:
    """List all available domains for creating temporary email addresses."""
    logger.info("Listing domains")
    try:
        resp = requests.get(f"{BASE_URL}/domains", timeout=10)
        resp.raise_for_status()
        domains = resp.json().get("hydra:member", [])
        if not domains:
            return "No domains available at the moment."
        lines = [f"  - {d['domain']}" for d in domains]
        return "Available domains:\n" + "\n".join(lines)
    except Exception as e:
        logger.error(f"list_domains error: {e}")
        return f"Error listing domains: {e}"


@mcp.tool()
def create_temp_email(address: str = "", password: str = "") -> str:
    """
    Create a new temporary email account on mail.tm.

    - address: full email address (e.g. user@domain.com). If empty, a random one is generated.
    - password: account password. If empty, a random secure password is generated.

    Stores the session token internally so you can call get_inbox, read_email, etc. right away.
    Returns the address and password so you can reuse them later with login().
    """
    logger.info(f"Creating temp email: address={address or 'random'}")
    try:
        # Pick a domain if no address provided
        if not address:
            resp = requests.get(f"{BASE_URL}/domains", timeout=10)
            resp.raise_for_status()
            domains = resp.json().get("hydra:member", [])
            if not domains:
                return "No domains available to create an account."
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            address = f"{username}@{domains[0]['domain']}"

        # Generate password if not provided
        if not password:
            chars = string.ascii_letters + string.digits + "!@#$%"
            password = ''.join(random.choices(chars, k=16))

        # Create the account
        resp = requests.post(
            f"{BASE_URL}/accounts",
            json={"address": address, "password": password},
            timeout=10
        )
        if resp.status_code == 422:
            return f"Error: Address '{address}' is already taken or invalid. Try a different one."
        resp.raise_for_status()
        account = resp.json()

        # Get auth token
        resp = requests.post(
            f"{BASE_URL}/token",
            json={"address": address, "password": password},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        _session["token"] = data["token"]
        _session["account_id"] = data["id"]
        _session["address"] = address
        _save_session()

        return (
            f"Temporary email created!\n"
            f"Address:  {address}\n"
            f"Password: {password}\n"
            f"Account ID: {data['id']}\n\n"
            f"Session is active. Use get_inbox() to check messages."
        )
    except Exception as e:
        logger.error(f"create_temp_email error: {e}")
        return f"Error creating email: {e}"


@mcp.tool()
def login(address: str, password: str) -> str:
    """
    Log in to an existing mail.tm account.

    - address: the email address
    - password: the account password

    Stores the session token so subsequent tool calls work without passing credentials.
    """
    logger.info(f"Logging in as {address}")
    try:
        resp = requests.post(
            f"{BASE_URL}/token",
            json={"address": address, "password": password},
            timeout=10
        )
        if resp.status_code == 401:
            return "Login failed: invalid address or password."
        resp.raise_for_status()
        data = resp.json()

        _session["token"] = data["token"]
        _session["account_id"] = data["id"]
        _session["address"] = address
        _save_session()

        return f"Logged in as {address}. Session active."
    except Exception as e:
        logger.error(f"login error: {e}")
        return f"Error logging in: {e}"


@mcp.tool()
def get_inbox(page: int = 1) -> str:
    """
    List messages in the current inbox.

    - page: page number (default 1, each page has up to 30 messages)

    Requires an active session (call create_temp_email or login first).
    """
    err = _require_session()
    if err:
        return err
    logger.info(f"Getting inbox page {page} for {_session['address']}")
    try:
        resp = requests.get(
            f"{BASE_URL}/messages?page={page}",
            headers=_auth_headers(),
            timeout=10
        )
        resp.raise_for_status()
        body = resp.json()
        messages = body.get("hydra:member", [])
        total = body.get("hydra:totalItems", 0)

        if not messages:
            return f"Inbox is empty for {_session['address']}."

        lines = [f"Inbox: {_session['address']} | {total} message(s) total | Page {page}"]
        lines.append("-" * 60)
        for m in messages:
            from_addr = m.get("from", {}).get("address", "unknown")
            subject = m.get("subject", "(no subject)")
            status = "UNREAD" if not m.get("seen") else "read"
            msg_id = m.get("id", "")
            lines.append(f"[{status}] {subject}")
            lines.append(f"  From: {from_addr}")
            lines.append(f"  ID:   {msg_id}")
            lines.append("")

        return "\n".join(lines).rstrip()
    except Exception as e:
        logger.error(f"get_inbox error: {e}")
        return f"Error fetching inbox: {e}"


@mcp.tool()
def read_email(message_id: str) -> str:
    """
    Read the full content of an email by its ID.

    - message_id: the message ID from get_inbox()

    Requires an active session.
    """
    err = _require_session()
    if err:
        return err
    logger.info(f"Reading message {message_id}")
    try:
        resp = requests.get(
            f"{BASE_URL}/messages/{message_id}",
            headers=_auth_headers(),
            timeout=10
        )
        if resp.status_code == 404:
            return f"Message '{message_id}' not found."
        resp.raise_for_status()
        m = resp.json()

        from_addr = m.get("from", {}).get("address", "unknown")
        subject = m.get("subject", "(no subject)")
        to_list = [r.get("address", "") for r in m.get("to", [])]
        date = m.get("createdAt", "")
        text = m.get("text", "")
        html = m.get("html", [""])
        # Prefer plain text; fall back to HTML snippet
        body = text if text else (html[0] if html else "(no body)")

        return (
            f"From:    {from_addr}\n"
            f"To:      {', '.join(to_list)}\n"
            f"Subject: {subject}\n"
            f"Date:    {date}\n"
            f"ID:      {message_id}\n"
            f"{'-' * 60}\n"
            f"{body}"
        )
    except Exception as e:
        logger.error(f"read_email error: {e}")
        return f"Error reading email: {e}"


@mcp.tool()
def mark_as_read(message_id: str) -> str:
    """
    Mark an email as read.

    - message_id: the message ID from get_inbox()

    Requires an active session.
    """
    err = _require_session()
    if err:
        return err
    logger.info(f"Marking message {message_id} as read")
    try:
        resp = requests.patch(
            f"{BASE_URL}/messages/{message_id}",
            json={"seen": True},
            headers=_auth_headers(),
            timeout=10
        )
        if resp.status_code == 404:
            return f"Message '{message_id}' not found."
        resp.raise_for_status()
        return f"Message '{message_id}' marked as read."
    except Exception as e:
        logger.error(f"mark_as_read error: {e}")
        return f"Error marking as read: {e}"


@mcp.tool()
def delete_email(message_id: str) -> str:
    """
    Delete an email message permanently.

    - message_id: the message ID from get_inbox()

    Requires an active session.
    """
    err = _require_session()
    if err:
        return err
    logger.info(f"Deleting message {message_id}")
    try:
        resp = requests.delete(
            f"{BASE_URL}/messages/{message_id}",
            headers=_auth_headers(),
            timeout=10
        )
        if resp.status_code == 404:
            return f"Message '{message_id}' not found."
        if resp.status_code == 204:
            return f"Message '{message_id}' deleted."
        resp.raise_for_status()
        return f"Message '{message_id}' deleted."
    except Exception as e:
        logger.error(f"delete_email error: {e}")
        return f"Error deleting email: {e}"


@mcp.tool()
def get_account_info() -> str:
    """
    Get details about the currently logged-in account (address, quota, usage).

    Requires an active session.
    """
    err = _require_session()
    if err:
        return err
    logger.info("Getting account info")
    try:
        resp = requests.get(f"{BASE_URL}/me", headers=_auth_headers(), timeout=10)
        resp.raise_for_status()
        m = resp.json()
        quota = m.get("quota", 0)
        used = m.get("used", 0)
        pct = (used / quota * 100) if quota else 0
        return (
            f"Account:  {m.get('address', 'N/A')}\n"
            f"ID:       {m.get('id', 'N/A')}\n"
            f"Storage:  {used} / {quota} bytes ({pct:.1f}% used)\n"
            f"Created:  {m.get('createdAt', 'N/A')}\n"
            f"Updated:  {m.get('updatedAt', 'N/A')}"
        )
    except Exception as e:
        logger.error(f"get_account_info error: {e}")
        return f"Error getting account info: {e}"


@mcp.tool()
def delete_account() -> str:
    """
    Permanently delete the current account and all its messages.
    This cannot be undone. Clears the active session.

    Requires an active session.
    """
    err = _require_session()
    if err:
        return err
    account_id = _session["account_id"]
    address = _session["address"]
    logger.info(f"Deleting account {address} ({account_id})")
    try:
        resp = requests.delete(
            f"{BASE_URL}/accounts/{account_id}",
            headers=_auth_headers(),
            timeout=10
        )
        if resp.status_code == 204:
            _clear_session()
            return f"Account '{address}' permanently deleted. Session cleared."
        resp.raise_for_status()
        return "Account deletion failed."
    except Exception as e:
        logger.error(f"delete_account error: {e}")
        return f"Error deleting account: {e}"


@mcp.tool()
def logout() -> str:
    """
    Clear the current session. Does not delete the account — you can log back in later
    using login() with the same credentials.
    """
    _load_session()
    address = _session.get("address") or "unknown"
    _clear_session()
    logger.info(f"Logged out {address}")
    return f"Logged out. Session for '{address}' cleared."


# === STARTUP ===
if __name__ == "__main__":
    logger.info("Starting Mail.tm MCP server...")
    _load_session()
    if _session.get("address"):
        logger.info(f"Restored session for: {_session['address']}")
    try:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
