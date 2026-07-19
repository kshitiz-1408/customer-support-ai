from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from api.deps import get_current_user
from models.user import UserRead, UserInDB, UserUpdate
from services.user_service import UserService
from utils.auth import verify_password, hash_password

router = APIRouter()


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Full name cannot be empty or only whitespace.")
            return trimmed
        return v


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit.")
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        if not any(char in special_chars for char in v):
            raise ValueError("Password must contain at least one special character.")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


@router.get("/me", response_model=UserRead)
def get_user_profile(current_user: UserInDB = Depends(get_current_user)):
    """Retrieve profile details for the authenticated user."""
    return current_user


@router.patch("/me", response_model=UserRead)
def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: UserInDB = Depends(get_current_user)
):
    """Update profile details for the authenticated user (only full_name is modifiable)."""
    if profile_update.full_name is None:
        return current_user
        
    updated = UserService.update_user(
        current_user.id,
        UserUpdate(full_name=profile_update.full_name)
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    pwd_req: PasswordChangeRequest,
    request: Request,
    current_user: UserInDB = Depends(get_current_user)
):
    """Securely change password for the authenticated user and invalidate active refresh tokens."""
    # 1. Verify current password matches
    if not verify_password(pwd_req.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
        
    # 2. Prevent setting same password as old
    if verify_password(pwd_req.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password."
        )

    # 3. Hash the new password and apply updates
    new_hash = hash_password(pwd_req.new_password)
    updated = UserService.change_password(current_user.id, new_hash)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    from services.audit_service import AuditService
    AuditService.log_action(
        admin_id=current_user.id,
        target_user_id=current_user.id,
        action="password_changed",
        previous_value="[REDACTED]",
        new_value="[REDACTED]",
        resource_type="user",
        resource_id=current_user.id,
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
        
    return {"message": "Password changed successfully. Existing sessions have been invalidated."}
