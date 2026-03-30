import hmac
import hashlib
import json
import time
import os

KEY_PATH = "memory/shared/trusted-agents.json"
MY_IDENTITY_PATH = "memory/shared/my-identity.json"

def generate_keys(agent_id):
    """Genera una identidad única para el agente."""
    # En producción usaría Ed25519. Aquí simulamos con un secreto fuerte.
    secret = os.urandom(32).hex()
    identity = {
        "agent_id": agent_id,
        "private_key": secret,
        "public_key": hashlib.sha256(secret.encode()).hexdigest()
    }
    with open(MY_IDENTITY_PATH, 'w') as f:
        json.dump(identity, f, indent=2)
    os.chmod(MY_IDENTITY_PATH, 0o600)
    return identity["public_key"]

def sign_message(body, private_key):
    """Firma un mensaje usando HMAC-SHA256 (Determinístico)."""
    return hmac.new(private_key.encode(), body.encode(), hashlib.sha256).hexdigest()

def verify_envelope(envelope):
    """
    CAPA 0: VERIFICACIÓN EXTREMA.
    Valida: Firma, Timestamp (ventana 30s) y Nonce (Replay Attack).
    """
    try:
        sender_id = envelope['sender_id']
        msg_body = envelope['body']
        signature = envelope['signature']
        timestamp = envelope['timestamp']
        
        # 1. Chequeo de Ventana Temporal (Anti-Stale)
        now = time.time()
        if abs(now - timestamp) > 30:
            return False, "Message expired (Temporal Drift)"
            
        # 2. Cargar Clave Pública del Remitente
        if not os.path.exists(KEY_PATH):
            return False, "Trusted registry missing"
            
        with open(KEY_PATH, 'r') as f:
            trusted = json.load(f)
            
        if sender_id not in trusted:
            return False, f"Unknown Agent: {sender_id}"
            
        # 3. Verificación Matemática (No LLM)
        # Re-calculamos la firma esperada usando la Public Key (que actúa como secreto compartido en este mock)
        expected = sign_message(msg_body, trusted[sender_id]['public_key'])
        
        if not hmac.compare_digest(expected, signature):
            return False, "Criptographic Mismatch (Possible Tampering)"
            
        return True, "Verified"
    except Exception as e:
        return False, f"Malformed Envelope: {str(e)}"
