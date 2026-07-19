import sys
import os
from pathlib import Path

# Setup Python path to include backend
PROJECT_ROOT = Path(__file__).resolve().parent.parent
backend_path = PROJECT_ROOT / "backend"
sys.path.append(str(backend_path))

# Setup environment variables so config works
os.environ.setdefault("APP_ENV", "development")

from services.user_service import UserService
from models.user import UserRole, UserUpdate
from database.database import close_db

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/promote_user.py <email>")
        sys.exit(1)
        
    email = sys.argv[1].strip().lower()
    
    user = UserService.get_user_by_email(email)
    if not user:
        print(f"Error: User with email '{email}' not found.")
        sys.exit(1)
        
    if user.role == UserRole.ADMIN:
        print(f"User '{email}' is already an administrator.")
        close_db()
        sys.exit(0)
        
    try:
        updated = UserService.update_user(user.id, UserUpdate(role=UserRole.ADMIN))
        if updated and updated.role == UserRole.ADMIN:
            print(f"Success: User '{email}' promoted to administrator.")
        else:
            print(f"Error: Failed to update role for user '{email}'.")
    except Exception as e:
        print(f"Exception promoting user '{email}': {str(e)}")
        sys.exit(1)
    finally:
        close_db()

if __name__ == "__main__":
    main()
