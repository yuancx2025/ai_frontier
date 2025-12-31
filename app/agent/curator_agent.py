from typing import List
from pydantic import BaseModel, Field
from .base import BaseAgent
from .prompts import CURATOR_PROMPT


class RankedArticle(BaseModel):
    digest_id: str = Field(description="The ID of the digest (article_type:article_id)")
    relevance_score: float = Field(description="Relevance score from 0.0 to 10.0", ge=0.0, le=10.0)
    rank: int = Field(description="Rank position (1 = most relevant)", ge=1)
    reasoning: str = Field(description="Brief explanation of why this article is ranked here")


class RankedDigestList(BaseModel):
    articles: List[RankedArticle] = Field(description="List of ranked articles")


class CuratorAgent(BaseAgent):
    def __init__(self, user_profile: dict):
        super().__init__("gemini-3-flash-preview")
        self.user_profile = user_profile
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        interests = "\n".join(f"- {interest}" for interest in self.user_profile["interests"])
        preferences = self.user_profile["preferences"]
        pref_text = "\n".join(f"- {k}: {v}" for k, v in preferences.items())
        
        return f"""{CURATOR_PROMPT}

        User Profile:
        Name: {self.user_profile["name"]}
        Background: {self.user_profile["background"]}
        Expertise Level: {self.user_profile["expertise_level"]}

        Interests:
        {interests}

        Preferences:
        {pref_text}"""

    def rank_digests(self, digests: List[dict]) -> List[RankedArticle]:
        if not digests:
            return []
        
        digest_list = "\n\n".join([
            f"ID: {d['id']}\nTitle: {d['title']}\nSummary: {d['summary']}\nType: {d['article_type']}"
            for d in digests
        ])
        
        user_prompt = f"""Rank these {len(digests)} AI news digests based on the user profile:

{digest_list}

Provide a relevance score (0.0-10.0) and rank (1-{len(digests)}) for each article, ordered from most to least relevant."""

        try:
            ranked_list = self.generate_structured_response(
                prompt=user_prompt,
                system_prompt=self.system_prompt,
                output_class=RankedDigestList,
                temperature=0.3
            )
            return ranked_list.articles if ranked_list else []
        except Exception as e:
            print(f"Error ranking digests: {e}")
            return []
