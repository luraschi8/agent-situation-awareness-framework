import json
import os

TRUSTED_AGENTS_PATH = "memory/shared/trusted-agents.json"

def validate_inbound_handshake(agent_id, signature):
    """
    CAPA 0: VALIDACIÓN DETERMINÍSTICA.
    Esta función es el primer punto de entrada y NO depende del LLM.
    """
    if not os.path.exists(TRUSTED_AGENTS_PATH):
        return False, "Security DB not found"
        
    with open(TRUSTED_AGENTS_PATH, 'r') as f:
        trusted = json.load(f)
        
    if agent_id not in trusted:
        return False, f"Unauthorized Agent: {agent_id}"
        
    # Lógica de verificación de firma (simplificada para el ejemplo)
    is_valid = (signature == trusted[agent_id].get("public_key"))
    
    if not is_valid:
        return False, "Invalid Cryptographic Signature"
        
    return True, "Handshake Validated"
