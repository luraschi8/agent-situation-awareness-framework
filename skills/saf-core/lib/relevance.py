def check_relevance(action, user_state):
    # Lógica simplificada del Relevance Gate
    mode = user_state.get("override_mode")
    if mode == "vacation" and action == "weekly_menu":
        return False
    return True
