# test_integration.py
import pytest
from datetime import datetime
from paper_database import PaperDatabase
from author_lineup_evaluator import AuthorLineupEvaluator

@pytest.fixture
def test_db():
    """Fixture for temporary in-memory database"""
    db = PaperDatabase(":memory:")
    yield db
    # Teardown happens automatically for in-memory DB

def test_author_evaluation_flow(test_db):
    """End-to-end test of author evaluation pipeline"""
    # 1. Add test paper
    test_data = {
        'id': '1706.03762',
        'title': 'Attention Is All You Need',
        'authors': ['Test Author 1', 'Test Author 2'],
        'abstract': 'Test abstract',
        'updated': datetime.utcnow().isoformat()
    }
    test_db.add_or_update_paper(test_data)
    
    # 2. Verify paper exists without evaluation
    papers = test_db.get_unevaluated_papers()
    assert len(papers) == 1
    assert papers[0].author_lineup_score is None
    
    # 3. Run evaluation
    evaluator = AuthorLineupEvaluator()
    updated, stats = evaluator.batch_evaluate(papers)
    
    # 4. Verify results
    assert len(updated) == 1
    assert updated[0].author_lineup_score is not None
    assert isinstance(updated[0].author_metrics, dict)
    assert stats['total_evaluated'] == 1
    
    # 5. Verify database update
    test_db.update_author_evaluation(
        updated[0].arxiv_id,
        updated[0].author_lineup_score,
        updated[0].author_metrics
    )
    updated_paper = test_db.get_unevaluated_papers()
    assert len(updated_paper) == 0  # Should now be evaluated