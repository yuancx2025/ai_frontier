from typing import List
from .base import BaseScraper, Article


class XAIArticle(Article):
    pass


class XAIScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return [
            "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_xainews.xml"
        ]

    def get_articles(self, hours: int = 24) -> List[XAIArticle]:
        return [
            XAIArticle(**article.model_dump())
            for article in super().get_articles(hours)
        ]


if __name__ == "__main__":
    scraper = XAIScraper()
    articles: List[XAIArticle] = scraper.get_articles(hours=3000)
    print(f"Found {len(articles)} articles")
    if articles:
        print(f"\nFirst article: {articles[0].title}")
        print(f"URL: {articles[0].url}")
