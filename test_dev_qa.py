from crewai import Agent, Task, Crew, Process
from agents.developer_agent import create_developer_agent
from agents.qa_agent import create_qa_agent
from tools.scanner_direct import scan_website_direct, generate_scan_summary
import json

# Step 1: Run a scan (direct Python, no LLM)
scan_result = scan_website_direct("https://example.com")
scan_summary = generate_scan_summary(scan_result)

print("\n" + "="*60)
print("SCAN COMPLETED - Issues found:")
for issue in scan_result["issues"]:
    print(f"  - {issue['description']}")

# Step 2: Create agents
developer = create_developer_agent()
qa = create_qa_agent()

# Step 3: Create a task for the developer
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
    expected_output="A summary of the fix plan, backup creation, and update application.",
    agent=developer
)

# Step 4: Create a task for QA
qa_task = Task(
    description="""
    The Developer has applied a fix in staging for client 'test_client_001'.
    
    Your job:
    1. Run visual regression test using the 'Visual Regression Test' tool on these URLs:
       - https://staging-test_client_001.autosec.ai/
       - https://staging-test_client_001.autosec.ai/contact
    
    2. Generate a test report using the tool.
    
    3. Provide a final recommendation: PASS or FAIL.
    """,
    expected_output="Test report and PASS/FAIL recommendation.",
    agent=qa
)

# Step 5: Run the crew sequentially
crew = Crew(
    agents=[developer, qa],
    tasks=[dev_task, qa_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()
print("\n" + "="*60)
print("FULL PIPELINE RESULT:")
print(result)