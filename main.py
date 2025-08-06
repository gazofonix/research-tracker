from src.arxiv.rss_fetcher import fetch_papers
from src.llm.assessor import assess_paper_qwen_hf
from src.llm.test_api import check_api_health

def main():
    #check_api_health()
    papers = fetch_papers()
    # Assessment UI
    assess = input("Would you like to assess a paper with the LLM agent? (y/n): ").strip().lower()
    if assess == "y":
        paper_idx = int(input(f"Select paper number (1-{len(papers)}): ")) - 1
        #user_interests = input("Describe your research interests (for relevance scoring): ")
        user_interests = "operation research, supply chain, transportation, optimization, machine learning"
        use_custom = input("Would you like to provide a custom prompt or chat with the agent? (y/n): ").strip().lower()
        custom_prompt = None
        if use_custom == "y":
            print("Enter your custom prompt. Use {title}, {authors}, {abstract}, {user_interests} as placeholders.")
            custom_prompt = input("Custom prompt: ")
        assessment = assess_paper_qwen_hf(
            papers[paper_idx],
            user_interests,
            additional_prompt=custom_prompt
        )
        print("\n--- Assessment Result ---")
        print(assessment)

if __name__ == "__main__":
    main()