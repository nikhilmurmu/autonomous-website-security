from crewai import Task, Crew, Process
from agents.developer_agent import create_developer_agent
from tools.scanner_direct import scan_website_direct, generate_scan_summary, create_issue_summary
from memory.vector_store import get_memory_store
from tools.qa_tools import visual_regression_test_tool, generate_test_report_tool
from tools.deployer_tools import deploy_to_production_tool
import json
from datetime import datetime

# Step 1: Scan the website
scan_result = scan_website_direct("http://autosec-test.local")
scan_summary = generate_scan_summary(scan_result)
issue_summary = create_issue_summary(scan_result)

print("\n" + "="*60)
print("SCAN COMPLETED - Issues found:")
for issue in scan_result["issues"]:
    print(f"  - {issue['description']}")

# Step 1.5: Memory lookup
memory = get_memory_store()
similar_fixes = memory.find_similar_fixes(issue_summary, n_results=2)
context_text = ""
if similar_fixes:
    context_text = "Past similar fixes found in memory:\n"
    for fix in similar_fixes:
        fix_plan = fix['fix_plan']
        context_text += f"- Issue: {fix['issue_summary'][:100]}...\n"
        context_text += f"  Recommended action: {fix_plan.get('recommended_action', 'unknown')}\n\n"
else:
    context_text = "No past similar fixes found in memory."

print("\n" + "="*60)
print("MEMORY CONTEXT:")
print(context_text)

# Step 2: Create Developer agent (LLM-based)
developer = create_developer_agent()

# Step 3: Developer task with memory context
dev_task = Task(
    description=f"""
A security scan found the following issues on the client website:
{scan_summary}

Client ID: autosec-test

MEMORY CONTEXT (use this if helpful):
{context_text}

Your job:
1. Use 'Generate Fix Plan' tool for the first issue (missing security headers).
2. Use 'Create Backup' tool for client 'autosec-test'.
3. Use 'Apply Update' tool to add security headers (simulated).
4. Use 'WP Add Security Headers' tool for client 'autosec-test' to actually patch the site.

Provide a summary of actions taken.
""",
    expected_output="Summary of fix plan, backup creation, update application, and real security header patch.",
    agent=developer
)

# Create a crew with only the Developer
crew = Crew(
    agents=[developer],
    tasks=[dev_task],
    process=Process.sequential,
    verbose=True
)

print("\n" + "="*60)
print("STARTING DEVELOPER (LLM-based)")
print("="*60)

dev_result = crew.kickoff()
print("\n" + "="*60)
print("Developer completed.")
print("Result:", dev_result)

# Step 4: QA – Direct Python, no LLM
print("\n" + "="*60)
print("RUNNING QA TESTS (direct Python)")
print("="*60)

qa_urls = [
    "https://staging-autosec-test.autosec.ai/",
    "https://staging-autosec-test.autosec.ai/contact"
]

qa_test_result = visual_regression_test_tool.run(
    client_id="autosec-test",
    urls_to_test=qa_urls
)

print("Visual regression test completed.")
print("Raw result:", qa_test_result)

# Parse the result
try:
    qa_data = json.loads(qa_test_result)
    overall_status = qa_data.get("overall_status", "fail")
except:
    overall_status = "fail"

print(f"Overall QA status: {overall_status.upper()}")

# Step 5: Human approval and deployment (direct Python)
print("\n" + "="*60)
print("⏸️  HUMAN APPROVAL REQUIRED")
print("="*60)
print(f"QA has completed with status: {overall_status.upper()}")
print("Ready to deploy security_headers_fix_v1 to production for autosec-test.")

if overall_status == "pass":
    while True:
        response = input("Approve? (yes/no): ").strip().lower()
        if response in ["yes", "y"]:
            print("✅ Approved. Deploying...\n")
            deploy_result = deploy_to_production_tool.run(
                client_id="autosec-test",
                deployment_package="security_headers_fix_v1"
            )
            print("Deployment result:", deploy_result)
            break
        elif response in ["no", "n"]:
            print("❌ Denied. Deployment cancelled.\n")
            deploy_result = "Deployment cancelled by user."
            break
        else:
            print("Please type 'yes' or 'no'")
else:
    print("❌ QA did not pass. Deployment cannot proceed.")
    deploy_result = "Deployment skipped due to QA failure."

# Step 6: Store fix plan in memory
fix_plan_to_store = {
    "issue_type": "missing_security_headers",
    "recommended_action": "add_security_header",
    "headers_affected": ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options",
                         "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy"],
    "deployment_status": "success" if "deployed" in str(deploy_result).lower() else "cancelled"
}
memory.store_fix(
    issue_summary=issue_summary,
    fix_plan=fix_plan_to_store,
    metadata={"client_id": "autosec-test", "timestamp": datetime.now().isoformat()}
)
print("\n" + "="*60)
print("✅ Fix plan stored in memory for future learning.")
print("="*60)