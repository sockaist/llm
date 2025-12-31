
import os
from pathlib import Path
from cryptography.fernet import Fernet
from llm_backend.utils.logger import logger

class EncryptionManager:
    """
    Manages personal document encryption using Fernet (symmetric encryption).
    Keys are stored locally in .keys/ directory for development.
    """
    
    _instances = {}

    def __init__(self, keys_dir: str = ".keys"):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.user_ciphers = {}

    @classmethod
    def get_instance(cls):
        """Singleton-like accessor."""
        if cls not in cls._instances:
            cls._instances[cls] = cls()
        return cls._instances[cls]

    def _get_user_cipher(self, user_id: str) -> Fernet:
        """Get or recreate a Fernet cipher for the given user."""
        if user_id in self.user_ciphers:
            return self.user_ciphers[user_id]
        
        key_path = self.keys_dir / f"{user_id}.key"
        
        if key_path.exists():
            key = key_path.read_bytes()
        else:
            logger.info(f"[Encryption] Generating new key for user: {user_id}")
            key = Fernet.generate_key()
            try:
                key_path.write_bytes(key)
                # Secure permission for key file (Read/Write for owner only)
                os.chmod(key_path, 0o600)
            except Exception as e:
                logger.error(f"[Encryption] Failed to save key for {user_id}: {e}")
                raise
        
        cipher = Fernet(key)
        self.user_ciphers[user_id] = cipher
        return cipher

    def encrypt_text(self, user_id: str, plaintext: str) -> str:
        """Encrypt content for a specific user."""
        if not user_id or user_id == "public":
            return plaintext
            
        try:
            cipher = self._get_user_cipher(user_id)
            encrypted_bytes = cipher.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"[Encryption] Encryption failed for user {user_id}: {e}")
            raise

    def decrypt_text(self, user_id: str, encrypted_text: str) -> str:
        """Decrypt content for a specific user."""
        if not user_id or user_id == "public":
            return encrypted_text

        try:
            cipher = self._get_user_cipher(user_id)
            decrypted_bytes = cipher.decrypt(encrypted_text.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"[Encryption] Decryption failed for user {user_id}: {e}")
            # Do NOT return original text on failure (secure fail)
            return "[Decryption Failed]"
