from typing import List
from .base import BaseScraper, Article


class AnthropicArticle(Article):
    pass


class AnthropicScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return [
            "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
            "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
            "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml"
        ]

    def get_articles(self, hours: int = 24) -> List[AnthropicArticle]:
        return [
            AnthropicArticle(**article.model_dump())
            for article in super().get_articles(hours)
        ]


if __name__ == "__main__":
    scraper = AnthropicScraper()
    # Use a longer time window to find articles (RSS feed has older articles)
    articles: List[AnthropicArticle] = scraper.get_articles(hours=10000)
    print(f"Found {len(articles)} articles")
    if articles:
        print(f"\nFirst article: {articles[0].title}")
        print(f"URL: {articles[0].url}")
    else:
        print("No articles found")
