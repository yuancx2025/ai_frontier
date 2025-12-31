"""
Repository for YouTube video models.
Handles all YouTube-related database operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from .base_repository import BaseRepository
from .models import YouTubeVideo


class YouTubeRepository(BaseRepository):
    """
    Repository for managing YouTube video models.
    """
    
    def __init__(self, session: Optional[Session] = None):
        super().__init__(session)
        self.model_class = YouTubeVideo
    
    def create_video(
        self,
        video_id: str,
        title: str,
        url: str,
        channel_id: str,
        published_at: datetime,
        description: str = "",
        transcript: Optional[str] = None,
    ) -> Optional[YouTubeVideo]:
        """
        Create a single YouTube video.
        
        Args:
            video_id: YouTube video ID
            title: Video title
            url: Video URL
            channel_id: YouTube channel ID
            published_at: Publication datetime
            description: Video description
            transcript: Video transcript (optional)
            
        Returns:
            Created YouTubeVideo instance or None if duplicate
        """
        existing = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if existing:
            return None
        
        video = YouTubeVideo(
            video_id=video_id,
            title=title,
            url=url,
            channel_id=channel_id,
            published_at=published_at,
            description=description,
            transcript=transcript,
        )
        self.session.add(video)
        self.session.commit()
        return video
    
    def bulk_create_videos(self, videos: List[dict]) -> int:
        """
        Bulk create YouTube videos with duplicate checking.
        
        Args:
            videos: List of video dictionaries
            
        Returns:
            Number of new videos created
        """
        formatted_videos = [
            {
                "video_id": v["video_id"],
                "title": v["title"],
                "url": v["url"],
                "channel_id": v.get("channel_id", ""),
                "published_at": v["published_at"],
                "description": v.get("description", ""),
                "transcript": v.get("transcript"),
            }
            for v in videos
        ]
        return self._bulk_create_items(
            formatted_videos, YouTubeVideo, "video_id", "video_id"
        )
    
    def get_videos_without_transcript(
        self, limit: Optional[int] = None
    ) -> List[YouTubeVideo]:
        """
        Get YouTube videos that don't have transcripts yet.
        
        Args:
            limit: Maximum number of videos to return
            
        Returns:
            List of YouTubeVideo instances
        """
        query = self.session.query(YouTubeVideo).filter(
            YouTubeVideo.transcript.is_(None)
        )
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def update_video_transcript(self, video_id: str, transcript: str) -> bool:
        """
        Update the transcript of a YouTube video.
        
        Args:
            video_id: YouTube video ID
            transcript: Transcript text to set
            
        Returns:
            True if updated, False if video not found
        """
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if video:
            video.transcript = transcript
            self.session.commit()
            return True
        return False
    
    def get_recent_videos(
        self, hours: int = 24, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get YouTube videos from the last N hours.
        
        Args:
            hours: Number of hours to look back (default: 24)
            limit: Maximum number of videos to return
            
        Returns:
            List of video dictionaries with unified format:
            {
                "type": str,           # 'youtube'
                "id": str,              # video_id
                "title": str,
                "url": str,
                "content": str,         # description or transcript
                "published_at": datetime
            }
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        db_videos = self.session.query(YouTubeVideo).filter(
            YouTubeVideo.published_at >= cutoff_time
        ).all()
        
        videos = []
        for video in db_videos:
            # Use transcript if available, otherwise use description
            content = video.transcript if video.transcript else (video.description or "")
            
            videos.append({
                "type": "youtube",
                "id": video.video_id,
                "title": video.title,
                "url": video.url,
                "content": content,
                "published_at": video.published_at,
            })
        
        if limit:
            videos = videos[:limit]
        
        return videos