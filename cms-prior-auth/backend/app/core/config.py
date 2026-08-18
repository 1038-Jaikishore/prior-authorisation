import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "cms_prior_auth"
    
    # Embedding Configuration
    openrouter_api_key: str = ""
    embedding_provider: str = "mock"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_dimensions: int = 1536
    
    # Document Upload Configuration
    max_upload_mb: int = 10
    allowed_document_types: str = "pdf,docx,txt"
    
    # Allow extra fields for LLM keys in future volumes
    llm_provider: str = "openrouter"
    llm_model: str = "openai/gpt-3.5-turbo"
    llm_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

settings = Settings()
