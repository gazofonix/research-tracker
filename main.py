from src.arxiv.paper_database import PaperDatabase
from src.arxiv.author_lineup_evaluator import AuthorLineupEvaluator
from src.llm.assessor import assess_papers
from src.llm.test_api import check_api_health
import os, time


def main():
    #check_api_health() # Activate this to ensure OpenAPI is healthy before using LLM agent

    db = PaperDatabase("research_papers.db")
    print(f"Using database at: {os.path.abspath(db.db_path)}")
    fetch_result  = PaperDatabase.fetch_from_arxiv("research_papers.db", days=7, limit=1000)
    print("\n=== arXiv Fetch Report ===")
    print(f"Database contains {fetch_result['stats'].get('total_papers', 0)} papers")
    print(f"Last paper timestamp: {fetch_result['latest_timestamp']}")   
    if fetch_result['status'] == 'up_to_date':
        print("No new papers found - you're up-to-date!")
    elif fetch_result['status'] == 'new_papers':
        print(f"Added {fetch_result['new_papers_count']} new papers to database")

    # Test with known author
    # ===== TEMPORARY TEST CODE =====
    print("\n=== Running Author Evaluation Test ===")
    evaluator = AuthorLineupEvaluator()
    
    test_cases = [
        ("Yann LeCun"),
        ("Andrew Ng")
    ]
    
    for author in test_cases:
        print(f"\nTesting {author}:")
        result = evaluator.get_author_metrics(author)
        print(f"Results: {result}")
        time.sleep(34)  # Be extra careful during tests
    
    # ===== END TEMPORARY TEST CODE =====

    exit(0)
    
    # Evaluate papers
    print("\n=== Author Lineup Evaluation ===")
    unevaluated = db.get_unevaluated_papers()
    updated_papers, stats = evaluator.batch_evaluate(unevaluated)
    for paper in updated_papers:
        db.update_author_evaluation(
            arxiv_id=paper.arxiv_id,
            score=paper.author_lineup_score,
            metrics=paper.author_metrics
        )
    evaluator.print_stats(stats)
    
    db.to_excel("research_papers.xlsx")
    print("\nExported papers to research_papers.xlsx")



    #assessment = assess_papers(papers)
    #print("\n--- Assessment Result ---")
    #print(assessment)
    db = PaperDatabase("research_papers.db")
    report = PaperDatabase.fetch_from_arxiv("research_papers.db", days=7, limit=1000)
    print(f"Fetched {report['new']} new papers out of {report['fetched']} available")
    
    unevaluated = db.get_unevaluated_papers(limit=5)
    for paper in unevaluated:
        # Evaluation logic...
        db.update_user_evaluation(paper.arxiv_id, score, explanation)
    # Get papers for human evaluation
    unevaluated = db.get_unevaluated_papers(limit=5)
    for paper in unevaluated:
        print(f"\nPaper: {paper.title}")
        print(f"Abstract: {paper.abstract[:200]}...")
        # Present to user for evaluation...
        
        # Store evaluation
        db.update_user_evaluation(
            arxiv_id=paper.arxiv_id,
            score=8.5,
            explanation="Highly relevant to our research focus"
        )



if __name__ == "__main__":
    main()