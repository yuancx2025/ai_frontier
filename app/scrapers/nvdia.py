from typing import List
from .base import BaseScraper, Article


class NvdiaArticle(Article):
    pass


class NvdiaScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return [
            "https://nvidianews.nvidia.com/releases.xml",
            "https://nvidianews.nvidia.com/cats/ai_platforms_deployment.xml"
        ]

    def get_articles(self, hours: int = 24) -> List[NvdiaArticle]:
        return [
            NvdiaArticle(**article.model_dump())
            for article in super().get_articles(hours)
        ]


if __name__ == "__main__":
    scraper = NvdiaScraper()
    # Use a longer time window to find articles (RSS feed has older articles)
    articles: List[NvdiaArticle] = scraper.get_articles(hours=100)
    print(f"Found {len(articles)} articles")
    if articles:
        print(f"\nFirst article: {articles[0].title}")
        print(f"URL: {articles[0].url}")
    else:
        print("No articles found")
