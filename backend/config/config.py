import json
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Customer Support AI"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0"
    DEBUG: bool = True

    # Host settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS origins
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            try:
                return json.loads(v)
            except Exception:
                return ["http://localhost:3000"]
        return v

    # Database
    DATABASE_URL: str = "sqlite:///./customer_support.db"

    # Embedding Model Name
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    # FAISS Persistence Paths
    VECTOR_INDEX_PATH: str = "knowledge_base/faiss_index.bin"
    VECTOR_METADATA_PATH: str = "knowledge_base/faiss_metadata.json"

    # Gemini API Credentials
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: Optional[str] = "gemini-2.5-flash"

    # MongoDB Credentials
    MONGODB_URI: Optional[str] = None
    MONGODB_DB_NAME: str = "customer_support_ai"

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v: Optional[str]) -> Optional[str]:
        if not v or v.strip() == "" or v == "PASTE_YOUR_ACTUAL_API_KEY_HERE":
            raise ValueError("GEMINI_API_KEY environment variable is missing or has not been configured in your .env file.")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
