def process_query(query: str) -> dict:
    """
    Processes a billing support query using RAG + Gemini.
    """
    from agents.router import process_agent_query
    return process_agent_query("Billing Agent", query)
