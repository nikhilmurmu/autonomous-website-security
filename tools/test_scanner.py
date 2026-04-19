from crewai import Agent, Task, Crew, Process, LLM
from tools.scanner_tools import scan_website_tool, check_wordpress_version_tool
from config.settings import OLLAMA_BASE_URL, DEFAULT_MODEL

llm = LLM(
    model=f"ollama/{DEFAULT_MODEL}",
    base_url=OLLAMA_BASE_URL
)

scanner = Agent(
    role="Security Scanner",
    goal="Scan a test website and report findings",
    backstory="You are an expert security researcher.",
    llm=llm,
    tools=[scan_website_tool, check_wordpress_version_tool],
    verbose=True
)

task = Task(
    description="Scan https://example.com and report any security issues found.",
    expected_output="A summary of security issues with severity ratings.",
    agent=scanner
)

crew = Crew(
    agents=[scanner],
    tasks=[task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()
print("\n" + "="*50)
print("SCAN RESULT:")
print(result)