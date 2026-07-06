"""
Remote WordPress fix tools that call the AutoSec plugin REST endpoint.
"""
import json
import hashlib
import hmac
import requests
from pathlib import Path
from crewai.tools import tool
from loguru import logger
from config.settings import CLIENTS_DIR

def _call_plugin(client_id: str, action: str, **kwargs) -> dict:
    """Sign and send a fix request to the client's WordPress plugin."""
    config_path = CLIENTS_DIR / client_id / "config.json"
    if not config_path.exists():
        return {"error": f"Client {client_id} not found"}

    with open(config_path) as f:
        config = json.load(f)

    site_url = config["site_url"].rstrip("/")
    api_key = config.get("api_key", "autosec-secret-2026")

    payload = {"action": action}
    payload.update(kwargs)
    body = json.dumps(payload)

    # Generate HMAC signature using the shared API key
    signature = hmac.new(
        api_key.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Autosec-Signature": signature
    }

    url = f"{site_url}/wp-json/autosec/v1/fix"
    logger.info(f"Sending {action} to {url}")

    try:
        resp = requests.post(url, data=body, headers=headers, timeout=30)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

# --- CrewAI tool wrappers ---

@tool("Remote Add Security Headers")
def remote_add_headers_tool(client_id: str) -> str:
    """Add security headers to the remote WordPress site via the plugin."""
    result = _call_plugin(client_id, "add_headers")
    return json.dumps(result, indent=2)

@tool("Remote Update Plugin")
def remote_update_plugin_tool(client_id: str, plugin_slug: str) -> str:
    """Update a specific plugin on the remote WordPress site."""
    result = _call_plugin(client_id, "update_plugin", plugin_slug=plugin_slug)
    return json.dumps(result, indent=2)

@tool("Remote Backup Database")
def remote_backup_db_tool(client_id: str) -> str:
    """Create a database backup on the remote WordPress site."""
    result = _call_plugin(client_id, "backup_db")
    return json.dumps(result, indent=2)