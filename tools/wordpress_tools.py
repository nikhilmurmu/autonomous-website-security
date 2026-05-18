import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from crewai.tools import tool
from loguru import logger
from config.settings import CLIENTS_DIR

# Path to the PHP executable bundled with LocalWP (has mysqli)
LOCALWP_PHP = r"C:\Users\nikhi\AppData\Roaming\Local\lightning-services\php-8.2.29+0\bin\win64\php.exe"

def run_wp_cli(wp_path: str, command: list) -> dict:
    """Execute a WP-CLI command using LocalWP's PHP with correct MySQL env."""
    wp_cli_phar = str(Path(__file__).parent.parent / "wp-cli.phar")
    full_cmd = [LOCALWP_PHP, wp_cli_phar, f"--path={wp_path}"] + command
    
    env = os.environ.copy()
    # Point to the correct MySQL port and host
    env["MYSQL_TCP_PORT"] = "10005"
    env["MYSQL_HOST"] = "127.0.0.1"
    # Add MySQL bin directory so mysqldump is found
    env["PATH"] = (
        r"C:\Users\nikhi\AppData\Roaming\Local\lightning-services\mysql-8.0.35+4\bin\win64\bin" + ";" + env.get("PATH", "")
    )
    
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60, env=env)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "command": " ".join(full_cmd)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@tool("WP Plugin Update")
def wp_plugin_update_tool(client_id: str, plugin_slug: str) -> str:
    """Update a WordPress plugin to the latest version using WP-CLI."""
    config_path = CLIENTS_DIR / client_id / "config.json"
    if not config_path.exists():
        return json.dumps({"error": f"Client {client_id} not found"})
    
    with open(config_path) as f:
        config = json.load(f)
    
    logger.info(f"Updating plugin {plugin_slug} for {client_id}")
    result = run_wp_cli(config["wp_path"], ["plugin", "update", plugin_slug])
    return json.dumps(result, indent=2)


@tool("WP Core Update")
def wp_core_update_tool(client_id: str) -> str:
    """Update WordPress core to latest version."""
    config_path = CLIENTS_DIR / client_id / "config.json"
    if not config_path.exists():
        return json.dumps({"error": f"Client {client_id} not found"})
    
    with open(config_path) as f:
        config = json.load(f)
    
    logger.info(f"Updating WordPress core for {client_id}")
    result = run_wp_cli(config["wp_path"], ["core", "update"])
    return json.dumps(result, indent=2)


@tool("WP Backup")
def wp_backup_tool(client_id: str) -> str:
    """Create a WordPress database backup using WP-CLI."""
    config_path = CLIENTS_DIR / client_id / "config.json"
    if not config_path.exists():
        return json.dumps({"error": f"Client {client_id} not found"})
    
    with open(config_path) as f:
        config = json.load(f)
    
    backup_dir = CLIENTS_DIR / client_id / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_{timestamp}.sql"
    
    logger.info(f"Creating database backup for {client_id}")
    result = run_wp_cli(config["wp_path"], ["db", "export", str(backup_file)])
    
    return json.dumps({
        "backup_file": str(backup_file),
        "success": result["success"],
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", "")
    }, indent=2)


@tool("WP Add Security Headers")
def wp_add_security_headers_tool(client_id: str) -> str:
    """Add security headers to WordPress via .htaccess modification."""
    config_path = CLIENTS_DIR / client_id / "config.json"
    if not config_path.exists():
        return json.dumps({"error": f"Client {client_id} not found"})
    
    with open(config_path) as f:
        config = json.load(f)
    
    htaccess_path = Path(config["wp_path"]) / ".htaccess"
    if not htaccess_path.exists():
        return json.dumps({"error": ".htaccess not found"})
    
    headers_block = """
# Added by AutoSec AI
<IfModule mod_headers.c>
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    Header always set Content-Security-Policy "default-src 'self'"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Permissions-Policy "geolocation=(), microphone=(), camera=()"
</IfModule>
"""
    
    with open(htaccess_path, 'r') as f:
        content = f.read()
    
    if "AutoSec AI" in content:
        return json.dumps({"status": "already_present", "message": "Security headers already added"})
    
    with open(htaccess_path, 'a') as f:
        f.write("\n" + headers_block)
    
    logger.info(f"Added security headers to {client_id}")
    return json.dumps({"status": "added", "file": str(htaccess_path)})