import pytest
import os
from pydantic import ValidationError
from config.config import Settings
from database.database import get_tickets_collection, db_connected

def test_app_env_validation():
    # Valid environments
    s_dev = Settings(APP_ENV="development")
    assert s_dev.APP_ENV == "development"
    
    s_test = Settings(APP_ENV="test")
    assert s_test.APP_ENV == "test"
    
    s_prod = Settings(
        APP_ENV="production",
        MONGODB_URI=os.getenv("MONGODB_URI"),
        GEMINI_API_KEY="real_key",
        JWT_SECRET_KEY="real_secret_key_12345",
        ALLOWED_ORIGINS=["https://my-production-app.com"]
    )
    assert s_prod.APP_ENV == "production"

    # Invalid environment name
    with pytest.raises(ValidationError):
        Settings(APP_ENV="staging")


def test_production_cors_restriction():
    # Production must reject localhost CORS origins
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            APP_ENV="production",
            MONGODB_URI="mongodb+srv://realuser:realpass@cluster.mongodb.net/db",
            GEMINI_API_KEY="real_key",
            JWT_SECRET_KEY="real_secret_key_12345",
            ALLOWED_ORIGINS=["http://localhost:3000"]
        )
    assert "CORS origin" in str(excinfo.value)


def test_production_placeholder_secrets_rejection():
    # Production must reject default API key placeholder
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            APP_ENV="production",
            MONGODB_URI="mongodb+srv://realuser:realpass@cluster.mongodb.net/db",
            GEMINI_API_KEY="PASTE_YOUR_ACTUAL_API_KEY_HERE",
            JWT_SECRET_KEY="real_secret_key_12345",
            ALLOWED_ORIGINS=["https://my-production-app.com"]
        )
    assert "GEMINI_API_KEY" in str(excinfo.value)

    # Production must reject default MongoDB URI placeholder
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            APP_ENV="production",
            MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/?appName=customer-support-ai",
            GEMINI_API_KEY="real_key",
            JWT_SECRET_KEY="real_secret_key_12345",
            ALLOWED_ORIGINS=["https://my-production-app.com"]
        )
    assert "MONGODB_URI must not contain default placeholders" in str(excinfo.value)


def test_production_antigravity_path_rejection():
    # Production must reject Antigravity brain paths
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            APP_ENV="production",
            MONGODB_URI="mongodb+srv://realuser:realpass@cluster.mongodb.net/db",
            GEMINI_API_KEY="real_key",
            JWT_SECRET_KEY="real_secret_key_12345",
            ALLOWED_ORIGINS=["https://my-production-app.com"],
            EVALUATION_OUTPUT_DIR="~/.gemini/antigravity-ide/brain/12345"
        )
    assert "EVALUATION_OUTPUT_DIR cannot point to development/sandbox" in str(excinfo.value)


def test_production_mock_fallback_disabled():
    # Verify that in production, if database is not connected, get_tickets_collection raises error
    # We monkeypatch settings to represent production
    from database import database
    
    # Store original settings and db_connected
    orig_env = database.settings.APP_ENV
    orig_connected = database.db_connected
    
    try:
        database.settings.APP_ENV = "production"
        database.db_connected = False
        
        with pytest.raises(RuntimeError) as excinfo:
            get_tickets_collection()
        assert "Mock collection 'tickets' is disabled in production" in str(excinfo.value)
    finally:
        database.settings.APP_ENV = orig_env
        database.db_connected = orig_connected


def test_production_jwt_secret_rejection():
    # Production must reject default JWT secret placeholder
    with pytest.raises(ValidationError) as excinfo:
        Settings(
            APP_ENV="production",
            MONGODB_URI="mongodb+srv://realuser:realpass@cluster.mongodb.net/db",
            GEMINI_API_KEY="real_key",
            JWT_SECRET_KEY="CHANGE_ME_SECRET_KEY_FOR_PRODUCTION",
            ALLOWED_ORIGINS=["https://my-production-app.com"]
        )
    assert "JWT_SECRET_KEY" in str(excinfo.value)

