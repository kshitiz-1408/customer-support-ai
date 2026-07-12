import os
import json
from typing import List, Union, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Customer Support AI"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0"
    DEBUG: bool = True

    # Environment
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

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
    HF_HOME: str = "data/hf_cache"

    # FAISS Persistence Paths
    VECTOR_INDEX_PATH: str = "knowledge_base/faiss_index.bin"
    VECTOR_METADATA_PATH: str = "knowledge_base/faiss_metadata.json"

    # Gemini API Credentials
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: Optional[str] = "gemini-2.5-flash"

    # MongoDB Credentials
    MONGODB_URI: Optional[str] = None
    MONGODB_DB_NAME: str = "customer_support_ai"

    # Path & Dir boundaries
    RUNTIME_DATA_DIR: str = "data"
    MOCK_MONGO_PATH: Optional[str] = None
    EVALUATION_OUTPUT_DIR: Optional[str] = None

    # Resilience & Timeout configurations
    GEMINI_TIMEOUT: float = 30.0
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_BACKOFF_FACTOR: float = 2.0
    MONGODB_TIMEOUT_MS: int = 5000
    MONGODB_SOCKET_TIMEOUT_MS: int = 10000

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in ["development", "test", "production"]:
            raise ValueError(f"Invalid APP_ENV: '{v}'. Must be one of: development, test, production.")
        return v_lower

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v: Optional[str]) -> Optional[str]:
        # Skip validation during tests to allow offline mock behaviors
        if os.getenv("APP_ENV") == "test" or (v and v.lower() == "test"):
            return v
        if not v or v.strip() == "" or v == "PASTE_YOUR_ACTUAL_API_KEY_HERE":
            raise ValueError("GEMINI_API_KEY environment variable is missing or has not been configured in your .env file.")
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> 'Settings':
        if self.APP_ENV == "production":
            # 1. Require critical backend keys
            if not self.MONGODB_URI:
                raise ValueError("MONGODB_URI is required in production environment.")
            if not self.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is required in production environment.")

            # 2. Reject credentials placeholders in production
            if self.GEMINI_API_KEY == "PASTE_YOUR_ACTUAL_API_KEY_HERE" or "your-gemini" in self.GEMINI_API_KEY.lower():
                raise ValueError("GEMINI_API_KEY must not contain default placeholders in production.")
            if "mongodb+srv://user:pass" in self.MONGODB_URI:
                raise ValueError("MONGODB_URI must not contain default placeholders in production.")

            # 3. Reject default local CORS and API URLs in production
            for origin in self.ALLOWED_ORIGINS:
                if "localhost" in origin or "127.0.0.1" in origin:
                    raise ValueError(f"Localhost CORS origin '{origin}' is not permitted in production.")

            # 4. Prevent Antigravity brain paths in production
            if self.EVALUATION_OUTPUT_DIR and "antigravity-ide" in str(self.EVALUATION_OUTPUT_DIR):
                raise ValueError("EVALUATION_OUTPUT_DIR cannot point to development/sandbox directories in production.")

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

# Set environment variables for Hugging Face and SentenceTransformers cache
# to guarantee local, repeatable, and container-safe model caching.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
abs_hf_home = os.path.abspath(os.path.join(project_root, settings.HF_HOME))
os.environ["HF_HOME"] = abs_hf_home
os.environ["SENTENCE_TRANSFORMERS_HOME"] = os.path.join(abs_hf_home, "sentence_transformers")
