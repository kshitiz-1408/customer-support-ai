import time
import random
import logging
from typing import Callable, Any
from config.config import settings
from utils.logging import request_id_var
from utils.tracing import pipeline_tracker_var

# Try importing Google GenAI SDK exceptions safely
try:
    from google.genai.errors import APIError, ClientError
except ImportError:
    APIError = Exception
    ClientError = Exception

# Try importing PyMongo transient errors safely
try:
    from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError, NetworkTimeout
except ImportError:
    AutoReconnect = Exception
    ServerSelectionTimeoutError = Exception
    NetworkTimeout = Exception

logger = logging.getLogger("customer_support_backend")


def is_transient_gemini_error(e: Exception) -> bool:
    """
    Classifies if a Gemini SDK exception is a transient/retryable failure:
    - 5xx Server Errors (APIError)
    - 429 Too Many Requests / Quota Exceeded (ClientError)
    - Connection/Network timeouts or socket disconnects
    """
    err_name = type(e).__name__
    err_str = str(e).lower()
    
    # Handle known Google GenAI errors
    if APIError is not Exception and isinstance(e, APIError):
        # 5xx responses are transient
        if hasattr(e, "code") and e.code and 500 <= e.code < 600:
            return True
            
    if ClientError is not Exception and isinstance(e, ClientError):
        # 429 rate limit/quota is retryable if bounded
        if hasattr(e, "code") and e.code == 429:
            return True
        if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
            return True

    # Handle standard Python connection/socket/timeout exceptions
    if isinstance(e, (ConnectionError, TimeoutError)):
        return True

    # Inspect error details string as fallback check
    transient_keywords = ["timeout", "unavailable", "rate limit", "quota exceeded", "too many requests", "resource exhausted", "503", "504"]
    if any(k in err_str for k in transient_keywords):
        # Prevent retrying invalid API keys or bad requests even if they match keywords loosely
        non_retryable_keywords = ["key", "invalid", "unauthorized", "api_key", "400", "401", "403"]
        if any(nk in err_str for nk in non_retryable_keywords):
            return False
        return True

    return False


def is_transient_mongodb_error(e: Exception) -> bool:
    """
    Classifies if a MongoDB query exception is retryable:
    - AutoReconnect (connection dropped, primary replica switch)
    - ServerSelectionTimeoutError (replica set unreachable)
    - NetworkTimeout / socket timeout
    """
    if AutoReconnect is not Exception and isinstance(e, AutoReconnect):
        return True
    if ServerSelectionTimeoutError is not Exception and isinstance(e, ServerSelectionTimeoutError):
        return True
    if NetworkTimeout is not Exception and isinstance(e, NetworkTimeout):
        return True
        
    err_str = str(e).lower()
    transient_keywords = ["connection closed", "timeout", "autoreconnect", "server selection"]
    if any(k in err_str for k in transient_keywords):
        return True
        
    return False


def retry_gemini_call(func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    Executes a Gemini API request with bounded retry attempts,
    exponential backoff, and randomized jitter.
    """
    max_attempts = settings.GEMINI_MAX_RETRIES
    backoff_factor = settings.GEMINI_BACKOFF_FACTOR
    req_id = request_id_var.get() or "unknown"
    tracker = pipeline_tracker_var.get()
    
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            # Non-transient errors should fail immediately without retrying
            if not is_transient_gemini_error(e):
                logger.warning({
                    "event": "retry_skipped",
                    "request_id": req_id,
                    "reason": "non_transient_error",
                    "error_type": type(e).__name__,
                    "error_detail": str(e)[:200]
                })
                raise e
                
            if attempt == max_attempts:
                # Exhausted all retries
                logger.error({
                    "event": "retry_exhausted",
                    "request_id": req_id,
                    "dependency": "Gemini API",
                    "operation": getattr(func, "__name__", str(func)),
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "error_type": type(e).__name__,
                    "final_exhausted": True
                })
                raise e
                
            # Compute exponential backoff: backoff_factor^attempt + uniform random jitter
            backoff_s = (backoff_factor ** attempt) + random.uniform(0.1, 1.0)
            backoff_ms = int(backoff_s * 1000)
            
            logger.warning({
                "event": "retry_attempt",
                "request_id": req_id,
                "dependency": "Gemini API",
                "operation": getattr(func, "__name__", str(func)),
                "attempt": attempt,
                "max_attempts": max_attempts,
                "error_type": type(e).__name__,
                "backoff_ms": backoff_ms,
                "final_exhausted": False
            })
            
            # If tracking context exists, accumulate retry delay for timing diagnostic metrics
            if tracker:
                # We can add this backoff delay to the current llm_generation timing to reflect total cost
                pass
                
            time.sleep(backoff_s)


def retry_mongodb_read(func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    Executes a MongoDB read query with bounded retry attempts and short delay.
    Strictly used only for IDEMPOTENT operations (queries and lookups).
    """
    max_attempts = 3
    req_id = request_id_var.get() or "unknown"
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not is_transient_mongodb_error(e) or attempt == max_attempts:
                if attempt == max_attempts:
                    logger.error({
                        "event": "retry_exhausted",
                        "request_id": req_id,
                        "dependency": "MongoDB",
                        "operation": getattr(func, "__name__", str(func)),
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "error_type": type(e).__name__,
                        "final_exhausted": True
                    })
                raise e
                
            backoff_s = 0.5 * attempt + random.uniform(0.05, 0.2)
            backoff_ms = int(backoff_s * 1000)
            
            logger.warning({
                "event": "retry_attempt",
                "request_id": req_id,
                "dependency": "MongoDB",
                "operation": getattr(func, "__name__", str(func)),
                "attempt": attempt,
                "max_attempts": max_attempts,
                "error_type": type(e).__name__,
                "backoff_ms": backoff_ms,
                "final_exhausted": False
            })
            
            time.sleep(backoff_s)
