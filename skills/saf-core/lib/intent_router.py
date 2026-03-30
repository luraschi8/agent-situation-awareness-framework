def get_relevant_domains(message):
    msg = message.lower()
    if "taxfix" in msg or "trabajo" in msg:
        return ["work"]
    if "benja" in msg or "familia" in msg or "maría" in msg:
        return ["family"]
    return ["work", "family", "personal_projects", "infrastructure"]
