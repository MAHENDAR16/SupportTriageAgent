import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from src.config.settings import strip_openai_compat_suffix


def test_groq_connection():
    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")
    assert api_key, "GROQ_API_KEY not set -- copy .env.example to .env and fill it in"

    base_url = strip_openai_compat_suffix(
        os.environ.get("GROQ_API_URL", "https://api.groq.com/openai/v1")
    )
    llm = ChatGroq(
        api_key=api_key,
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        base_url=base_url,
    )
    response = llm.invoke("Reply with exactly: GROQ connection OK")
    assert "OK" in response.content
