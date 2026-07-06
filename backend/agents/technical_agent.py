def process_query(query: str) -> dict:
    """
    Processes a technical support query using RAG + Gemini.
    """
    from agents.router import process_agent_query
    return process_agent_query("Technical Agent", query)
