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
    def _initialize_sdk(cls, timeout: float = 30.0) -> None:
        """Lazily configures the GenAI client to prevent startup failure if key is missing during initialization."""
        if cls._client is None:
            # Pydantic validates key presence on startup, but we double-check here
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "PASTE_YOUR_ACTUAL_API_KEY_HERE":
                raise ValueError("GEMINI_API_KEY environment variable is missing or not configured correctly.")
            
            logger.info("Initializing Google GenAI client credentials...")
            cls._client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=int(timeout * 1000))
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
            
            # Execute request via the new google-genai SDK
            response = cls._client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=config
            )
            
            if not response or not response.text:
                logger.warning("Gemini API returned empty text response.")
                return "I apologize, but I could not formulate an answer right now. Please try again."
                
            return response.text
            
        except Exception as e:
            logger.error(f"Generative completion failed: {str(e)}", exc_info=True)
            # Do not expose raw SDK exceptions directly to users
            raise RuntimeError("The AI customer assistant is currently unavailable. Please try again later.")
