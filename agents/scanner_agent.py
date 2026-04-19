"""
Security Scanner Agent - Identifies vulnerabilities and outdated components.
"""
from crewai import Agent, LLM
from config.settings import DEFAULT_MODEL, OLLAMA_BASE_URL

def create_scanner_agent():
    llm = LLM(
        model=f"ollama/{DEFAULT_MODEL}",
        base_url=OLLAMA_BASE_URL,
        temperature=0.2
    )
    
    return Agent(
        role="Senior Security Scanner",
        goal="Thoroughly scan websites to identify security vulnerabilities, outdated software, and misconfigurations.",
        backstory="""
        You are a veteran security researcher with 15 years of experience.
        You methodically examine websites for:
        - Technology stack identification (WordPress, custom CMS, etc.)
        - Outdated plugin/theme versions with known CVEs
        - Missing security headers (HSTS, CSP, X-Frame-Options)
        - SSL/TLS certificate issues
        - Exposed sensitive files (.git, .env, backup files)
        
        You provide clear, actionable findings with severity ratings.
        """,
        llm=llm,
        allow_delegation=False,
        verbose=True
    )