"""
Repository for RSS article models.
Handles all article-related database operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from .base_repository import BaseRepository
from .models import Article


class ArticleRepository(BaseRepository):
    """
    Repository for managing articles from all sources.
    Uses unified Article model with source column.
    """
    
    # Valid source types
    VALID_SOURCES = {
        'openai', 'anthropic', 'cursor', 'windsurf', 
        'deepmind', 'xai', 'nvdia'
    }
    
    def __init__(self, session: Optional[Session] = None):
        super().__init__(session)
        self.model_class = Article  # Now safe to use with BaseRepository methods!
    
    def bulk_create_articles(
        self,
        source: str,
        articles: List[dict]
    ) -> int:
        """
        Create articles from any source.
        
        Args:
            source: Source of articles ('openai', 'anthropic', etc.)
            articles: List of article dictionaries
            
        Returns:
            Number of new articles created
            
        Raises:
            ValueError: If source is not recognized
        """
        if source not in self.VALID_SOURCES:
            raise ValueError(f"Unknown source: {source}. Valid sources: {self.VALID_SOURCES}")
        
        formatted = [
            {
                "guid": a["guid"],
                "source": source,  # Add source here
                "title": a["title"],
                "url": a["url"],
                "published_at": a["published_at"],
                "description": a.get("description", ""),
                "category": a.get("category"),
            }
            for a in articles
        ]
        # Use composite key for duplicate checking (source + guid)
        return self._bulk_create_items(
            formatted, Article, "guid", "guid",
            unique_fields=["source", "guid"]
        )
    
    def get_articles_by_source(
        self,
        source: str,
        limit: Optional[int] = None
    ) -> List[Article]:
        """
        Get all articles from a specific source.
        
        Args:
            source: Source to retrieve articles from
            limit: Maximum number of articles to return
            
        Returns:
            List of Article instances
        """
        if source not in self.VALID_SOURCES:
            raise ValueError(f"Unknown source: {source}. Valid sources: {self.VALID_SOURCES}")
        
        query = self.session.query(Article).filter(Article.source == source)
        if limit:
            query = query.limit(limit)
        return query.order_by(Article.published_at.desc()).all()
    
    def get_all_articles(self, limit: Optional[int] = None) -> List[Article]:
        """
        Get all articles from all sources.
        
        Args:
            limit: Maximum number of articles to return
            
        Returns:
            List of Article instances ordered by published_at descending
        """
        query = self.session.query(Article)
        if limit:
            query = query.limit(limit)
        return query.order_by(Article.published_at.desc()).all()
    
    def get_recent_articles(
        self, hours: int = 24, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get RSS articles from the last N hours.
        
        This method filters articles by published_at time, making it suitable
        for daily processing pipelines. Duplicate prevention is handled by
        create_digest() method, so this doesn't check for existing digests.
        
        Args:
            hours: Number of hours to look back (default: 24)
            limit: Maximum number of articles to return
            
        Returns:
            List of article dictionaries with unified format:
            {
                "type": str,           # 'openai', 'anthropic', etc.
                "id": str,              # guid
                "title": str,
                "url": str,
                "content": str,          # description
                "published_at": datetime
            }
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Only RSS articles from unified table
        db_articles = self.session.query(Article).filter(
            Article.published_at >= cutoff_time
        ).all()
        
        articles = []
        for article in db_articles:
            articles.append({
                "type": article.source,
                "id": article.guid,
                "title": article.title,
                "url": article.url,
                "content": article.description or "",
                "published_at": article.published_at,
            })
        
        if limit:
            articles = articles[:limit]
        
        return articles