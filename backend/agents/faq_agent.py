def process_query(query: str) -> dict:
    """
    Processes a general FAQ support query using RAG + Gemini.
    """
    from agents.router import process_agent_query
    return process_agent_query("FAQ Agent", query)
