import uuid
import time
import re
from starlette.types import ASGIApp, Scope, Receive, Send
from utils.logging import logger, request_id_var
from utils.tracing import PipelineTracker, pipeline_tracker_var

# Simple validation regex: allow standard UUIDs or alphanumeric with hyphens (8-50 chars)
VALID_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{8,50}$")

class ObservabilityMiddleware:
    """
    ASGI Middleware that manages request correlation (X-Request-ID),
    ensures thread-isolated tracking via contextvars request_id_var,
    and logs request lifecycle start, completion, and failures.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # 1. Extract and validate X-Request-ID header, else generate UUID4
        headers = scope.get("headers", [])
        client_req_id = None
        for k, v in headers:
            if k.lower() == b"x-request-id":
                try:
                    client_req_id = v.decode("latin1")
                except Exception:
                    pass
                break

        if client_req_id and VALID_REQUEST_ID_RE.match(client_req_id):
            req_id = client_req_id
        else:
            req_id = str(uuid.uuid4())

        # 2. Bind to ContextVar (propagates down the execution context)
        token = request_id_var.set(req_id)
        
        # Initialize pipeline tracker and bind to ContextVar
        tracker = PipelineTracker()
        token_tracker = pipeline_tracker_var.set(tracker)
        
        # 3. Log request lifecycle start & start http_request stage
        start_time = time.perf_counter()
        tracker.start_times["http_request"] = start_time
        tracker.stages["http_request"]["status"] = "RUNNING"
        
        logger.info({
            "event": "request_started",
            "method": scope.get("method", "HTTP"),
            "route": scope.get("path", "/"),
            "request_id": req_id
        })

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Inject X-Request-ID header into the response headers list
                headers_list = list(message.get("headers", []))
                headers_list.append((b"x-request-id", req_id.encode("latin1")))
                message["headers"] = headers_list
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            
            # 4. Log request completion & mark http_request stage PASS
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            tracker.stages["http_request"]["status"] = "PASS"
            tracker.stages["http_request"]["duration_ms"] = duration_ms
            
            logger.info({
                "event": "request_completed",
                "method": scope.get("method", "HTTP"),
                "route": scope.get("path", "/"),
                "status_code": 200,  # ASGI level success
                "duration_ms": int(duration_ms),
                "request_id": req_id
            })
        except Exception as e:
            # 5. Log request failure & mark http_request stage FAIL
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            tracker.stages["http_request"]["status"] = "FAIL"
            tracker.stages["http_request"]["duration_ms"] = duration_ms
            tracker.stages["http_request"]["error"] = str(e)
            if not tracker.first_failure:
                tracker.first_failure = "http_request"
                
            logger.error({
                "event": "request_failed",
                "method": scope.get("method", "HTTP"),
                "route": scope.get("path", "/"),
                "exception_type": type(e).__name__,
                "safe_error_summary": str(e)[:200],
                "duration_ms": int(duration_ms),
                "request_id": req_id
            })
            raise e
        finally:
            # 6. Emit pipeline trace summary if used for chat routing
            if tracker.conversation_id or scope.get("path", "").endswith("/chat/"):
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                persistence_success = (
                    tracker.stages["user_persistence"]["status"] != "FAIL" and
                    tracker.stages["assistant_persistence"]["status"] != "FAIL"
                )
                llm_success = tracker.stages["llm_generation"]["status"] != "FAIL"
                final_status = "FAIL" if tracker.first_failure else "SUCCESS"
                
                logger.info({
                    "event": "pipeline_trace_summary",
                    "request_id": req_id,
                    "conversation_id": tracker.conversation_id,
                    "intent": tracker.intent,
                    "agent": tracker.agent,
                    "total_duration_ms": duration_ms,
                    "retrieval_count": tracker.retrieval_count,
                    "llm_success": llm_success,
                    "persistence_success": persistence_success,
                    "final_status": final_status
                })

                # Calculate performance timing summary
                perf = tracker.get_performance_summary(duration_ms)
                persistence_total_ms = (
                    tracker.stages["user_persistence"]["duration_ms"] +
                    tracker.stages["assistant_persistence"]["duration_ms"]
                )
                
                logger.info({
                    "event": "chat_performance_summary",
                    "request_id": req_id,
                    "conversation_id": tracker.conversation_id,
                    "total_duration_ms": duration_ms,
                    "intent_detection_ms": tracker.stages["intent_detection"]["duration_ms"],
                    "rag_retrieval_total_ms": tracker.stages["rag_retrieval"]["duration_ms"],
                    "gemini_generation_ms": tracker.stages["llm_generation"]["duration_ms"],
                    "persistence_total_ms": persistence_total_ms,
                    "dominant_stage": perf["dominant_stage"],
                    "dominant_stage_duration_ms": perf["dominant_stage_duration_ms"],
                    "dominant_stage_percentage": perf["dominant_stage_percentage"],
                    "second_dominant_stage": perf["second_dominant_stage"],
                    "second_dominant_stage_duration_ms": perf["second_dominant_stage_duration_ms"],
                    "unmeasured_time_ms": perf["unmeasured_time_ms"]
                })
            
            # Reset context variables to prevent leakage
            pipeline_tracker_var.reset(token_tracker)
            request_id_var.reset(token)
