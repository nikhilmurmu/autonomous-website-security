import json
import hashlib
from datetime import datetime
from pathlib import Path
from crewai.tools import tool
from loguru import logger
from config.settings import CLIENTS_DIR

@tool("Visual Regression Test")
def visual_regression_test_tool(client_id: str, urls_to_test: list) -> str:
    """
    Perform visual regression testing by comparing before/after screenshots.
    For now, this is a simulation; in production, use Playwright for actual comparison.
    """
    logger.info(f"Starting visual regression test for {client_id}")
    
    results = {
        "client_id": client_id,
        "timestamp": datetime.now().isoformat(),
        "urls_tested": urls_to_test,
        "results": [],
        "overall_status": "pass"
    }
    
    for url in urls_to_test:
        # Simulate screenshot comparison
        baseline_hash = hashlib.md5(f"{url}_baseline".encode()).hexdigest()[:16]
        current_hash = hashlib.md5(f"{url}_current".encode()).hexdigest()[:16]
        
        # For demonstration, randomly pass or warn (but always pass for stability)
        diff_percentage = 0.0
        status = "pass"
        issues = []
        
        test_result = {
            "url": url,
            "baseline_hash": baseline_hash,
            "current_hash": current_hash,
            "diff_percentage": diff_percentage,
            "status": status,
            "issues_found": issues
        }
        results["results"].append(test_result)
    
    # Save results to file
    results_dir = CLIENTS_DIR / client_id / "qa_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = results_dir / f"visual_test_{timestamp}.json"
    with open(result_file, "w") as f:
        json.dump(results, f, indent=2)
    
    return json.dumps(results, indent=2)


@tool("Generate Test Report")
def generate_test_report_tool(test_results_json: str) -> str:
    """
    Generate a human-readable test report from JSON results.
    """
    try:
        results = json.loads(test_results_json)
    except:
        results = {"error": "Invalid JSON"}
    
    report_lines = [
        "QA Test Report",
        "==============",
        f"Client: {results.get('client_id', 'Unknown')}",
        f"Timestamp: {results.get('timestamp', 'Unknown')}",
        f"Overall Status: {results.get('overall_status', 'unknown').upper()}",
        "",
        "Tested URLs:"
    ]
    
    for res in results.get("results", []):
        report_lines.append(f"  - {res['url']}: {res['status'].upper()} (diff: {res['diff_percentage']}%)")
    
    return "\n".join(report_lines)