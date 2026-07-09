import logging
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from config.config import settings

logger = logging.getLogger("customer_support_backend")

class GeminiLLMService:
    """
    Service wrapper for Google's Gemini generative AI models.
    Provides decoupled, reusable methods for generating fact-grounded text.
    """
    _client: Optional[genai.Client] = None

    @classmethod
    def _initialize_sdk(cls, timeout: Optional[float] = None) -> None:
        """Lazily configures the GenAI client to prevent startup failure if key is missing during initialization."""
        if cls._client is None:
            # Pydantic validates key presence on startup, but we double-check here
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "PASTE_YOUR_ACTUAL_API_KEY_HERE":
                raise ValueError("GEMINI_API_KEY environment variable is missing or not configured correctly.")
            
            client_timeout = timeout if timeout is not None else settings.GEMINI_TIMEOUT
            
            logger.info("Initializing Google GenAI client credentials...")
            cls._client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=int(client_timeout * 1000))
            )

    @classmethod
    def generate_response(
        cls,
        user_query: str,
        system_instruction: Optional[str] = None,
        kb_context: Optional[List[Dict[str, Any]]] = None,
        agent_identity: Optional[str] = None,
        timeout: float = 30.0,
        history: Optional[List[dict]] = None
    ) -> str:
        """
        Generates a text completion response.
        
        Args:
            user_query: The main query string input by the customer.
            system_instruction: High-level model prompts mapping specialized agent behaviors.
            kb_context: Context chunks retrieved from FAISS database.
            agent_identity: Name of active agent (e.g. Technical Agent).
            timeout: API call deadline timeout in seconds.
            history: Optional list of conversation turns.
            
        Returns:
            The generated response string.
        """
        cls._initialize_sdk(timeout=timeout)
        
        try:
            model_name = settings.GEMINI_MODEL_NAME or "gemini-2.5-flash"
            logger.info(f"Submitting completion request to Gemini model '{model_name}' for agent identity: '{agent_identity or 'default'}'")
            
            # Build prompt with facts-grounding section
            prompt_parts = []
            
            if kb_context:
                prompt_parts.append("### Grounding Context (Use only facts from this context where possible):")
                for i, chunk in enumerate(kb_context, start=1):
                    content = chunk.get("content", "")
                    source = chunk.get("metadata", {}).get("source", "unknown")
                    prompt_parts.append(f"Context [{i}] (Source: {source}):\n{content}\n")
                prompt_parts.append("---")
            
            if history:
                prompt_parts.append("### Prior Conversation History:")
                for turn in history:
                    role = "Customer" if turn["role"] == "user" else "Assistant"
                    prompt_parts.append(f"{role}: {turn['content']}")
                prompt_parts.append("---")

            if agent_identity:
                prompt_parts.append(f"You are speaking as the {agent_identity}. Keep answers concise, factual, and professional.")
                
            prompt_parts.append(f"### User Query:\n{user_query}")
            full_prompt = "\n".join(prompt_parts)
            
            # Build configuration using types.GenerateContentConfig
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1000,
                system_instruction=system_instruction
            )
            
            import time
            start_time = time.perf_counter()
            logger.info({
                "event": "llm_generation_started",
                "model": model_name
            })
            
            from utils.resilience import retry_gemini_call
            
            # Execute request via the new google-genai SDK wrapped in retry with backoff/jitter
            response = retry_gemini_call(
                cls._client.models.generate_content,
                model=model_name,
                contents=full_prompt,
                config=config
            )
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            if not response or not response.text:
                logger.warning({
                    "event": "llm_generation_completed",
                    "model": model_name,
                    "success": False,
                    "detail": "empty text",
                    "duration_ms": duration_ms
                })
                return "I apologize, but I could not formulate an answer right now. Please try again."
                
            logger.info({
                "event": "llm_generation_completed",
                "model": model_name,
                "success": True,
                "duration_ms": duration_ms
            })
            return response.text
            
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000) if 'start_time' in locals() else 0
            logger.error({
                "event": "llm_generation_failed",
                "model": model_name,
                "exception_type": type(e).__name__,
                "error_detail": str(e),
                "duration_ms": duration_ms
            })
            # Do not expose raw SDK exceptions directly to users
            raise RuntimeError("The AI customer assistant is currently unavailable. Please try again later.")
