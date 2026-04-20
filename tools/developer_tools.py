import json
import re
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from crewai.tools import tool
from loguru import logger
from config.settings import CLIENTS_DIR

@tool("Generate Fix Plan")
def generate_fix_plan_tool(issue_description: str, technology: str = "Web Application", context: str = "") -> str:
    """
    Generate a structured fix plan for a security issue, optionally incorporating context from past similar fixes.
    
    Args:
        issue_description: Detailed description of the security issue.
        technology: Technology stack (e.g., "WordPress", "PHP", "Nginx").
        context: Optional string containing past similar fixes and their solutions.
    
    Returns:
        JSON string containing the fix plan.
    """
    logger.info(f"Generating fix plan for: {issue_description[:50]}...")
    if context:
        logger.info("Context from past fixes provided")
    
    plan = {
        "issue": issue_description,
        "technology": technology,
        "context_used": bool(context),
        "past_context_summary": context[:500] if context else None,
        "recommended_action": None,
        "steps": [],
        "code_changes": [],
        "commands": [],
        "testing_needed": []
    }
    
    # Use context to influence the plan (simple rule-based for now; in production, LLM would use it)
    if "missing_header" in issue_description.lower():
        # Extract specific header if mentioned
        import re
        header_match = re.search(r'Missing security header:?\s*([\w-]+)', issue_description, re.IGNORECASE)
        header_name = header_match.group(1) if header_match else "Security-Header"
        
        plan["recommended_action"] = "add_security_header"
        plan["steps"] = [
            "Locate web server configuration file (.htaccess, nginx.conf, or web.config)",
            f"Add header directive for {header_name}",
            "Restart web server to apply changes"
        ]
        plan["code_changes"] = [
            {
                "file": ".htaccess (Apache)",
                "content": f'Header always set {header_name} "..."'
            },
            {
                "file": "nginx.conf",
                "content": f'add_header {header_name} "...";'
            }
        ]
        plan["testing_needed"] = [
            f"Verify {header_name} appears in response headers",
            "Test website functionality remains intact"
        ]
        
        # If context contains past solutions, we could extract specific values
        if context and header_name in context:
            # In a real implementation, the LLM would parse the context
            plan["notes"] = "Past similar fix found in memory; consider reusing configuration values."
    
    elif "wordpress" in issue_description.lower() or "wp" in issue_description.lower():
        plan["recommended_action"] = "update_wordpress"
        plan["steps"] = [
            "Create full backup (files + database)",
            "Update WordPress core to latest version",
            "Update all plugins and themes",
            "Test critical functionality"
        ]
        plan["commands"] = [
            "wp core update",
            "wp plugin update --all",
            "wp theme update --all"
        ]
        plan["testing_needed"] = [
            "Verify admin dashboard accessible",
            "Test key user flows (login, checkout, forms)"
        ]
    
    elif "ssl" in issue_description.lower() or "tls" in issue_description.lower():
        plan["recommended_action"] = "renew_ssl_certificate"
        plan["steps"] = [
            "Verify certificate expiration date",
            "Renew certificate with CA (Let's Encrypt or commercial)",
            "Install new certificate on web server",
            "Restart web server"
        ]
        plan["commands"] = [
            "certbot renew --dry-run",
            "certbot renew --force-renewal"
        ]
        plan["testing_needed"] = [
            "Check SSL Labs rating",
            "Verify HTTPS works across browsers"
        ]
    
    else:
        plan["recommended_action"] = "manual_review"
        plan["steps"] = [
            "Analyze issue manually with security team",
            "Consult security documentation and CVE databases"
        ]
        if context:
            plan["steps"].append("Review past similar fixes provided in context")
        plan["notes"] = "No automated fix template available; human analysis required."
    
    # If context is provided, add a flag that the LLM should consider it
    if context:
        plan["llm_instruction"] = "Use the past_context_summary to inform and improve this fix plan."
    
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