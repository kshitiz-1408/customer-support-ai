from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from utils.logging import logger


class AppException(Exception):
    """Base exception for the application."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ResourceNotFoundException(AppException):
    """Exception raised when a resource is not found."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class BadRequestException(AppException):
    """Exception raised for bad requests."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


def register_error_handlers(app: FastAPI):
    """
    Register exception handlers for the FastAPI application.
    """
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.error(f"AppException: {exc.message} on path {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Format the validation error list to a cleaner message
        errors = []
        for err in exc.errors():
            loc = " -> ".join([str(x) for x in err.get("loc", [])])
            msg = err.get("msg", "invalid field format")
            errors.append(f"[{loc}]: {msg}")
            
        error_msg = "; ".join(errors)
        logger.error(f"Validation error: {error_msg} on path {request.url.path}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": f"Validation failed: {error_msg}", "errors": jsonable_encoder(exc.errors())}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.critical(f"Unhandled Exception: {str(exc)} on path {request.url.path}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."}
        )
