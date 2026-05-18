# agents/llm_factory.py
import os
import time
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

def get_llm(model_name: str = "groq/llama-3.1-8b-instant"):
    """
    Creates an LLM instance for Groq.
    Defaults to Llama 3.1 8B Instant – fast and free‑tier friendly.
    """
    time.sleep(2)  # small cooldown to stay under TPM limits
    return LLM(
        model=model_name,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1,
        max_tokens=1024
    )