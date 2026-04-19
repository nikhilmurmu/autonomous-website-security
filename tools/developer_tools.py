import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from crewai.tools import tool
from loguru import logger
from config.settings import CLIENTS_DIR

@tool("Generate Fix Plan")
def generate_fix_plan_tool(issue_description: str, technology: str) -> str:
    """
    Generate a structured fix plan for a security issue.
    In production, this would use the LLM to generate actual code.
    Here we return a template that the LLM agent can expand.
    """
    logger.info(f"Generating fix plan for: {issue_description[:50]}...")
    
    plan = {
        "issue": issue_description,
        "technology": technology,
        "recommended_action": None,
        "steps": [],
        "code_changes": [],
        "testing_needed": []
    }
    
    # Pre-defined plans for common issues
    if "missing_header" in issue_description.lower():
        header = issue_description.split(":")[-1].strip()
        plan["recommended_action"] = "add_security_header"
        plan["steps"] = [
            "Locate web server configuration file (.htaccess, nginx.conf, or web.config)",
            f"Add header directive for {header}",
            "Restart web server"
        ]
        plan["code_changes"] = [
            {
                "file": ".htaccess (Apache)",
                "content": f'Header always set {header} "..."'
            }
        ]
        plan["testing_needed"] = ["Verify header present in response", "Check site functionality"]
    
    elif "wordpress" in issue_description.lower() and "version" in issue_description.lower():
        plan["recommended_action"] = "update_wordpress"
        plan["steps"] = [
            "Create full backup",
            "Update WordPress core via admin or WP-CLI",
            "Update all plugins and themes",
            "Test critical functionality"
        ]
        plan["commands"] = ["wp core update", "wp plugin update --all", "wp theme update --all"]
    
    else:
        plan["recommended_action"] = "manual_review"
        plan["steps"] = ["Analyze issue manually", "Consult security documentation"]
    
    return json.dumps(plan, indent=2)


@tool("Create Backup")
def create_backup_tool(client_id: str, backup_type: str = "full") -> str:
    """
    Simulate creating a backup of client website.
    Returns backup metadata.
    """
    logger.info(f"Creating {backup_type} backup for client {client_id}")
    
    backup_dir = CLIENTS_DIR / client_id / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_id = f"{client_id}_{timestamp}"
    
    result = {
        "backup_id": backup_id,
        "client_id": client_id,
        "backup_type": backup_type,
        "timestamp": datetime.now().isoformat(),
        "location": str(backup_dir / backup_id),
        "verified": True,
        "status": "success"
    }
    
    # Create manifest file (simulated backup)
    manifest = {
        "backup_id": backup_id,
        "created_at": result["timestamp"],
        "type": backup_type,
        "files_backed_up": ["/wp-content/", "/wp-config.php", "/.htaccess"],
        "database_backed_up": True
    }
    
    manifest_path = backup_dir / f"{backup_id}_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    return json.dumps(result, indent=2)


@tool("Apply Update")
def apply_update_tool(client_id: str, update_type: str, target: str) -> str:
    """
    Simulate applying an update in staging environment.
    """
    logger.info(f"Applying {update_type} update to {target} for {client_id}")
    
    result = {
        "client_id": client_id,
        "update_type": update_type,
        "target": target,
        "timestamp": datetime.now().isoformat(),
        "status": "applied_in_staging",
        "staging_url": f"https://staging-{client_id}.autosec.ai",
        "steps_completed": [
            "Created backup point",
            f"Applied {update_type} update to {target}",
            "Cleared cache"
        ],
        "message": "Update applied successfully in staging. Ready for QA testing."
    }
    
    return json.dumps(result, indent=2)