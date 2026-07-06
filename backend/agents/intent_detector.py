"""
Intent Detector Module.
"""

def detect_intent(query: str) -> dict:
    """
    Classifies the user query into one of the known agent categories using basic keyword heuristic mapping.
    If no category matches, returns 'unknown'.
    
    Categories:
    - 'billing': accounting, invoices, checkout, Stripe, refund, cost
    - 'technical': crash, bug, error, config, server, password, access, integration, webhooks
    - 'product': features, specs, release, cost plans, options, specifications
    - 'complaint': slow, terrible, bad, unhappy, escalate, grievance, supervisor, manager
    - 'faq': standard questions regarding hours, contact, support locations, etc.
    - 'unknown': default fallback category
    
    Returns:
        dict: {"intent": "billing" | "technical" | "product" | "complaint" | "faq" | "unknown"}
    """
    q_lower = query.lower()

    # Keywords associated with billing issues, invoices, payments, and subscription charges
    billing_keywords = [
        "refund",
        "billing",
        "invoice",
        "payment",
        "payments",
        "pay",
        "paid",
        "charge",
        "charged",
        "card",
        "credit card",
        "debit card",
        "receipt",
        "billing statement",
        "subscription payment"
    ]

    # Keywords associated with technical errors, logins, crashes, and server integrations
    technical_keywords = [
        "error",
        "errors",
        "bug",
        "bugs",
        "crash",
        "crashes",
        "login",
        "log in",
        "password",
        "server",
        "port",
        "api",
        "integration",
        "webhook",
        "failed",
        "failure",
        "issue",
        "problem",
        "cannot",
        "can't",
        "not working",
        "broken"
    ]

    # Keywords associated with product catalog details, versions, release dates, and pricing plans
    product_keywords = [
        "product",
        "products",
        "price",
        "prices",
        "pricing",
        "cost",
        "costs",
        "subscription",
        "subscriptions",
        "plan",
        "plans",
        "premium",
        "feature",
        "features",
        "spec",
        "specs",
        "specification",
        "specifications",
        "version",
        "release",
        "release date",
        "buy",
        "purchase",
        "available",
        "availability",
        "compare",
        "comparison",
        "upgrade",
        "license"
    ]

    # Keywords associated with customer complaints, grievances, and management escalation requests
    complaint_keywords = [
        "complaint",
        "complain",
        "bad",
        "terrible",
        "worst",
        "poor",
        "unhappy",
        "angry",
        "frustrated",
        "disappointed",
        "escalate",
        "grievance",
        "manager",
        "supervisor"
    ]

    # Keywords associated with support desk lookups, office location addresses, and general FAQ helpers
    faq_keywords = [
        "faq",
        "hours",
        "working hours",
        "office",
        "address",
        "location",
        "contact",
        "support",
        "email",
        "phone",
        "website",
        "how do i",
        "how to",
        "where is",
        "what is",
        "warranty",
        "warranties"
    ]

    # Classify the intent by matching query terms against keyword lists using clean any() checks
    if any(keyword in q_lower for keyword in billing_keywords):
        return {"intent": "billing"}
        
    if any(keyword in q_lower for keyword in technical_keywords):
        return {"intent": "technical"}
        
    if any(keyword in q_lower for keyword in product_keywords):
        return {"intent": "product"}
        
    if any(keyword in q_lower for keyword in complaint_keywords):
        return {"intent": "complaint"}
        
    if any(keyword in q_lower for keyword in faq_keywords):
        return {"intent": "faq"}

    # Fallback to unknown if no keywords matched
    return {"intent": "unknown"}
