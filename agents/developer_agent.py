from crewai import Agent, LLM
from config.settings import CODE_MODEL, OLLAMA_BASE_URL
from tools.developer_tools import generate_fix_plan_tool, create_backup_tool, apply_update_tool

def create_developer_agent():
    llm = LLM(
        model=f"ollama/{CODE_MODEL}",
        base_url=OLLAMA_BASE_URL,
        temperature=0.2
    )
    
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
        5. Communicate clearly what was done.
        """,
        llm=llm,
        tools=[generate_fix_plan_tool, create_backup_tool, apply_update_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )