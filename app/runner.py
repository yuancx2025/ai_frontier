from typing import List, Callable, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from .scrapers.youtube import YouTubeScraper, ChannelVideo
from .scrapers.openai import OpenAIScraper
from .scrapers.anthropic import AnthropicScraper
from .scrapers.cursor import CursorScraper
from .scrapers.windsurf import WindsurfScraper
from .scrapers.deepmind import DeepMindScraper
from .scrapers.xai import XAIScraper
from .scrapers.nvdia import NvdiaScraper
from .database.youtube_repository import YouTubeRepository
from .database.article_repository import ArticleRepository

# Load environment variables
load_dotenv()


class ScrapingResult(BaseModel):
    """Result from a single scraper run."""
    source: str = Field(description="Source name (e.g., 'youtube', 'openai')")
    items: List[Any] = Field(description="List of scraped items")
    count: int = Field(description="Number of items scraped")
    success: bool = Field(default=True, description="Whether scraping succeeded")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="When scraping occurred")
    
    @property
    def item_count(self) -> int:
        """Convenience property for count."""
        return len(self.items)
    
    class Config:
        arbitrary_types_allowed = True  # For List[Any] with different item types


class ScrapingResults(BaseModel):
    """Aggregated results from all scrapers."""
    youtube: ScrapingResult
    openai: ScrapingResult
    anthropic: ScrapingResult
    cursor: ScrapingResult
    windsurf: ScrapingResult
    deepmind: ScrapingResult
    xai: ScrapingResult
    nvdia: ScrapingResult
    total_items: int = Field(description="Total items across all sources")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def get_summary(self) -> dict:
        """Get counts per source as a dictionary."""
        return {
            "youtube": self.youtube.count,
            "openai": self.openai.count,
            "anthropic": self.anthropic.count,
            "cursor": self.cursor.count,
            "windsurf": self.windsurf.count,
            "deepmind": self.deepmind.count,
            "xai": self.xai.count,
            "nvdia": self.nvdia.count,
        }
    
    def get_all_items(self) -> dict:
        """Get all items per source as a dictionary."""
        return {
            "youtube": self.youtube.items,
            "openai": self.openai.items,
            "anthropic": self.anthropic.items,
            "cursor": self.cursor.items,
            "windsurf": self.windsurf.items,
            "deepmind": self.deepmind.items,
            "xai": self.xai.items,
            "nvdia": self.nvdia.items,
        }


def _get_youtube_channels() -> List[str]:
    """
    Get YouTube channel IDs from environment variable or use defaults.
    
    Environment variable format: comma-separated channel IDs
    Example: YOUTUBE_CHANNELS=UCn8ujwUInbJkBhffxqAPBVQ,UCawZsQWqfGSbCI5yjkdVkTA
    """
    channels_env = os.getenv("YOUTUBE_CHANNELS")
    
    if channels_env:
        # Parse comma-separated values, strip whitespace
        return [ch.strip() for ch in channels_env.split(",") if ch.strip()]
    
    # Default channels (fallback)
    return [
        "UCn8ujwUInbJkBhffxqAPBVQ",  # Dave Ebbelaar
    ]


def _save_youtube_videos(
    scraper: YouTubeScraper, youtube_repo: YouTubeRepository, hours: int
) -> List[ChannelVideo]:
    videos = []
    video_dicts = []
    youtube_channels = _get_youtube_channels()
    for channel_id in youtube_channels:
        channel_videos = scraper.get_latest_videos(channel_id, hours=hours)
        videos.extend(channel_videos)
        video_dicts.extend(
            [
                {
                    "video_id": v.video_id,
                    "title": v.title,
                    "url": v.url,
                    "channel_id": channel_id,
                    "published_at": v.published_at,
                    "description": v.description,
                }
                for v in channel_videos
            ]
        )
    if video_dicts:
        youtube_repo.bulk_create_videos(video_dicts)
    return videos


def _save_rss_articles(
    scraper, articles_repo: ArticleRepository, source: str, hours: int
) -> List[Any]:
    articles = scraper.get_articles(hours=hours)
    if articles:
        article_dicts = [
            {
                "guid": a.guid,
                "title": a.title,
                "url": a.url,
                "published_at": a.published_at,
                "description": a.description,
                "category": a.category,
            }
            for a in articles
        ]
        articles_repo.bulk_create_articles(source, article_dicts)
    return articles


SCRAPER_REGISTRY = [
    ("youtube", YouTubeScraper(), _save_youtube_videos),
    ("openai", OpenAIScraper(), _save_rss_articles),
    ("anthropic", AnthropicScraper(), _save_rss_articles),
    ("cursor", CursorScraper(), _save_rss_articles),
    ("windsurf", WindsurfScraper(), _save_rss_articles),
    ("deepmind", DeepMindScraper(), _save_rss_articles),
    ("xai", XAIScraper(), _save_rss_articles),
    ("nvdia", NvdiaScraper(), _save_rss_articles),
]


def run_scrapers(hours: int = 24) -> ScrapingResults:
    """
    Run all registered scrapers and return typed results.
    
    Args:
        hours: Number of hours to look back for content
        
    Returns:
        ScrapingResults model with results from all scrapers
    """
    youtube_repo = YouTubeRepository()
    articles_repo = ArticleRepository()
    results = {}

    for name, scraper, save_func in SCRAPER_REGISTRY:
        try:
            if name == "youtube":
                items = save_func(scraper, youtube_repo, hours)
            else:
                items = save_func(scraper, articles_repo, name, hours)
            
            results[name] = ScrapingResult(
                source=name,
                items=items,
                count=len(items),
                success=True
            )
        except Exception as e:
            error_msg = str(e)
            # Check for common database errors
            if "does not exist" in error_msg or "relation" in error_msg.lower():
                print(f"Error: Database tables not initialized. Run: uv run python -m app.database.create_tables")
            else:
                print(f"Error running {name} scraper: {error_msg}")
            
            results[name] = ScrapingResult(
                source=name,
                items=[],
                count=0,
                success=False,
                error=error_msg
            )
    
    # Create aggregated result with defaults for missing sources
    default_result = lambda source: ScrapingResult(source=source, items=[], count=0, success=False)
    
    return ScrapingResults(
        youtube=results.get("youtube", default_result("youtube")),
        openai=results.get("openai", default_result("openai")),
        anthropic=results.get("anthropic", default_result("anthropic")),
        cursor=results.get("cursor", default_result("cursor")),
        windsurf=results.get("windsurf", default_result("windsurf")),
        deepmind=results.get("deepmind", default_result("deepmind")),
        xai=results.get("xai", default_result("xai")),
        nvdia=results.get("nvdia", default_result("nvdia")),
        total_items=sum(r.count for r in results.values())
    )


if __name__ == "__main__":
    results = run_scrapers(hours=24*7)
    print(f"YouTube videos: {results.youtube.count}")
    print(f"OpenAI articles: {results.openai.count}")
    print(f"Anthropic articles: {results.anthropic.count}")
    print(f"Cursor articles: {results.cursor.count}")
    print(f"Windsurf articles: {results.windsurf.count}")
    print(f"DeepMind articles: {results.deepmind.count}")
    print(f"XAI articles: {results.xai.count}")
    print(f"NVIDIA articles: {results.nvdia.count}")
    print(f"\nTotal items: {results.total_items}")