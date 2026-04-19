from crewai import Agent
from agents.llm_factory import get_llm
from tools.scanner_tools import scan_website_tool, check_wordpress_version_tool

def create_scanner_agent():
    return Agent(
        role="Senior Security Scanner",
        goal="Thoroughly scan websites to identify security vulnerabilities, outdated software, and misconfigurations.",
        backstory="""
        You are a veteran security researcher with 15 years of experience.
        You methodically examine websites for:
        - Technology stack identification
        - Outdated plugin/theme versions
        - Missing security headers
        - SSL/TLS certificate issues
        - Exposed sensitive files
        """,
        llm=get_llm(),
        tools=[scan_website_tool, check_wordpress_version_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )