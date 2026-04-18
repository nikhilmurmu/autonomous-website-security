from crewai import Agent, Task, Crew, Process, LLM

llm = LLM(
    model="ollama/llama3.2:3b",
    base_url="http://localhost:11434"
)

test_agent = Agent(
    role="Tester",
    goal="Say hello",
    backstory="You are a test agent.",
    llm=llm,
    verbose=True
)

test_task = Task(
    description="Say 'Hello! I am an AI agent running locally on your laptop.'",
    expected_output="A greeting",
    agent=test_agent
)

crew = Crew(
    agents=[test_agent],
    tasks=[test_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()
print("\n" + "="*50)
print("RESULT:", result)
print("="*50)