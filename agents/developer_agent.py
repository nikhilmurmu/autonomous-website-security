from crewai import Agent
from agents.llm_factory import get_llm
from tools.developer_tools import generate_fix_plan_tool, create_backup_tool, apply_update_tool

def create_developer_agent():
    return Agent(
        role="Senior Security Developer",
        goal="Create safe, tested fixes for identified security vulnerabilities.",
        backstory="""
        You are a senior developer specializing in security patches.
        Your workflow:
        1. Analyze the issue provided by the Scanner.
        2. Use 'Generate Fix Plan' tool to create a structured approach.
        3. Use 'Create Backup' tool before any changes.
        4. Use 'Apply Update' tool to implement the fix in staging.
        """,
        llm=get_llm(),
        tools=[generate_fix_plan_tool, create_backup_tool, apply_update_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )