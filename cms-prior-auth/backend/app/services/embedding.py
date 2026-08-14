import hashlib
import random
import requests
from abc import ABC, abstractmethod
from typing import List
from app.core.config import settings

class EmbeddingProvider(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for a single block of text."""
        pass
        
    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of text blocks."""
        pass
        
    @abstractmethod
    def get_dimensions(self) -> int:
        """Return dimensions of the vectors produced by the model."""
        pass

class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions
        
    def get_embedding(self, text: str) -> List[float]:
        # Generate deterministic float vector using hashlib MD5 as seed
        hasher = hashlib.md5(text.encode("utf-8"))
        seed_val = int(hasher.hexdigest()[:8], 16)
        rng = random.Random(seed_val)
        return [rng.uniform(-1.0, 1.0) for _ in range(self.dimensions)]
        
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self.get_embedding(t) for t in texts]
        
    def get_dimensions(self) -> int:
        return self.dimensions

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dimensions: int = 1536):
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.url = "https://api.openai.com/v1/embeddings"
        
    def get_embedding(self, text: str) -> List[float]:
        res = self.get_embeddings([text])
        return res[0]
        
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            raise ValueError("OpenAI/OpenRouter API key is missing. Please set embedding_api_key in .env")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": texts,
            "model": self.model
        }
        
        # Add dimensions parameter if supported (like for text-embedding-3 models)
        if "text-embedding-3" in self.model:
            payload["dimensions"] = self.dimensions
            
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            embeddings = []
            # Preserve output order
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            for item in sorted_data:
                embeddings.append(item["embedding"])
            return embeddings
        except Exception as e:
            raise RuntimeError(f"Embedding request failed: {str(e)}")
            
    def get_dimensions(self) -> int:
        return self.dimensions

def get_embedding_provider() -> EmbeddingProvider:
    provider_name = settings.embedding_provider.lower().strip()
    dimensions = settings.embedding_dimensions
    
    if provider_name == "mock":
        return MockEmbeddingProvider(dimensions=dimensions)
    elif provider_name in ["openai", "openrouter"]:
        return OpenAIEmbeddingProvider(
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            dimensions=dimensions
        )
    else:
        raise ValueError(f"Unsupported embedding provider configured: '{settings.embedding_provider}'. Supported: 'mock', 'openai'.")
