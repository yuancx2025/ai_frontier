from typing import List
from .base import BaseScraper, Article


class WindsurfArticle(Article):
    pass


class WindsurfScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return [
            "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_windsurf_blog.xml"
        ]

    def get_articles(self, hours: int = 24) -> List[WindsurfArticle]:
        return [
            WindsurfArticle(**article.model_dump())
            for article in super().get_articles(hours)
        ]


if __name__ == "__main__":
    scraper = WindsurfScraper()
    articles: List[WindsurfArticle] = scraper.get_articles(hours=300)
    print(f"Found {len(articles)} articles")
    if articles:
        print(f"\nFirst article: {articles[0].title}")
        print(f"URL: {articles[0].url}")
