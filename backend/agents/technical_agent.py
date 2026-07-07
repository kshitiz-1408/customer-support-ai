from typing import Optional

def process_query(query: str, conversation_id: Optional[str] = None, session_id: Optional[str] = None) -> dict:
    """
    Processes a technical support query using RAG + Gemini.
    """
    from agents.router import process_agent_query
    return process_agent_query("Technical Agent", query, conversation_id, session_id)
