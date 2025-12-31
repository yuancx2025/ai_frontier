from typing import Optional
import logging
from app.agent.curator_digest_agent import CuratorDigestAgent, CuratorDigestOutput
from app.profiles.user_profile import USER_PROFILE
from app.database.article_repository import ArticleRepository
from app.database.youtube_repository import YouTubeRepository
from app.database.digest_repository import DigestRepository
from .base import BaseProcessService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class DigestProcessor(BaseProcessService):
    def __init__(self, hours: int = 24, user_profile: dict = None):
        super().__init__()
        if user_profile is None:
            user_profile = USER_PROFILE
        self.agent = CuratorDigestAgent(user_profile)
        self.articles_repo = ArticleRepository()
        self.youtube_repo = YouTubeRepository()
        self.digests_repo = DigestRepository()
        self.hours = hours

    def get_items_to_process(self, limit: Optional[int] = None) -> list:
        # Get articles from RSS feeds
        articles = self.articles_repo.get_recent_articles(hours=self.hours, limit=limit)
        
        # Get YouTube videos
        youtube_videos = self.youtube_repo.get_recent_videos(hours=self.hours, limit=limit)
        
        # Combine both sources
        all_items = articles + youtube_videos
        
        # Apply limit to combined list if specified
        if limit:
            all_items = all_items[:limit]
        
        return all_items

    def process_item(self, item: dict) -> Optional[CuratorDigestOutput]:
        return self.agent.generate_digest_with_score(
            title=item["title"],
            content=item["content"],
            article_type=item["type"]
        )

    def save_result(self, item: dict, result: CuratorDigestOutput) -> bool:
        try:
            self.digests_repo.create_digest(
                article_type=item["type"],
                article_id=item["id"],
                url=item["url"],
                title=result.title,
                summary=result.summary,
                relevance_score=result.relevance_score,
                reasoning=result.reasoning,
                published_at=item.get("published_at")
            )
            return True
        except Exception:
            return False

    def _get_item_id(self, item: dict) -> str:
        return f"{item['type']}:{item['id']}"

    def _get_item_title(self, item: dict) -> str:
        return item["title"]


def process_digests(hours: int = 24, limit: Optional[int] = None, user_profile: dict = None) -> dict:
    """
    Process articles from the last N hours and create digests with relevance scores.
    
    Args:
        hours: Number of hours to look back for articles (default: 24)
        limit: Maximum number of articles to process
        user_profile: User profile for relevance scoring (defaults to USER_PROFILE)
        
    Returns:
        Dictionary with processing results
    """
    processor = DigestProcessor(hours=hours, user_profile=user_profile)
    return processor.process(limit=limit)


if __name__ == "__main__":
    result = process_digests()
    print(f"Total articles: {result['total']}")
    print(f"Processed: {result['processed']}")
    print(f"Failed: {result['failed']}")

