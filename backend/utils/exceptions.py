from fastapi import status
from utils.errors import AppException

class AuthException(AppException):
    """Base exception for all auth/user errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, status_code)

class DuplicateEmailException(AuthException):
    """Raised when registering a user with an email that is already registered."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)

class InvalidPasswordException(AuthException):
    """Raised when password strength or verification fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)

class InvalidEmailException(AuthException):
    """Raised when email validation or structure is invalid."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)

class DatabaseFailureException(AppException):
    """Raised when a MongoDB operation fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InvalidCredentialsException(AuthException):
    """Raised when authentication fails due to incorrect credentials."""
    def __init__(self, message: str = "Incorrect email or password"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)

class InactiveAccountException(AuthException):
    """Raised when an inactive user tries to perform authenticated actions."""
    def __init__(self, message: str = "Inactive user account"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)

class InvalidTokenException(AuthException):
    """Raised when a token is invalid, malformed, or of the wrong type."""
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)

class ExpiredTokenException(AuthException):
    """Raised when a token is expired."""
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


