from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="The unique, trimmed, and normalized email address of the user.")
    full_name: str = Field(..., min_length=2, max_length=100, description="The user's full name.")
    role: UserRole = Field(UserRole.USER, description="The user's role (user or admin).")
    is_active: bool = Field(True, description="Indicates if the user is active.")
    is_verified: bool = Field(False, description="Indicates if the user is verified.")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            # Trim whitespace and convert to lowercase for deterministic checks
            return v.strip().lower()
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Full name cannot be empty or only whitespace.")
        return trimmed

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="The user's raw password.")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit.")
        # Special character checklist
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        if not any(char in special_chars for char in v):
            raise ValueError("Password must contain at least one special character.")
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    last_login: Optional[datetime] = None
    refresh_token_version: Optional[int] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> Optional[str]:
        if isinstance(v, str):
            return v.strip().lower()
        return v

class UserRead(UserBase):
    id: str = Field(..., alias="_id", description="The database primary key string ID.")
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, v: Any) -> str:
        return str(v)

class UserInDB(UserBase):
    id: str = Field(..., alias="_id")
    password_hash: str
    refresh_token_version: int = 1
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, v: Any) -> str:
        return str(v)

class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="The user's email address.")
    password: str = Field(..., min_length=8, description="The user's password.")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation.")
    full_name: str = Field(..., min_length=2, max_length=100, description="The user's full name.")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("full_name", "password", "confirm_password", mode="before")
    @classmethod
    def trim_strings(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def validate_registration_payload(self) -> 'UserRegister':
        if self.password != self.confirm_password:
            raise ValueError("passwords do not match")
        
        # Validate password strength
        v = self.password
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit.")
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        if not any(char in special_chars for char in v):
            raise ValueError("Password must contain at least one special character.")
            
        # Validate full_name not empty
        if not self.full_name:
            raise ValueError("Full name cannot be empty or only whitespace.")
        return self

class UserRegisterResponse(BaseModel):
    id: str = Field(..., alias="id")
    email: EmailStr
    full_name: str
    role: UserRole
    created_at: datetime
    message: str = "User registered successfully"

    model_config = ConfigDict(
        populate_by_name=True
    )

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, v: Any) -> str:
        return str(v)

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="The user's email address.")
    password: str = Field(..., description="The user's password.")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="The refresh token issued during login.")

class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


