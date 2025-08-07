import openai, requests, os
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()  # Loads variables from .env into environment
OPENAI_KEY = os.getenv("OPENAI_KEY")
OPENAI_MODEL_ID = "gpt-4o"

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

def assess_paper_openai(paper, user_interests, additional_prompt=None):
    """OpenAI assessment function """
    prompt = DEFAULT_PROMPT.format(
        user_interests=user_interests,
        title=paper["title"],
        authors=", ".join(paper["authors"]),
        abstract=paper["summary"]
    )
    if additional_prompt:
        prompt += "\n" + additional_prompt

    try:
        client = OpenAI(api_key=OPENAI_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL_ID,
            messages=[
                {"role": "system", "content": "You are a research paper assessment assistant. Your goal is to determine a relevance score for each paper and produce an explanation for the score."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=512,
            temperature=0.7
        )
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"OpenAI Error: {str(e)}")
        return None

def assess_papers(papers):
    """Assess a list of papers using OpenAI"""
    paper_idx = int(input(f"Select paper number (1-{len(papers)}): ")) - 1
    user_interests = "operation research, supply chain, transportation, optimization, machine learning"
    assessment = assess_paper_openai(
        papers[paper_idx],
        user_interests,
        additional_prompt=None
    )
    if assessment:
        return assessment
    else:
        print("Assessment failed for all providers")
        return None


"""def assess_paper_qwen_hf(paper, user_interests, additional_prompt=None):
    prompt = DEFAULT_PROMPT.format(
        user_interests=user_interests,
        title=paper["title"],
        authors=", ".join(paper["authors"]),
        abstract=paper["summary"]
    )
    if additional_prompt:
        prompt += "\n" + additional_prompt

    # Choose a Qwen model (e.g., Qwen/Qwen1.5-14B-Chat)
    model_id = "Qwen/Qwen1.5-14B-Chat"
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
            return f"HTTP Error: {str(e)}"""
