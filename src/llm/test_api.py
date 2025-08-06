import requests, os
from dotenv import load_dotenv
load_dotenv()  # Loads variables from .env into environment
HF_API_KEY = os.getenv("HF_API_KEY")

MODEL_ID = "Qwen/Qwen1.5-0.5B-Chat"  # Start with a smaller model

import requests
import os
import time
from dotenv import load_dotenv

# Configuration
load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")
MODEL_ID = "Qwen/Qwen1.5-0.5B-Chat"
MODEL_OPTIONS = [
    "Qwen/Qwen3-Reranker-0.6B",  # Primary option
    "Qwen/Qwen3-1.7B",  # Fallback option 1
    "Qwen/Qwen3-32B"  # Fallback option 2
]
MAX_RETRIES = 2
RETRY_DELAY = 1
TIMEOUT = 8

def find_available_model():
    """Check which models are available from our options list.
    
    Returns:
        tuple: (available_model_id, status_message)
    """
    if not HF_API_KEY:
        return None, "API key not found in environment variables"
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    for model_id in MODEL_OPTIONS:
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    f"https://api-inference.huggingface.co/models/{model_id}",
                    headers=headers,
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    return model_id, f"Model {model_id} is available"
                elif response.status_code == 404:
                    break  # Try next model
                elif response.status_code == 401:
                    return None, "Invalid API key or unauthorized access"
                
                # For other status codes, retry
                time.sleep(RETRY_DELAY)
                    
            except requests.exceptions.RequestException:
                time.sleep(RETRY_DELAY)
                continue
    
    return None, "No available models from the options list"


def api_test_with_fallback():
    """Test API with automatic fallback to available models."""
    print("\nRunning API health check...")
    
    # 1. Verify API key
    if not HF_API_KEY:
        print("❌ Critical: No HF_API_KEY found in environment")
        return False, None
    
    print("✓ API key configuration valid")
    
    # 2. Find available model
    model_id, status_msg = find_available_model()
    if not model_id:
        print(f"❌ {status_msg}")
        return False, None
    
    print(f"✓ Using model: {model_id}")
    
    # 3. Test API functionality
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": "Explain quantum computing in simple terms.",
        "parameters": {"max_new_tokens": 50}  # Smaller for testing
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{model_id}",
                headers=headers,
                json=payload,
                timeout=TIMEOUT
            )

            if response.status_code == 200:
                print("✓ API test successful")
                print(f"Sample response: {response.json()}")
                return True, model_id
            
            error_msg = f"API error {response.status_code}"
            if response.text:
                error_msg += f": {response.text[:100]}"  # Show first 100 chars
            print(f"Attempt {attempt+1} failed - {error_msg}")
            time.sleep(RETRY_DELAY)
            
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1} failed - {str(e)}")
            time.sleep(RETRY_DELAY)
    
    print("❌ API test failed after retries")
    return False, model_id

def check_api_health():
    """Comprehensive API health check with detailed reporting."""
    success, active_model = api_test_with_fallback()
    if success:
        print(f"✅ API is operational using model: {active_model}")
        # Proceed with your application logic
    else:
        print("❌ API is not ready - check errors above")
        # Implement fallback behavior

