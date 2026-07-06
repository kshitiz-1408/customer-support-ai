def process_query(query: str) -> dict:
    """
    Processes a customer complaint query using RAG + Gemini.
    """
    from agents.router import process_agent_query
    return process_agent_query("Complaint Agent", query)
