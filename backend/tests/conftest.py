import os
import sys
import pytest

# Ensure backend root is in the import path before any other imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Override MONGODB_URI to force mock database for all tests
os.environ["MONGODB_URI"] = ""
os.environ["APP_ENV"] = "test"
os.environ["GEMINI_API_KEY"] = "test"

@pytest.fixture(autouse=True)
def clean_mock_db():
    from database.database import get_mock_db_file
    mock_file = get_mock_db_file()
    if mock_file.exists():
        try:
            os.remove(mock_file)
        except OSError:
            pass
    yield
    if mock_file.exists():
        try:
            os.remove(mock_file)
        except OSError:
            pass
