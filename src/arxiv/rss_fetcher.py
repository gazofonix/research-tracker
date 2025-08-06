# rss_fetcher.py
import feedparser
from datetime import datetime, timedelta
from src.arxiv.arxiv_categories import arxiv_categories


def get_user_preferred_category():
    """Prompt user to select an arXiv category."""
    print("Available arXiv CS categories:")
    for i, (cat_id, cat_info) in enumerate(arxiv_categories.items(), 1):
        print(f"{i}. {cat_id} - {cat_info['name']}")
    choice = input("Select a category by number: ")
    try:
        idx = int(choice) - 1
        cat_id = list(arxiv_categories.keys())[idx]
        return cat_id
    except (ValueError, IndexError):
        print("Invalid selection.")
        return None

def fetch_arxiv_papers(feed_url, days=7):
    """Fetch latest arXiv papers from the given RSS feed URL."""
    feed = feedparser.parse(feed_url)
    papers = []
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)
    for entry in feed.entries:
        # Parse published date
        if hasattr(entry, 'published_parsed'):
            published = datetime(*entry.published_parsed[:6])
        else:
            continue
        if published < cutoff:
            continue
        papers.append({
            "title": entry.title,
            "summary": entry.summary,
            "link": entry.link,
            "authors": [author.name for author in entry.authors] if hasattr(entry, 'authors') else []
        })
    # Sort by published date, descending
    papers.sort(key=lambda x: x.get("published", now), reverse=True)
    return papers

def fetch_papers():
    """Fetch papers from arXiv based on user-selected category."""
    cat_id = get_user_preferred_category()
    if not cat_id:
        return []
    feed_url = f"https://rss.arxiv.org/rss/{cat_id}"
    print(f"\nFetching latest papers from {cat_id} ({arxiv_categories[cat_id]['name']})...\n")
    papers = fetch_arxiv_papers(feed_url)
    if not papers:
        print("No papers found.")
    else:
        print(f"Fetched {len(papers)} papers from the last 7 days.")
    return papers