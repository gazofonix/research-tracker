import openai, requests, os
from dotenv import load_dotenv
load_dotenv()  # Loads variables from .env into environment
HF_API_KEY = os.getenv("HF_API_KEY")

DEFAULT_PROMPT = """
You are an expert research assessor. For the following paper, score it from 1-10 in three categories:
1. Importance of the result in general; how important do you think is the result for the space of research we have chosen.
2. How well-known or expert the authors are on the topic. Do the authors have a high h-index on google scholar? Do they have other similar papers in prestiguous venues? Are they well-known? Or fron well-known universities?
3. Relevance to operation research scientists in the area of supply chain and transportation. Is the paper helping in solving large optimization or machine learning problems?
4. Relevance to additional user's interests (see below).

User interests: {user_interests}

Paper:
Title: {title}
Authors: {authors}
Abstract: {abstract}
"""

def assess_paper_qwen_hf(paper, user_interests, additional_prompt=None):
    prompt = DEFAULT_PROMPT.format(
        user_interests=user_interests,
        title=paper["title"],
        authors=", ".join(paper["authors"]),
        abstract=paper["summary"]
    )
    if additional_prompt:
        prompt += "\n" + additional_prompt

    # Choose a Qwen model (e.g., Qwen/Qwen1.5-14B-Chat)
    #model_id = "Qwen/Qwen1.5-14B-Chat"
    model_id = "Qwen/Qwen1.5-7B-Chat"
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 512}
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        # The output format may vary by model; adjust as needed
        return result[0]["generated_text"] if isinstance(result, list) else result["generated_text"]
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return "Error: Model not found. Please check the model ID."
        else:
            return f"HTTP Error: {str(e)}"