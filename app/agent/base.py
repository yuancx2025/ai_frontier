import os
import json
from abc import ABC
from google import genai
from dotenv import load_dotenv

load_dotenv()


class BaseAgent(ABC):
    def __init__(self, model: str):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        self.client = genai.Client(api_key=api_key)
        self.model = model
    
    def _parse_structured_output(self, response_text: str, output_class):
        """Parse JSON response from Gemini into Pydantic model."""
        try:
            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            # Parse JSON
            data = json.loads(response_text)
            return output_class(**data)
        except (json.JSONDecodeError, ValueError) as e:
            # If parsing fails, try to extract JSON object from text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return output_class(**data)
                except:
                    pass
            raise ValueError(f"Failed to parse structured output: {e}")
    
    def generate_structured_response(self, prompt: str, system_prompt: str, output_class, temperature: float = 0.7):
        """Generate structured output using Gemini with JSON mode."""
        try:
            # Combine prompts
            full_prompt = f"{system_prompt}\n\n{prompt}\n\nPlease respond with valid JSON only."

            # Get JSON schema from Pydantic model
            schema = output_class.model_json_schema()
            
            # Use the new google-genai Client API
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config={
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                    "response_schema": schema
                }
            )
            
            response_text = response.text
            
            return self._parse_structured_output(response_text, output_class)
        except Exception as e:
            raise ValueError(f"Error generating structured response: {e}")

