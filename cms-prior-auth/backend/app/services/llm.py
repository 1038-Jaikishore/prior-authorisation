import json
import re
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.core.config import settings

class LLMProvider(ABC):
    @abstractmethod
    def generate_completion(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        json_mode: bool = False, 
        temperature: float = 0.0
    ) -> str:
        """Generates a text completion from the LLM model."""
        pass



class OpenRouterLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3-8b-instruct:free"):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def generate_completion(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        json_mode: bool = False, 
        temperature: float = 0.0
    ) -> str:
        if not self.api_key:
            raise ValueError("OpenRouter API key is missing. Please set OPENROUTER_API_KEY in .env")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/1038-Jaikishore/prior-authorisation.git",
            "X-Title": "CMS Prior Auth Decision Support"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=45)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise RuntimeError(f"OpenRouter returned error details: {data['error']}")

            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print("LLM ERROR", str(e))
            if 'response' in locals() and hasattr(response, 'text'):
                print("LLM RESPONSE TEXT:", response.text)
            raise RuntimeError(f"OpenRouter LLM request failed: {str(e)}")

def get_llm_provider() -> LLMProvider:
    key = settings.openrouter_api_key or getattr(settings, "llm_api_key", "")
    model = getattr(settings, "llm_model", "meta-llama/llama-3-8b-instruct:free")
    return OpenRouterLLMProvider(api_key=key, model=model)
