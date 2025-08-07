from __future__ import annotations
from typing import List, Dict, Optional, Tuple, DefaultDict
import time, random, logging
import numpy as np
from collections import Counter, defaultdict
from scholarly import scholarly, ProxyGenerator

class AuthorLineupEvaluator:
    def __init__(self, google_scholar_enabled: bool = True):
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = {
            'prestige_threshold': 30,  # h-index threshold for prestigious authors
            'ideal_team_size': 5,
            'max_team_size': 10,
            'weights': {
                'prestige': 0.4,
                'balance': 0.3,
                'industry': 0.2,
                'size_penalty': -0.1  # Negative because it's a penalty
            }
        }
        self._google_scholar_enabled = google_scholar_enabled
        
        # Rate limiting
        self._last_request_time = 0
        self._base_delay = random.uniform(30, 60)  # 30-60 second base delay
        self._current_delay = self._base_delay
        
        # Retry configuration
        self._max_retries = 3
        self._timeout = 30  # seconds
        
        # Proxy initialization
        self._init_proxy()

    
        """Initialize proxy with automatic fallback"""
        try:
            pg = ProxyGenerator()
            success = pg.FreeProxies()
            if success:
                scholarly.use_proxy(pg)
                self.logger.info("Using free proxies")
            else:
                scholarly.use_proxy(None)
                self.logger.warning("Failed to get free proxies, continuing without")
        except Exception as e:
            scholarly.use_proxy(None)
            self.logger.error(f"Proxy initialization failed: {str(e)}")

    def _init_proxy(self):
        """Initialize proxy with improved error handling"""
        try:
            # Try to use Tor or free proxies first
            pg = ProxyGenerator()
            
            # Attempt 1: Try Tor if available
            try:
                pg.Tor_External(tor_sock_port=9050, tor_control_port=9051)
                scholarly.use_proxy(pg)
                self.logger.info("Using Tor proxy")
                return
            except Exception as tor_error:
                self.logger.warning(f"Tor proxy failed: {str(tor_error)}")
            
            # Attempt 2: Try free proxies with timeout
            try:
                pg.FreeProxies(timeout=5)  # Shorter timeout for free proxies
                scholarly.use_proxy(pg)
                self.logger.info("Using free proxies")
                return
            except Exception as free_proxy_error:
                self.logger.warning(f"Free proxies failed: {str(free_proxy_error)}")
            
            # Fallback to no proxy
            scholarly.use_proxy(None)
            self.logger.warning("Continuing without proxy")
            
        except Exception as e:
            scholarly.use_proxy(None)
            self.logger.error(f"Proxy initialization completely failed: {str(e)}")
            self.logger.warning("Continuing without proxy")

    def _enforce_rate_limit(self):
        """Ensure we stay within rate limits"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._current_delay:
            wait_time = self._current_delay - elapsed
            self.logger.info(f"Rate limiting: Waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        self._last_request_time = time.time()

    def get_author_metrics(self, author_name: str) -> Dict:
        """Get author metrics with retries and fallbacks"""
        for attempt in range(self._max_retries):
            try:
                self._enforce_rate_limit()
                
                self.logger.info(f"Attempt {attempt+1} for {author_name}")
                search_query = scholarly.search_author(author_name)
                author = next(search_query).fill()
                
                return {
                    "h_index": author.hindex,
                    "citations": author.citedby,
                    "affiliation": author.affiliation,
                    "is_industry": self._is_industry_affiliation(author.affiliation),
                    "source": "Google Scholar"
                }
                
            except StopIteration:
                self.logger.warning(f"No profile found for {author_name}")
                return self._get_fallback_metrics(author_name)
            except Exception as e:
                self.logger.error(f"Attempt {attempt+1} failed: {str(e)}")
                if attempt == self._max_retries - 1:
                    return self._get_fallback_metrics(author_name)
                
                # Exponential backoff
                self._current_delay = min(600, self._current_delay * 2)
                time.sleep(5 * (attempt + 1))

        return self._get_fallback_metrics(author_name)

    def _get_semantic_scholar_data(self, author_name: str, paper_title: str) -> Dict:
        """Get data from Semantic Scholar API"""
        try:
            # Placeholder for Semantic Scholar API implementation
            # You would implement actual API calls here
            return {}
        except Exception as e:
            self.logger.error(f"Semantic Scholar failed: {str(e)}")
            return {}

    def _is_industry_affiliation(self, affiliation: str) -> bool:
        """Determine if affiliation is industry (vs academic)"""
        if not affiliation:
            return False
        return not any(x in affiliation.lower() for x in ['university', 'college', 'institute'])

    def _get_fallback_metrics(self, author_name: str) -> Dict:
        """Provide fallback metrics when all sources fail"""
        return {
            "h_index": 0,
            "citations": 0,
            "affiliation": "",
            "is_industry": False,
            "source": "Fallback"
        }

    def _calculate_prestige_score(self, author_scores: Dict[str, int]) -> float:
        """Calculate score based on presence of prestigious authors"""
        max_score = max(author_scores.values(), default=0)
        if max_score >= self.config['prestige_threshold']:
            return 1.0
        return max_score / self.config['prestige_threshold']

    def _calculate_balance_score(self, author_scores: Dict[str, int]) -> float:
        """Calculate balance score - prefers teams with one prestigious author and junior authors"""
        scores = list(author_scores.values())
        
        if len(scores) == 1:
            return 0.7  # Single-author papers get decent but not max score
        
        # Count how many authors are in each tier
        tier_counts = Counter(scores)
        
        # Ideal case: 1 prestigious + a few junior authors
        has_prestige = any(s >= self.config['prestige_threshold'] for s in scores)
        num_junior = sum(1 for s in scores if s <= 3)
        
        if has_prestige and len(scores) <= 4 and num_junior >= 1:
            return 1.0
        elif has_prestige:
            return 0.8
        else:
            # No prestigious authors - score based on average
            return np.mean(scores) / 10

    def _calculate_industry_score(self, author_metrics: List[Dict]) -> float:
        """Calculate score based on industry participation"""
        industry_count = sum(1 for m in author_metrics if m.get('is_industry', False))
        
        if industry_count == len(author_metrics):
            return 1.0  # All authors from industry
        elif industry_count > 0:
            return 0.5  # Mixed academia/industry
        return 0.0      # Pure academia

    def _calculate_size_penalty(self, team_size: int) -> float:
        """Calculate penalty for very large author lists"""
        if team_size <= self.config['ideal_team_size']:
            return 0.0
        elif team_size > self.config['max_team_size']:
            return 1.0  # Maximum penalty
        else:
            return min(1.0, 
                     (team_size - self.config['ideal_team_size']) / 
                     (self.config['max_team_size'] - self.config['ideal_team_size']))

    def _calculate_composite_score(self, author_scores: Dict, author_metrics: List) -> float:
        """Combine all component scores into final 0-1 score"""
        components = {
            'prestige': self._calculate_prestige_score(author_scores),
            'balance': self._calculate_balance_score(author_scores),
            'industry': self._calculate_industry_score(author_metrics),
            'size_penalty': self._calculate_size_penalty(len(author_scores))
        }
        
        return sum(components[k] * self.config['weights'][k] for k in components)

    def _evaluate_lineup(self, title: str, authors: List[str]) -> Dict:
        """Evaluate an author lineup and return composite score"""
        author_metrics = [self.get_author_metrics(a) for a in authors]
        author_scores = {a: m.get('h_index', 0) for a, m in zip(authors, author_metrics)}
        
        return {
            'score': min(1.0, max(0.0, self._calculate_composite_score(author_scores, author_metrics))),
            'author_scores': author_scores,
            'components': {
                'prestige': self._calculate_prestige_score(author_scores),
                'balance': self._calculate_balance_score(author_scores),
                'industry': self._calculate_industry_score(author_metrics),
                'size_penalty': self._calculate_size_penalty(len(authors))
            }
        }

    def batch_evaluate(self, papers: List['PaperRecord']) -> Tuple[List['PaperRecord'], dict]:
        stats = {
            'total_evaluated': 0,
            'papers_by_score': defaultdict(int),
            'processing_times': [],
            'errors': 0
        }
        updated_papers = []
        
        for paper in papers:
            try:
                if not paper.authors:
                    paper.author_lineup_score = 0.0
                    paper.author_metrics = {"error": "no_authors"}
                    updated_papers.append(paper)
                    continue
                    
                start_time = time.time()
                result = self._evaluate_lineup(paper.title, paper.authors)
                
                paper.author_lineup_score = result['score']
                paper.author_metrics = {
                    'author_scores': result['author_scores'],
                    'components': result['components']
                }
                
                stats['total_evaluated'] += 1
                stats['processing_times'].append(time.time() - start_time)
                stats['papers_by_score'][round(result['score'], 1)] += 1
                updated_papers.append(paper)
                
            except Exception as e:
                stats['errors'] += 1
                self.logger.error(f"Failed to evaluate {getattr(paper, 'arxiv_id', 'unknown')}: {str(e)}")
                continue
                
        if stats['processing_times']:
            stats['avg_processing_time'] = np.mean(stats['processing_times'])
        else:
            stats['avg_processing_time'] = 0
            
        return updated_papers, stats

    @staticmethod
    def print_stats(stats: dict):
        """Print evaluation statistics"""
        print("\n=== Author Evaluation Report ===")
        print(f"Total papers evaluated: {stats['total_evaluated']}")
        if 'avg_processing_time' in stats:
            print(f"Average processing time: {stats['avg_processing_time']:.2f}s per paper")
        print(f"Errors encountered: {stats['errors']}")
        
        if stats.get('papers_by_score'):
            print("\nScore Distribution:")
            for score, count in sorted(stats['papers_by_score'].items()):
                print(f"  {score:.1f}: {count} papers")