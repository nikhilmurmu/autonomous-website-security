from crewai import Agent, Task, Crew, Process, LLM
from tools.scanner_tools import scan_website_tool
from config.settings import OLLAMA_BASE_URL, DEFAULT_MODEL

llm = LLM(
    model=f"ollama/{DEFAULT_MODEL}",
    base_url=OLLAMA_BASE_URL,
    temperature=0.0  # deterministic
)

scanner = Agent(
    role="Security Scanner",
    goal="Use the 'Scan Website' tool exactly once and return its complete JSON output without modification.",
    backstory="You are a security tool wrapper. Your only job is to call the tool and return the result.",
    llm=llm,
    tools=[scan_website_tool],
    verbose=True,
    allow_delegation=False,
    max_iter=2  # Force quick exit
)

task = Task(
    description="""
    Call the 'Scan Website' tool with url='https://example.com'.
    DO NOT call any other tool.
    DO NOT summarize, analyze, or add commentary.
    Return the exact JSON output from the tool as your final answer.
    """,
    expected_output="Raw JSON output from the Scan Website tool.",
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
print("RAW SCAN OUTPUT:")
print(result)