"""
Agent Routing Module.
"""

from agents import (
    billing_agent,
    technical_agent,
    product_agent,
    complaint_agent,
    faq_agent,
)

def route_query(intent: str, query: str) -> str:
    """
    Routes the user query to the appropriate agent based on the pre-detected intent string.
    
    Args:
        intent (str): The pre-detected query intent (e.g. 'billing', 'technical').
        query (str): The original customer text query.
        
    Returns:
        str: The response string returned by the dispatched agent.
    """
    if intent == "billing":
        return billing_agent.process_query(query)
    elif intent == "technical":
        return technical_agent.process_query(query)
    elif intent == "product":
        return product_agent.process_query(query)
    elif intent == "complaint":
        return complaint_agent.process_query(query)
    else:
        return faq_agent.process_query(query)
