def route_intent(message):
    """
    Determina qué dominios de memoria inyectar basándose en la intención.
    """
    msg = message.lower()
    mapping = {
        "work": ["taxfix", "job", "office", " Vincent", "Jose"],
        "family": ["maría", "benja", "familia", "school", "gym"],
        "projects": ["lastingnote", "cryptography", "coding", "next.js"],
        "infrastructure": ["tailscale", "server", "home", "lights", "blinds"]
    }
    
    active_domains = []
    for domain, keywords in mapping.items():
        if any(k in msg for k in keywords):
            active_domains.append(domain)
            
    return active_domains if active_domains else ["general"]
