import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import feedparser

ARXIV_CATEGORY_FEED_URL = "https://rss.arxiv.org/rss/cs.AI"

@dataclass
class PaperRecord:
    local_id: int
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    arxiv_timestamp: datetime
    llm_relevance_score: Optional[float] = None
    llm_explanation: Optional[str] = None
    user_relevance_score: Optional[float] = None
    user_explanation: Optional[str] = None
    author_lineup_score: Optional[float] = None  
    author_metrics: Optional[Dict[str, Any]] = None  

class PaperDatabase:
    def __init__(self, db_path: str = "research_papers.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS papers (
                    local_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arxiv_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    abstract TEXT,
                    arxiv_timestamp TIMESTAMP NOT NULL,
                    llm_relevance_score REAL,
                    llm_explanation TEXT,
                    user_relevance_score REAL,
                    user_explanation TEXT,
                    author_lineup_score REAL,  
                    author_metrics TEXT,
                    db_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS authors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY (paper_id) REFERENCES papers (local_id),
                    UNIQUE (paper_id, name)
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_arxiv_timestamp 
                ON papers(arxiv_timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_evaluated 
                ON papers(user_relevance_score)
            ''')
            conn.commit()

    # Core CRUD Operations
    def add_or_update_paper(self, arxiv_data: Dict):
        """
        Add/update paper using arXiv metadata
        Args:
            arxiv_data: Dictionary containing:
                - id: arXiv ID
                - title: Paper title
                - authors: List of authors
                - abstract: Paper abstract
                - updated: arXiv's last updated timestamp (isoformat)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            updated_time = datetime.fromisoformat(arxiv_data['updated'])
            
            cursor.execute('''
                INSERT OR REPLACE INTO papers (
                    arxiv_id, title, abstract, arxiv_timestamp,
                    llm_relevance_score, llm_explanation,
                    user_relevance_score, user_explanation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(arxiv_id) DO UPDATE SET
                    title = excluded.title,
                    abstract = excluded.abstract,
                    arxiv_timestamp = excluded.arxiv_timestamp,
                    db_updated = CURRENT_TIMESTAMP
            ''', (
                arxiv_data['id'],
                arxiv_data['title'],
                arxiv_data['abstract'],
                updated_time,
                arxiv_data.get('llm_relevance_score'),
                arxiv_data.get('llm_explanation'),
                arxiv_data.get('user_relevance_score'),
                arxiv_data.get('user_explanation')
            ))
            
            paper_id = cursor.lastrowid if not cursor.rowcount else cursor.execute(
                'SELECT local_id FROM papers WHERE arxiv_id = ?', 
                (arxiv_data['id'],)
            ).fetchone()[0]
            
            cursor.execute('DELETE FROM authors WHERE paper_id = ?', (paper_id,))
            for author in arxiv_data['authors']:
                cursor.execute('''
                    INSERT INTO authors (paper_id, name)
                    VALUES (?, ?)
                ''', (paper_id, author))
            
            conn.commit()

    # Fetch Operations
    def get_latest_arxiv_timestamp(self) -> Optional[datetime]:
        """Get the most recent arXiv updated timestamp from stored papers"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(arxiv_timestamp) FROM papers')
            result = cursor.fetchone()[0]
            return datetime.fromisoformat(result) if result else None

    def paper_exists(self, arxiv_id: str) -> bool:
        """Check if paper exists in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM papers WHERE arxiv_id = ?', (arxiv_id,))
            return cursor.fetchone() is not None

    @classmethod
    def fetch_from_arxiv(cls, db_path: str, days: int = 7, limit: int = 1000) -> Dict[str, Any]:
        """
        Enhanced version with better user feedback
        Returns dictionary with:
        - 'status': 'new_papers' | 'up_to_date' | 'error'
        - 'message': Human-readable status
        - 'stats': Database statistics
        - 'latest_timestamp': Most recent paper timestamp
        - 'new_papers_count': Count of new papers added (0 if none)
        """
        try:
            instance = cls(db_path)
            stats = instance.get_stats()
            latest = instance.get_latest_arxiv_timestamp()
            
            if not latest:  # First run
                report = instance._fetch_and_store_papers(days, limit)
                return {
                    'status': 'new_papers',
                    'message': f"Initial import: Added {report['new']} papers",
                    'stats': stats,
                    'latest_timestamp': report['latest_after'],
                    'new_papers_count': report['new']
                }
            
            # Subsequent runs
            report = instance._fetch_and_store_papers(days, limit)
            
            if report['new'] > 0:
                return {
                    'status': 'new_papers',
                    'message': f"Added {report['new']} new papers (latest: {report['latest_after']})",
                    'stats': stats,
                    'latest_timestamp': report['latest_after'],
                    'new_papers_count': report['new']
                }
            else:
                return {
                    'status': 'up_to_date',
                    'message': f"Database up-to-date. Latest paper: {latest}",
                    'stats': stats,
                    'latest_timestamp': latest.isoformat(),
                    'new_papers_count': 0
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'stats': {},
                'latest_timestamp': None,
                'new_papers_count': 0
            }
  
    def _fetch_and_store_papers(self, days: int = 7, limit: int = 1000) -> Dict[str, Any]:
        """Internal method that implements the actual workflow"""
        report = {
            'latest_before': self.get_latest_arxiv_timestamp(),
            'fetched': 0,
            'new': 0,
            'latest_after': None  # Initialize with None
        }
        
        try:
            cutoff = report['latest_before'] or (datetime.utcnow() - timedelta(days=days))
            papers = self._fetch_arxiv_papers(cutoff)[:limit]
            report['fetched'] = len(papers)
            
            new_papers = [p for p in papers if not self.paper_exists(p['id'])]
            report['new'] = len(new_papers)
            
            for paper in new_papers:
                self.add_or_update_paper(paper)
            
            if new_papers:
                report['latest_after'] = max(datetime.fromisoformat(p['updated']) for p in new_papers)
            return report
            
        except Exception as e:
            report['error'] = str(e)
            return report

    def _fetch_arxiv_papers(self, cutoff: datetime) -> List[Dict]:
        """Internal arXiv API fetcher"""
        feed = feedparser.parse(ARXIV_CATEGORY_FEED_URL)
        papers = []
        
        for entry in feed.entries:
            if not hasattr(entry, 'published_parsed'):
                continue
                
            updated = datetime(*entry.updated_parsed[:6])
            if updated <= cutoff:
                continue
                
            papers.append({
                'id': entry.id.split('/')[-1],
                'title': entry.title,
                'authors': [a.name for a in entry.authors],
                'abstract': entry.summary,
                'updated': updated.isoformat()
            })
        
        return sorted(papers, key=lambda x: x['updated'], reverse=True)

    # Evaluation Management
    def get_unevaluated_papers(self, limit: int = 10) -> List[PaperRecord]:
        """
        Get oldest papers without user evaluation
        Args:
            limit: Maximum number of papers to return
        Returns:
            List of PaperRecord objects sorted by oldest first
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM papers 
                WHERE user_relevance_score IS NULL
                ORDER BY arxiv_timestamp ASC
                LIMIT ?
            ''', (limit,))
            
            return [self._row_to_paper_record(row) for row in cursor.fetchall()]

    def update_author_evaluation(self, arxiv_id: str, score: float, metrics: dict) -> bool:
        """Update author evaluation fields"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE papers
                SET author_lineup_score = ?,
                    author_metrics = ?,
                    db_updated = CURRENT_TIMESTAMP
                WHERE arxiv_id = ?
            ''', (score, json.dumps(metrics), arxiv_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_user_evaluation(self, arxiv_id: str, score: float, explanation: str) -> bool:
        """
        Update user evaluation for a specific paper
        Args:
            arxiv_id: arXiv identifier of the paper
            score: User relevance score (1-10)
            explanation: User's explanation
        Returns:
            True if update was successful, False if paper not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE papers
                SET user_relevance_score = ?,
                    user_explanation = ?,
                    db_updated = CURRENT_TIMESTAMP
                WHERE arxiv_id = ?
            ''', (score, explanation, arxiv_id))
            conn.commit()
            return cursor.rowcount > 0

    # Reporting
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute('SELECT COUNT(*) FROM papers')
            stats['total_papers'] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM papers 
                WHERE user_relevance_score IS NOT NULL
            ''')
            stats['user_evaluated'] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM papers 
                WHERE llm_relevance_score IS NOT NULL
            ''')
            stats['llm_evaluated'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT MIN(arxiv_timestamp) FROM papers')
            stats['oldest_paper'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT MAX(arxiv_timestamp) FROM papers')
            stats['newest_paper'] = cursor.fetchone()[0]
            
            return stats

    # Utility Methods
    def _row_to_paper_record(self, row) -> PaperRecord:
        """Convert database row to PaperRecord object"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name FROM authors
                WHERE paper_id = ?
                ORDER BY id
            ''', (row['local_id'],))
            authors = [author_row[0] for author_row in cursor.fetchall()]
            
            return PaperRecord(
                local_id=row['local_id'],
                arxiv_id=row['arxiv_id'],
                title=row['title'],
                authors=authors,
                abstract=row['abstract'],
                arxiv_timestamp=datetime.fromisoformat(row['arxiv_timestamp']),
                llm_relevance_score=row['llm_relevance_score'],
                llm_explanation=row['llm_explanation'],
                user_relevance_score=row['user_relevance_score'],
                user_explanation=row['user_explanation']
            )

    def to_excel(self, output_path: str = "papers_export.xlsx"):
        """Export database to Excel file"""
        with sqlite3.connect(self.db_path) as conn:
            # Include all columns explicitly
            papers_df = pd.read_sql('''
                SELECT p.*, 
                    GROUP_CONCAT(a.name, ', ') as authors
                FROM papers p
                LEFT JOIN authors a ON p.local_id = a.paper_id
                GROUP BY p.local_id
                ORDER BY p.arxiv_timestamp DESC
            ''', conn)
            
            # Ensure all expected columns exist
            expected_cols = ['arxiv_id', 'title', 'authors', 'abstract',
                            'arxiv_timestamp', 'author_lineup_score', 
                            'author_metrics', 'db_updated']
            for col in expected_cols:
                if col not in papers_df.columns:
                    papers_df[col] = None
                    
            papers_df.to_excel(output_path, index=False)

        """Debug function to check current schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(papers)")
            columns = cursor.fetchall()
            print("Current schema columns:")
            for col in columns:
                print(f"{col[1]} ({col[2]})")