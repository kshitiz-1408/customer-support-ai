from typing import Optional

def process_query(query: str, conversation_id: Optional[str] = None, session_id: Optional[str] = None) -> dict:
    """
    Processes a general FAQ support query using RAG + Gemini.
    """
    from agents.router import process_agent_query
    return process_agent_query("FAQ Agent", query, conversation_id, session_id)
