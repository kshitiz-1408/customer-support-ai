import logging
from datetime import datetime, timezone
from fastapi import APIRouter, status, Depends, Request
from models.user import (
    UserRegister, UserRegisterResponse, UserCreate,
    UserLogin, TokenResponse, TokenRefreshRequest, TokenRefreshResponse,
    UserRead, UserUpdate
)
from services.user_service import UserService
from utils.auth import (
    verify_password, create_access_token, create_refresh_token, decode_token
)
from utils.exceptions import (
    InvalidCredentialsException, InactiveAccountException, InvalidTokenException
)
from api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger("customer_support_backend")


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user, hashes their password, and returns the created user's basic information without sensitive fields.",
)
def register_user(user_in: UserRegister):
    logger.info(f"Initiating registration request for email: {user_in.email}")
    
    from models.user import UserRole
    # Map UserRegister to UserCreate explicitly forcing role to 'user'
    user_create = UserCreate(
        email=user_in.email,
        full_name=user_in.full_name,
        password=user_in.password,
        role=UserRole.USER
    )
    
    created_user = UserService.create_user(user_create)
    
    return UserRegisterResponse(
        id=created_user.id,
        email=created_user.email,
        full_name=created_user.full_name,
        role=created_user.role,
        created_at=created_user.created_at,
        message="User registered successfully"
    )

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticates credentials and returns access and refresh tokens.",
)
def login(user_in: UserLogin, request: Request):
    logger.info(f"Initiating login request for email: {user_in.email}")
    
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    
    from services.audit_service import AuditService
    user = UserService.get_user_by_email(user_in.email)
    if not user:
        AuditService.log_action(
            admin_id=None,
            target_user_id=None,
            action="login_failed",
            previous_value=None,
            new_value=user_in.email,
            resource_type="user",
            status="failed",
            ip_address=ip,
            user_agent=ua,
            additional_metadata={"reason": "user_not_found"}
        )
        raise InvalidCredentialsException()
        
    if not verify_password(user_in.password, user.password_hash):
        AuditService.log_action(
            admin_id=None,
            target_user_id=user.id,
            action="login_failed",
            previous_value=None,
            new_value=user_in.email,
            resource_type="user",
            status="failed",
            ip_address=ip,
            user_agent=ua,
            additional_metadata={"reason": "invalid_password"}
        )
        raise InvalidCredentialsException()
        
    if not user.is_active:
        AuditService.log_action(
            admin_id=None,
            target_user_id=user.id,
            action="login_failed",
            previous_value=None,
            new_value=user_in.email,
            resource_type="user",
            status="failed",
            ip_address=ip,
            user_agent=ua,
            additional_metadata={"reason": "inactive_account"}
        )
        raise InactiveAccountException()
        
    # Generate tokens
    access_token = create_access_token(user.id, user.email, user.role.value if hasattr(user.role, 'value') else user.role)
    refresh_token = create_refresh_token(user.id, user.email, user.refresh_token_version)
    
    # Update last login
    UserService.update_user(user.id, UserUpdate(last_login=datetime.now(timezone.utc)))
    
    # Success audit
    AuditService.log_action(
        admin_id=user.id,
        target_user_id=user.id,
        action="login",
        previous_value=None,
        new_value=user.email,
        resource_type="user",
        status="success",
        ip_address=ip,
        user_agent=ua
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Validates a refresh token and returns a new access token.",
)
def refresh(refresh_in: TokenRefreshRequest):
    logger.info("Initiating token refresh request")
    
    payload = decode_token(refresh_in.refresh_token)
    if payload.get("type") != "refresh":
        raise InvalidTokenException("Invalid token type")
        
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenException("Missing user identity in token")
        
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise InvalidTokenException("User not found")
        
    if not user.is_active:
        raise InactiveAccountException()
        
    # Verify version matching for token invalidation/revocation
    token_version = payload.get("version")
    if token_version != user.refresh_token_version:
        raise InvalidTokenException("Token has been revoked or invalidated")
        
    # Generate new access token
    access_token = create_access_token(user.id, user.email, user.role.value if hasattr(user.role, 'value') else user.role)
    
    return TokenRefreshResponse(
        access_token=access_token
    )

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Revokes current user session by incrementing refresh token version.",
)
def logout(request: Request, current_user=Depends(get_current_user)):
    logger.info(f"Initiating logout request for user: {current_user.email}")
    
    new_version = current_user.refresh_token_version + 1
    UserService.update_user(current_user.id, UserUpdate(refresh_token_version=new_version))
    
    from services.audit_service import AuditService
    AuditService.log_action(
        admin_id=current_user.id,
        target_user_id=current_user.id,
        action="logout",
        previous_value=None,
        new_value=current_user.email,
        resource_type="user",
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"message": "Logged out successfully"}

@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user details",
    description="Retrieves profile information for the authenticated user.",
)
def get_me(current_user=Depends(get_current_user)):
    return current_user

