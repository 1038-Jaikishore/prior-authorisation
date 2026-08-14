import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "cms_prior_auth"
    
    # Embedding Configuration
    embedding_provider: str = "mock"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_dimensions: int = 1536
    
    # Allow extra fields for LLM keys in future volumes
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
