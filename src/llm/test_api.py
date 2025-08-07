import openai, requests, os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()  # Loads variables from .env into environment
OPENAI_KEY = os.getenv("OPENAI_KEY")
OPENAI_MODEL_ID = "gpt-4o"  # Default model

def test_openai():
    """Test OpenAI API with a simple prompt"""
    try:
        client = OpenAI(api_key=OPENAI_KEY)
        response = client.responses.create(
            model=OPENAI_MODEL_ID,
            instructions="You are a drunk pirate",
            input="Say hello"
        )
        print(response.output_text)
        return True
    except Exception as e:
        print(f"🚨 OpenAI API failed: {str(e)}")
        return False

def check_api_health():
    """Check if the OpenAI API is healthy"""
    print("Checking OpenAI API health...")
    if test_openai():
        print("✅ OpenAI API is healthy.")
    else:
        print("🚨 OpenAI API is not healthy. Please check your API key and network connection.")
        exit(1)  # Exit if the API is not healthy