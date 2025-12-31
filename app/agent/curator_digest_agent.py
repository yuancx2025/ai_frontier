from typing import Optional
from pydantic import BaseModel, Field
from .base import BaseAgent
from .prompts import CURATOR_DIGEST_PROMPT


class CuratorDigestOutput(BaseModel):
    """Combined output containing both digest and relevance score."""
    title: str = Field(description="Compelling title (5-10 words) that captures the essence of the content")
    summary: str = Field(description="2-3 sentence summary highlighting main points and why they matter")
    relevance_score: float = Field(
        description="Relevance score from 0.0 to 10.0 based on user profile",
        ge=0.0,
        le=10.0
    )
    reasoning: str = Field(description="Brief explanation of why this article is relevant to the user profile")


class CuratorDigestAgent(BaseAgent):
    """
    Combined agent that generates digests and scores relevance in a single call.
    This replaces the separate DigestAgent and CuratorAgent for efficiency.
    """
    
    def __init__(self, user_profile: dict):
        super().__init__("gemini-3-flash-preview")
        self.user_profile = user_profile
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        interests = "\n".join(f"- {interest}" for interest in self.user_profile["interests"])
        preferences = self.user_profile["preferences"]
        pref_text = "\n".join(f"- {k}: {v}" for k, v in preferences.items())
        
        return f"""{CURATOR_DIGEST_PROMPT}

User Profile:
Name: {self.user_profile["name"]}
Background: {self.user_profile["background"]}
Expertise Level: {self.user_profile["expertise_level"]}

Interests:
{interests}

Preferences:
{pref_text}"""

    def generate_digest_with_score(
        self, 
        title: str, 
        content: str, 
        article_type: str
    ) -> Optional[CuratorDigestOutput]:
        """
        Generate a digest and relevance score for an article in a single call.
        
        Args:
            title: Original article title
            content: Article content (will be truncated to 8000 chars)
            article_type: Type of article (e.g., 'openai', 'youtube')
            
        Returns:
            CuratorDigestOutput with title, summary, relevance_score, and reasoning
        """
        try:
            user_prompt = f"""Create a digest and score this {article_type} article:

Title: {title}
Content: {content[:8000]}

Generate:
1. A compelling digest title (5-10 words)
2. A 2-3 sentence summary highlighting key points
3. A relevance score (0.0-10.0) based on how well this aligns with the user profile
4. Brief reasoning for the relevance score"""

            return self.generate_structured_response(
                prompt=user_prompt,
                system_prompt=self.system_prompt,
                output_class=CuratorDigestOutput,
                temperature=0.7
            )
        except Exception as e:
            print(f"Error generating curator digest: {e}")
            return None
