from typing import Optional
from pydantic import BaseModel
from .base import BaseAgent
from .prompts import DIGEST_PROMPT


class DigestOutput(BaseModel):
    title: str
    summary: str


class DigestAgent(BaseAgent):
    def __init__(self):
        super().__init__("gemini-3-flash-preview")
        self.system_prompt = DIGEST_PROMPT

    def generate_digest(self, title: str, content: str, article_type: str) -> Optional[DigestOutput]:
        try:
            user_prompt = f"Create a digest for this {article_type}: \n Title: {title} \n Content: {content[:8000]}"

            return self.generate_structured_response(
                prompt=user_prompt,
                system_prompt=self.system_prompt,
                output_class=DigestOutput,
                temperature=0.7
            )
        except Exception as e:
            print(f"Error generating digest: {e}")
            return None

