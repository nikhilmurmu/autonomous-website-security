import requests
import json
import re
from datetime import datetime
from crewai.tools import tool
from loguru import logger

@tool("Scan Website")
def scan_website_tool(url: str) -> str:
    """
    Scan a website to identify technology stack, headers, and basic security posture.
    """
    logger.info(f"Starting security scan of {url}")
    
    results = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "technology_stack": {},
        "security_headers": {},
        "issues": [],
        "warnings": []
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
        
        # Check security headers
        security_headers = [
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Permissions-Policy"
        ]
        
        for header in security_headers:
            if header not in response.headers:
                results["issues"].append({
                    "type": "missing_header",
                    "header": header,
                    "severity": "medium",
                    "description": f"Missing security header: {header}"
                })
            else:
                results["security_headers"][header] = response.headers[header]
        
        # Detect WordPress
        if "wp-content" in response.text or "wp-includes" in response.text:
            results["technology_stack"]["cms"] = "WordPress"
            version_match = re.search(r'WordPress\s+([\d.]+)', response.text)
            if version_match:
                results["technology_stack"]["wordpress_version"] = version_match.group(1)
            else:
                gen_match = re.search(r'<meta name="generator" content="WordPress ([\d.]+)"', response.text)
                if gen_match:
                    results["technology_stack"]["wordpress_version"] = gen_match.group(1)
        
        # Check for exposed sensitive files
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
        
        results["scan_successful"] = True
        
    except Exception as e:
        results["error"] = str(e)
        results["scan_successful"] = False
    
    return json.dumps(results, indent=2)

@tool("Check WordPress Version")
def check_wordpress_version_tool(version: str) -> str:
    """Check if a WordPress version has known vulnerabilities."""
    # In production, you'd query WPScan API. Here's a simulated check.
    latest = "6.5.2"
    result = {
        "current_version": version,
        "latest_version": latest,
        "is_latest": version >= latest,
        "vulnerabilities": []
    }
    # Simulate known vulnerable versions
    vulnerable = {"6.4.0": ["CVE-2023-xyz - XSS"], "6.3.2": ["CVE-2023-abc - SQLi"]}
    if version in vulnerable:
        result["vulnerabilities"] = vulnerable[version]
        result["severity"] = "high"
    elif version < latest:
        result["severity"] = "medium"
    else:
        result["severity"] = "low"
    return json.dumps(result, indent=2)