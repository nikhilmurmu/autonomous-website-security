# agents/llm_factory.py
import os
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

def get_llm(model_name: str = "groq/llama-3.3-70b-versatile"):
    """
    Creates an LLM instance for Groq.
    Defaults to Llama 3.3 70B, which is fast and highly capable.
    """
    return LLM(
        model=model_name,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1
    )