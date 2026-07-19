from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.config import settings
from utils.auth import decode_token
from utils.exceptions import InvalidTokenException, InactiveAccountException, ForbiddenException
from services.user_service import UserService
from models.user import UserInDB, UserCreate, UserRole

# Make auto_error False to allow manual handling and fallback in test mode
security = HTTPBearer(auto_error=False)

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> UserInDB:
    """
    Dependency that extracts the Bearer token, validates it, and fetches the corresponding
    active user. Falls back to a default test user if no credentials are provided in APP_ENV='test'.
    """
    if not credentials:
        if settings.APP_ENV == "test":
            email = "test_default_user@example.com"
            user = UserService.get_user_by_email(email)
            if not user:
                user = UserService.create_user(UserCreate(
                    email=email,
                    full_name="Default Test User",
                    password="ValidPassword123!"
                ))
            return user
        raise InvalidTokenException("Not authenticated")
        
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload.get("type") != "access":
        raise InvalidTokenException("Invalid token type")
        
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenException("Missing user identity in token")
        
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise InvalidTokenException("User not found")
        
    if not user.is_active:
        raise InactiveAccountException()
        
    return user


def get_current_admin(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """
    Dependency that verifies the current user has the ADMIN role.
    """
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Insufficient permissions: Admin access required.")
    return current_user


