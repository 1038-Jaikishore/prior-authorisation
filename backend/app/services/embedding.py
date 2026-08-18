import hashlib
import random
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any
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
            raise ValueError("OpenAI API key is missing. Please set embedding_api_key in .env")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": texts,
            "model": self.model
        }
        
        if "text-embedding-3" in self.model:
            payload["dimensions"] = self.dimensions
            
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            embeddings = []
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            for item in sorted_data:
                embeddings.append(item["embedding"])
            return embeddings
        except Exception as e:
            raise RuntimeError(f"OpenAI embedding request failed: {str(e)}")
            
    def get_dimensions(self) -> int:
        return self.dimensions

class OpenRouterEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "openai/text-embedding-3-small", dimensions: int = 1536):
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.url = "https://openrouter.ai/api/v1/embeddings"
        
    def get_embedding(self, text: str) -> List[float]:
        res = self.get_embeddings([text])
        return res[0]
        
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            raise ValueError("OpenRouter API key is missing. Please set OPENROUTER_API_KEY in .env")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/1038-Jaikishore/prior-authorisation.git",
            "X-Title": "CMS Prior Auth Decision Support"
        }
        
        payload = {
            "input": texts,
            "model": self.model
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise RuntimeError(f"OpenRouter returned error details: {data['error']}")
                
            embeddings = []
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            for item in sorted_data:
                embeddings.append(item["embedding"])
            return embeddings
        except Exception as e:
            raise RuntimeError(f"OpenRouter embedding request failed: {str(e)}")
            
    def get_dimensions(self) -> int:
        return self.dimensions

def get_embedding_provider() -> EmbeddingProvider:
    provider_name = settings.embedding_provider.lower().strip()
    dimensions = settings.embedding_dimensions
    
    if provider_name == "mock":
        return MockEmbeddingProvider(dimensions=dimensions)
    elif provider_name == "openrouter":
        key = settings.openrouter_api_key or settings.embedding_api_key
        return OpenRouterEmbeddingProvider(
            api_key=key,
            model=settings.embedding_model,
            dimensions=dimensions
        )
    elif provider_name == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            dimensions=dimensions
        )
    else:
        raise ValueError(f"Unsupported embedding provider: '{settings.embedding_provider}'")

def validate_provider(provider: EmbeddingProvider) -> Dict[str, Any]:
    """Validates connectivity, model support, and output vector format of the provider."""
    try:
        # Perform test embedding
        test_text = "Verification test text."
        vector = provider.get_embedding(test_text)
        
        # Verify vector properties
        if not isinstance(vector, list) or not all(isinstance(x, (int, float)) for x in vector):
            raise ValueError("Returned vector is not a list of numbers.")
            
        actual_dim = len(vector)
        expected_dim = provider.get_dimensions()
        
        if actual_dim != expected_dim:
            raise ValueError(f"Embedding dimension mismatch: expected {expected_dim}, got {actual_dim}.")
            
        return {
            "status": "VALID",
            "model": getattr(provider, "model", "unknown"),
            "dimensions": actual_dim
        }
    except Exception as e:
        return {
            "status": "INVALID",
            "error": str(e)
        }
