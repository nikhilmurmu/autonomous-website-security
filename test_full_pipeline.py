from crewai import Agent, Task, Crew, Process
from agents.developer_agent import create_developer_agent
from agents.qa_agent import create_qa_agent
from agents.deployer_agent import create_deployer_agent
from tools.scanner_direct import scan_website_direct, generate_scan_summary

# Step 1: Scan the website (direct Python, no LLM)
scan_result = scan_website_direct("https://example.com")
scan_summary = generate_scan_summary(scan_result)

print("\n" + "="*60)
print("SCAN COMPLETED - Issues found:")
for issue in scan_result["issues"]:
    print(f"  - {issue['description']}")

# Step 2: Create agents
developer = create_developer_agent()
qa = create_qa_agent()
deployer = create_deployer_agent()

# Step 3: Developer task
dev_task = Task(
    description=f"""
    A security scan found the following issues on the client website:
    {scan_summary}
    
    Client ID: test_client_001
    
    Your job:
    1. Use 'Generate Fix Plan' tool for the first issue (missing security headers).
    2. Use 'Create Backup' tool for client 'test_client_001'.
    3. Use 'Apply Update' tool to add security headers (simulated).
    
    Provide a summary of actions taken.
    """,
    expected_output="Summary of fix plan, backup creation, and update application.",
    agent=developer
)

# Step 4: QA task
qa_task = Task(
    description="""
    The Developer has applied a fix in staging for client 'test_client_001'.
    
    Your job:
    1. Run visual regression test using the 'Visual Regression Test' tool on these URLs:
       - https://staging-test_client_001.autosec.ai/
       - https://staging-test_client_001.autosec.ai/contact
    
    2. Generate a test report.
    
    3. Provide a final recommendation: PASS or FAIL.
    """,
    expected_output="Test report and PASS/FAIL recommendation.",
    agent=qa,
    output_file="qa_result.txt"
)

# Step 5: Deployer task with HUMAN APPROVAL
deployer_task = Task(
    description="""
    The QA engineer has completed testing for client 'test_client_001'.
    The QA recommendation is PASS.
    
    Your EXACT required workflow:
    1. Use the 'Request Human Approval' tool with action_description="Deploy security_headers_fix_v1 to production for test_client_001".
    2. If the tool returns 'approved', THEN use the 'Deploy to Production' tool with client_id='test_client_001' and deployment_package='security_headers_fix_v1'.
    3. If the tool returns 'denied', do NOT deploy and instead report that deployment was cancelled.
    
    DO NOT skip the approval step. DO NOT deploy without approval.
    """,
    expected_output="Deployment confirmation or cancellation report.",
    agent=deployer
)

# Step 6: Create and run the crew
crew = Crew(
    agents=[developer, qa, deployer],
    tasks=[dev_task, qa_task, deployer_task],
    process=Process.sequential,
    verbose=True
)

print("\n" + "="*60)
print("STARTING FULL PIPELINE WITH HUMAN APPROVAL")
print("="*60)

result = crew.kickoff()

print("\n" + "="*60)
print("FULL PIPELINE RESULT:")
print(result)
print("="*60)
