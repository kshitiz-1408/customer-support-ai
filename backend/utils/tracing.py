import time
import logging
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Dict, Any, Optional
from utils.logging import request_id_var

logger = logging.getLogger("customer_support_backend")

class PipelineTracker:
    """
    Tracks statuses, start times, and durations of all stages in a request pipeline,
    along with fine-grained performance and database latency metrics.
    """
    def __init__(self):
        # Maps stage_name -> {status: "PASS"/"FAIL"/"NOT_RUN", duration_ms: float, error: str}
        self.stages: Dict[str, Dict[str, Any]] = {
            "http_request": {"status": "NOT_RUN", "duration_ms": 0.0},
            "chat_endpoint": {"status": "NOT_RUN", "duration_ms": 0.0},
            "conversation_resolution": {"status": "NOT_RUN", "duration_ms": 0.0},
            "user_persistence": {"status": "NOT_RUN", "duration_ms": 0.0},
            "intent_detection": {"status": "NOT_RUN", "duration_ms": 0.0},
            "agent_routing": {"status": "NOT_RUN", "duration_ms": 0.0},
            "history_loading": {"status": "NOT_RUN", "duration_ms": 0.0},
            "rag_retrieval": {"status": "NOT_RUN", "duration_ms": 0.0},
            "context_construction": {"status": "NOT_RUN", "duration_ms": 0.0},
            "llm_generation": {"status": "NOT_RUN", "duration_ms": 0.0},
            "assistant_persistence": {"status": "NOT_RUN", "duration_ms": 0.0},
            "response_serialization": {"status": "NOT_RUN", "duration_ms": 0.0},
        }
        self.first_failure: Optional[str] = None
        self.intent: Optional[str] = None
        self.agent: Optional[str] = None
        self.conversation_id: Optional[str] = None
        self.retrieval_count: int = 0
        self.llm_success: bool = True
        self.persistence_success: bool = True
        self.start_times: Dict[str, float] = {}

        # Fine-grained performance timings
        self.embedding_generation_ms: float = 0.0
        self.faiss_search_ms: float = 0.0
        self.db_conversation_lookup_ms: float = 0.0
        self.db_conversation_creation_ms: float = 0.0
        self.db_user_message_insert_ms: float = 0.0
        self.db_history_query_ms: float = 0.0
        self.db_assistant_message_insert_ms: float = 0.0
        self.db_ticket_create_ms: float = 0.0
        self.db_ticket_list_ms: float = 0.0
        self.db_ticket_update_ms: float = 0.0
        self.db_ticket_delete_ms: float = 0.0

    def get_performance_summary(self, total_duration_ms: float) -> Dict[str, Any]:
        """
        Calculates and returns a performance summary, identifying the dominant stage,
        secondary stage, exact percentages, and unmeasured time.
        """
        exclude = {"http_request", "chat_endpoint"}
        measured_stages = {
            name: data["duration_ms"]
            for name, data in self.stages.items()
            if name not in exclude and data["status"] != "NOT_RUN"
        }
        
        # Sort stages by duration descending
        sorted_stages = sorted(measured_stages.items(), key=lambda x: x[1], reverse=True)
        
        dominant_stage = "none"
        dominant_duration = 0.0
        second_stage = "none"
        second_duration = 0.0
        
        if len(sorted_stages) > 0:
            dominant_stage, dominant_duration = sorted_stages[0]
        if len(sorted_stages) > 1:
            second_stage, second_duration = sorted_stages[1]
            
        dominant_pct = (dominant_duration / total_duration_ms * 100.0) if total_duration_ms > 0 else 0.0
        
        # Calculate sum of all sub-stages to find unmeasured time
        sum_measured = sum(measured_stages.values())
        unmeasured_time = max(0.0, total_duration_ms - sum_measured)
        
        return {
            "dominant_stage": dominant_stage,
            "dominant_stage_duration_ms": dominant_duration,
            "dominant_stage_percentage": dominant_pct,
            "second_dominant_stage": second_stage,
            "second_dominant_stage_duration_ms": second_duration,
            "unmeasured_time_ms": unmeasured_time
        }

pipeline_tracker_var: ContextVar[Optional[PipelineTracker]] = ContextVar("pipeline_tracker", default=None)


def start_stage(stage: str):
    """Marks a stage as started and records its monotonic start time."""
    tracker = pipeline_tracker_var.get()
    if not tracker:
        return
    tracker.start_times[stage] = time.perf_counter()
    tracker.stages[stage]["status"] = "RUNNING"
    
    logger.info({
        "event": "pipeline_stage_started",
        "request_id": request_id_var.get(),
        "stage": stage,
        "conversation_id": tracker.conversation_id,
        "intent": tracker.intent,
        "agent": tracker.agent
    })


def complete_stage(stage: str, extra_meta: Optional[Dict[str, Any]] = None):
    """Marks a stage as successfully completed and calculates its duration."""
    tracker = pipeline_tracker_var.get()
    if not tracker:
        return
    start = tracker.start_times.get(stage)
    duration_ms = 0.0
    if start:
        duration_ms = (time.perf_counter() - start) * 1000.0
    
    tracker.stages[stage]["status"] = "PASS"
    tracker.stages[stage]["duration_ms"] = duration_ms
    
    payload = {
        "event": "pipeline_stage_completed",
        "request_id": request_id_var.get(),
        "stage": stage,
        "conversation_id": tracker.conversation_id,
        "intent": tracker.intent,
        "agent": tracker.agent,
        "duration_ms": duration_ms,
        "success": True
    }
    if extra_meta:
        payload.update(extra_meta)
    logger.info(payload)


def fail_stage(stage: str, error: Exception, extra_meta: Optional[Dict[str, Any]] = None):
    """Marks a stage as failed, records the error type/summary, and records first failure."""
    tracker = pipeline_tracker_var.get()
    if not tracker:
        return
    start = tracker.start_times.get(stage)
    duration_ms = 0.0
    if start:
        duration_ms = (time.perf_counter() - start) * 1000.0
        
    tracker.stages[stage]["status"] = "FAIL"
    tracker.stages[stage]["duration_ms"] = duration_ms
    tracker.stages[stage]["error"] = str(error)
    
    if not tracker.first_failure:
        tracker.first_failure = stage
        
    payload = {
        "event": "pipeline_stage_failed",
        "request_id": request_id_var.get(),
        "stage": stage,
        "conversation_id": tracker.conversation_id,
        "intent": tracker.intent,
        "agent": tracker.agent,
        "duration_ms": duration_ms,
        "success": False,
        "error_type": type(error).__name__,
        "safe_error_summary": str(error)[:200]
    }
    if extra_meta:
        payload.update(extra_meta)
    logger.error(payload)


@contextmanager
def trace_stage(stage: str, extra_meta: Optional[Dict[str, Any]] = None):
    """Context manager to easily track execution boundaries of a pipeline stage."""
    start_stage(stage)
    try:
        yield
        complete_stage(stage, extra_meta)
    except Exception as e:
        fail_stage(stage, e, extra_meta)
        raise e
