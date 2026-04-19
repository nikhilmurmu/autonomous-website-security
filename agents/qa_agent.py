from crewai import Agent
from agents.llm_factory import get_llm
from tools.qa_tools import visual_regression_test_tool, generate_test_report_tool

def create_qa_agent():
    return Agent(
        role="Senior QA Engineer",
        goal="Validate that security fixes haven't broken any functionality.",
        backstory="""
        You are a meticulous QA engineer.
        Your process:
        1. Run visual regression tests using the 'Visual Regression Test' tool.
        2. Analyze the results.
        3. Generate a clear test report.
        4. Provide a PASS/FAIL recommendation.
        """,
        llm=get_llm(),
        tools=[visual_regression_test_tool, generate_test_report_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=4
    )