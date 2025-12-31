from datetime import datetime, timedelta, timezone
from typing import List, Optional
from abc import ABC, abstractmethod
import feedparser
import re
import html
from pydantic import BaseModel


class Article(BaseModel):
    title: str
    description: str
    url: str
    guid: str
    published_at: datetime
    category: Optional[str] = None


class BaseScraper(ABC):
    @property
    @abstractmethod
    def rss_urls(self) -> List[str]:
        pass
    
    # Description is a bit different across the RSS feeds we are using, need to normalize it.
    @property
    def max_description_length(self) -> int:
        """
        Maximum length for normalized descriptions.
        Override in subclasses to customize per scraper.
        """
        return 500
    
    def _normalize_description(self, entry) -> str:
        """
        Extract and normalize description from RSS feed entry.
        
        Handles various RSS feed formats:
        - Tries description, summary, subtitle fields
        - Strips HTML tags
        - Limits length to prevent full article content
        - Handles CDATA sections
        - Cleans whitespace
        
        Args:
            entry: feedparser entry object
            
        Returns:
            Clean, normalized description string (max length per max_description_length)
        """
        # Try multiple fields in order of preference
        raw_text = (
            entry.get("description") or
            entry.get("summary") or
            entry.get("subtitle") or
            ""
        )
        
        if not raw_text:
            return ""
        
        # Handle CDATA sections (feedparser usually handles this, but be safe)
        # Remove CDATA markers if present
        raw_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', raw_text, flags=re.DOTALL)
        
        # Strip HTML tags
        # Simple regex approach (more reliable than html.parser for mixed content)
        text = re.sub(r'<[^>]+>', '', raw_text)
        
        # Decode HTML entities (&amp; -> &, &lt; -> <, etc.)
        text = html.unescape(text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
        text = text.strip()
        
        # Limit length to prevent full article content
        # Most RSS descriptions should be summaries, not full articles
        max_length = self.max_description_length
        
        if len(text) > max_length:
            # Try to truncate at sentence boundary
            truncated = text[:max_length]
            last_period = truncated.rfind('.')
            last_exclamation = truncated.rfind('!')
            last_question = truncated.rfind('?')
            
            # Find the last sentence ending
            last_sentence_end = max(last_period, last_exclamation, last_question)
            
            if last_sentence_end > max_length * 0.7:  # At least 70% of max length
                text = text[:last_sentence_end + 1]
            else:
                # No good sentence boundary, just truncate and add ellipsis
                text = text[:max_length].rstrip() + "..."
        
        return text

    def get_articles(self, hours: int = 24) -> List[Article]:
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=hours)
        articles = []
        seen_guids = set()

        for rss_url in self.rss_urls:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                continue

            for entry in feed.entries:
                published_parsed = getattr(entry, "published_parsed", None)
                if not published_parsed:
                    continue

                published_time = datetime(*published_parsed[:6], tzinfo=timezone.utc)
                if published_time >= cutoff_time:
                    guid = entry.get("id", entry.get("link", ""))
                    if guid not in seen_guids:
                        seen_guids.add(guid)
                        articles.append(
                            Article(
                                title=entry.get("title", ""),
                                description=self._normalize_description(entry),
                                url=entry.get("link", ""),
                                guid=guid,
                                published_at=published_time,
                                category=entry.get("tags", [{}])[0].get("term")
                                if entry.get("tags")
                                else None,
                            )
                        )

        return articles