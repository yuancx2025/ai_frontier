"""
Repository for Digest models.
Handles all digest-related database operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from .base_repository import BaseRepository
from .models import Digest


class DigestRepository(BaseRepository):
    """
    Repository for managing Digest models.
    """
    
    def __init__(self, session: Optional[Session] = None):
        super().__init__(session)
        self.model_class = Digest
    
    def create_digest(
        self,
        article_type: str,
        article_id: str,
        url: str,
        title: str,
        summary: str,
        relevance_score: Optional[float] = None,
        reasoning: Optional[str] = None,
        category: Optional[str] = None,
        published_at: Optional[datetime] = None,
    ) -> Optional[Digest]:
        """
        Create a new digest.
        
        Args:
            article_type: Type of article (e.g., 'openai', 'youtube')
            article_id: ID of the article
            url: Article URL
            title: Article title
            summary: Digest summary
            relevance_score: Relevance score (0.0-10.0) for user profile
            reasoning: Brief explanation of relevance score
            category: Content category (technique, research, education, etc.)
            published_at: Publication datetime (optional)
            
        Returns:
            Created Digest instance or None if duplicate
        """
        digest_id = f"{article_type}:{article_id}"
        existing = self.session.query(Digest).filter_by(id=digest_id).first()
        if existing:
            return None
        
        if published_at:
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            created_at = published_at
        else:
            created_at = datetime.now(timezone.utc)
        
        digest = Digest(
            id=digest_id,
            article_type=article_type,
            article_id=article_id,
            url=url,
            title=title,
            summary=summary,
            relevance_score=relevance_score,
            reasoning=reasoning,
            category=category,
            created_at=created_at,
        )
        self.session.add(digest)
        self.session.commit()
        return digest
    
    def get_recent_digests(
        self, hours: int = 24, exclude_sent: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recent digests within a time window.
        
        Args:
            hours: Number of hours to look back
            exclude_sent: Whether to exclude already-sent digests
            
        Returns:
            List of digest dictionaries
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = self.session.query(Digest).filter(Digest.created_at >= cutoff_time)
        
        if exclude_sent:
            query = query.filter(Digest.sent_at.is_(None))
        
        digests = query.order_by(Digest.created_at.desc()).all()
        
        return [
            {
                "id": d.id,
                "article_type": d.article_type,
                "article_id": d.article_id,
                "url": d.url,
                "title": d.title,
                "summary": d.summary,
                "relevance_score": d.relevance_score,
                "reasoning": d.reasoning,
                "category": d.category,
                "created_at": d.created_at,
                "sent_at": d.sent_at,
            }
            for d in digests
        ]
    
    def mark_digests_as_sent(self, digest_ids: List[str]) -> int:
        """
        Mark digests as sent by setting their sent_at timestamp.
        
        Args:
            digest_ids: List of digest IDs to mark as sent
            
        Returns:
            Number of digests updated
        """
        sent_time = datetime.now(timezone.utc)
        updated = (
            self.session.query(Digest)
            .filter(Digest.id.in_(digest_ids))
            .update({Digest.sent_at: sent_time}, synchronize_session=False)
        )
        self.session.commit()
        return updated
    
    def get_all_digest_ids(self) -> set:
        """
        Get all digest IDs as a set for quick lookup.
        Used to check which articles already have digests.
        
        Returns:
            Set of digest IDs in format "article_type:article_id"
        """
        digests = self.session.query(Digest).all()
        return {f"{d.article_type}:{d.article_id}" for d in digests}
    
    def get_recent_digest_ids(self, hours: int = 24) -> set:
        """
        Get digest IDs for digests created within the last N hours.
        More efficient than get_all_digest_ids() when only recent digests matter.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Set of digest IDs in format "article_type:article_id"
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        digests = self.session.query(Digest).filter(
            Digest.created_at >= cutoff_time
        ).all()
        return {d.id for d in digests}  # d.id is already in format "article_type:article_id"