import requests
import json
import re
from datetime import datetime
from typing import Dict, Any

def scan_website_direct(url: str) -> Dict[str, Any]:
    """
    Directly scan a website without LLM involvement.
    Returns a clean Python dictionary.
    """
    results = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "technology_stack": {},
        "security_headers": {},
        "issues": [],
        "warnings": [],
        "status_code": None,
        "final_url": None,
        "scan_successful": False
    }
    
    try:
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "AutoSec-Security-Scanner/1.0"},
            allow_redirects=True
        )
        
        results["status_code"] = response.status_code
        results["final_url"] = response.url
        results["scan_successful"] = True
        
        # Security headers check
        security_headers = [
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Permissions-Policy"
        ]
        
        for header in security_headers:
            if header in response.headers:
                results["security_headers"][header] = response.headers[header]
            else:
                results["issues"].append({
                    "type": "missing_header",
                    "header": header,
                    "severity": "medium",
                    "description": f"Missing security header: {header}"
                })
        
        # WordPress detection
        if "wp-content" in response.text or "wp-includes" in response.text:
            results["technology_stack"]["cms"] = "WordPress"
            version_match = re.search(r'WordPress\s+([\d.]+)', response.text)
            if version_match:
                results["technology_stack"]["wordpress_version"] = version_match.group(1)
            else:
                gen_match = re.search(r'<meta name="generator" content="WordPress ([\d.]+)"', response.text)
                if gen_match:
                    results["technology_stack"]["wordpress_version"] = gen_match.group(1)
        
        # Exposed sensitive files check
        sensitive_files = [".git/config", ".env", "wp-config.php.bak", "backup.zip"]
        for sensitive in sensitive_files:
            test_url = url.rstrip("/") + "/" + sensitive
            try:
                r = requests.get(test_url, timeout=5)
                if r.status_code == 200:
                    results["issues"].append({
                        "type": "exposed_file",
                        "file": sensitive,
                        "severity": "critical",
                        "description": f"Exposed sensitive file: {sensitive}"
                    })
            except:
                pass
                
    except Exception as e:
        results["error"] = str(e)
    
    return results

def generate_scan_summary(scan_data: Dict[str, Any]) -> str:
    """Generate a human-readable summary from scan results."""
    if not scan_data.get("scan_successful"):
        return f"Scan failed: {scan_data.get('error', 'Unknown error')}"
    
    lines = [
        f"Scan Report for {scan_data['final_url']}",
        f"Timestamp: {scan_data['timestamp']}",
        f"HTTP Status: {scan_data['status_code']}",
        "",
        f"Total Issues Found: {len(scan_data['issues'])}",
        ""
    ]
    
    if scan_data["issues"]:
        lines.append("Issues:")
        for issue in scan_data["issues"]:
            lines.append(f"  - [{issue['severity'].upper()}] {issue['description']}")
    else:
        lines.append("No critical issues found.")
    
    if scan_data.get("technology_stack"):
        lines.append("")
        lines.append("Technology Stack:")
        for tech, value in scan_data["technology_stack"].items():
            lines.append(f"  - {tech}: {value}")
    
    return "\n".join(lines)