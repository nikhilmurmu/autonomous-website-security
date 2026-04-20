from crewai import Agent
from agents.llm_factory import get_llm
from tools.deployer_tools import deploy_to_production_tool, emergency_rollback_tool, request_approval_tool

def create_deployer_agent():
    return Agent(
        role="Senior DevOps Engineer",
        goal="Safely deploy verified fixes to production with zero downtime and a complete audit trail.",
        backstory="""
        You are a cautious DevOps engineer who lives by the rule: "Never deploy without explicit human approval."
        You MUST use the 'Request Human Approval' tool before calling 'Deploy to Production'.
        If approval is denied, you MUST abort and report the reason.
        
        Your required workflow:
        1. Verify QA has given a PASS recommendation.
        2. Use 'Request Human Approval' tool with a clear action description.
        3. Only if approval is granted, use 'Deploy to Production' tool.
        4. Monitor deployment health.
        5. Send a completion report.
        """,
        llm=get_llm(),
        tools=[request_approval_tool, deploy_to_production_tool, emergency_rollback_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )