from typing import List
from .base import BaseScraper, Article


class DeepMindArticle(Article):
    pass


class DeepMindScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return [
            "https://deepmind.com/blog/feed/basic/"
        ]

    def get_articles(self, hours: int = 24) -> List[DeepMindArticle]:
        return [
            DeepMindArticle(**article.model_dump())
            for article in super().get_articles(hours)
        ]


if __name__ == "__main__":
    scraper = DeepMindScraper()
    articles: List[DeepMindArticle] = scraper.get_articles(hours=300)
    print(f"Found {len(articles)} articles")
    if articles:
        print(f"\nFirst article: {articles[0].title}")
        print(f"URL: {articles[0].url}")
