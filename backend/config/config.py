import json
from typing import List, Union
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
