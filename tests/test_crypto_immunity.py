import unittest
import time
import sys
sys.path.append('skills/saf-core/lib')
import crypto_engine
import json
import os

class TestCryptoImmunity(unittest.TestCase):
    def setUp(self):
        # Setup de confianza mutua
        self.agent_id = "michi_agent"
        self.pub_key = "test_pub_key"
        with open(crypto_engine.KEY_PATH, 'w') as f:
            json.dump({self.agent_id: {"public_key": self.pub_key}}, f)

    def test_valid_message(self):
        body = "Hola Jarvis"
        sig = crypto_engine.sign_message(body, self.pub_key)
        envelope = {
            "sender_id": self.agent_id,
            "body": body,
            "signature": sig,
            "timestamp": time.time()
        }
        ok, msg = crypto_engine.verify_envelope(envelope)
        self.assertTrue(ok)

    def test_forged_signature(self):
        envelope = {
            "sender_id": self.agent_id,
            "body": "Mensaje Malicioso",
            "signature": "fake_signature",
            "timestamp": time.time()
        }
        ok, msg = crypto_engine.verify_envelope(envelope)
        self.assertFalse(ok)
        self.assertEqual(msg, "Criptographic Mismatch (Possible Tampering)")

    def test_replay_attack(self):
        body = "Acción antigua"
        sig = crypto_engine.sign_message(body, self.pub_key)
        envelope = {
            "sender_id": self.agent_id,
            "body": body,
            "signature": sig,
            "timestamp": time.time() - 60 # 1 minuto atrás
        }
        ok, msg = crypto_engine.verify_envelope(envelope)
        self.assertFalse(ok)
        self.assertIn("expired", msg)

if __name__ == '__main__':
    unittest.main()
