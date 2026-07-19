import sys
import os
import secrets
import string
import json
from pathlib import Path

# 1. Determine Project Root and locate backend/.env
current_dir = Path(__file__).resolve().parent
env_path = None
project_root = None

# Check current directory
if (current_dir / "backend" / ".env").exists():
    env_path = current_dir / "backend" / ".env"
    project_root = current_dir
# Check parent directory (if running from scripts/)
elif (current_dir.parent / "backend" / ".env").exists():
    env_path = current_dir.parent / "backend" / ".env"
    project_root = current_dir.parent
# General parent lookup fallback
else:
    p = current_dir
    for _ in range(4):
        if (p / "backend" / ".env").exists():
            env_path = p / "backend" / ".env"
            project_root = p
            break
        p = p.parent

if not env_path or not project_root:
    print("Could not locate backend/.env")
    sys.exit(1)

# 2. Load backend/.env using python-dotenv before importing config/Settings
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)
except ImportError:
    print("Error: python-dotenv is not installed.")
    sys.exit(1)

# 3. Verify GEMINI_API_KEY is available
if not os.getenv("GEMINI_API_KEY"):
    print("backend/.env was found but GEMINI_API_KEY is missing.")
    sys.exit(1)

# 4. Setup Python path to include backend
backend_path = project_root / "backend"
sys.path.append(str(backend_path))

# Setup environment variables so config Settings works
os.environ.setdefault("APP_ENV", "development")

# Now import backend modules safely
try:
    from services.user_service import UserService
    from utils.auth import hash_password
    from models.user import UserRole
    from database.database import close_db, get_users_collection
    from datetime import datetime, timezone
except Exception as e:
    print(f"Error importing backend modules: {str(e)}")
    sys.exit(1)

def generate_secure_password(length=16):
    """Generates a strong secure password containing at least 1 uppercase, 1 lowercase, 1 digit, and 1 special char."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        has_upper = any(c.isupper() for c in pwd)
        has_lower = any(c.islower() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)
        has_spec = any(c in "!@#$%^&*" for c in pwd)
        if has_upper and has_lower and has_digit and has_spec:
            return pwd

def main():
    email = "admin@example.com"
    
    # Locate user in database
    try:
        user = UserService.get_user_by_email(email)
    except Exception as e:
        print("Error: Could not connect to MongoDB database. Please ensure it is running and the connection string is valid.")
        sys.exit(1)
        
    if not user:
        print(f"Error: Administrator with email '{email}' does not exist.")
        sys.exit(1)
        
    if user.role != UserRole.ADMIN:
        print(f"Error: User '{email}' is not an administrator (role: {user.role}).")
        close_db()
        sys.exit(1)
        
    new_pwd = generate_secure_password(16)
    hashed_pwd = hash_password(new_pwd)
    
    try:
        # Update user's password in database directly with timezone-aware datetime
        coll = get_users_collection()
        coll.update_one(
            {"_id": user.id},
            {"$set": {
                "password_hash": hashed_pwd,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        # Check if bootstrap_credentials.json exists and update it
        artifacts_dir = Path("C:/Users/HP/.gemini/antigravity-ide/brain/19a93036-5576-4401-8a01-827787595b36")
        creds_file = artifacts_dir / "bootstrap_credentials.json"
        if creds_file.exists():
            try:
                with open(creds_file, "r") as f:
                    data = json.load(f)
                data["password"] = new_pwd
                with open(creds_file, "w") as f:
                    json.dump(data, f)
            except Exception:
                pass

        print("==================================================")
        print("Administrator Password Reset Successful")
        print()
        print("Email:")
        print(email)
        print()
        print("New Password:")
        print(new_pwd)
        print()
        print("Role:")
        print("admin")
        print("==================================================")
        
    except Exception as e:
        print(f"Exception resetting password for administrator: {str(e)}")
        sys.exit(1)
    finally:
        close_db()

if __name__ == "__main__":
    main()
