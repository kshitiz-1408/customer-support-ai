def process_query(query: str) -> dict:
    """
    Processes a product catalog query using RAG + Gemini.
    """
    from agents.router import process_agent_query
    return process_agent_query("Product Agent", query)
