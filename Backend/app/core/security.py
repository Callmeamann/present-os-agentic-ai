import os
import base64
import binascii
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from app.core.config import settings

# We must use a 32-byte key for AES-256.
# We get this from the 32-byte (64-char) hex string in our .env
try:
    AES_KEY = bytes.fromhex(settings.SECRET_KEY)
except ValueError:
    raise ValueError("SECRET_KEY must be a 64-character hex-encoded string (32 bytes)")

class TokenSecurity:
    """
    Handles encryption and decryption of sensitive tokens using AES-GCM.
    This ensures that data like Google refresh tokens are stored securely
    in our database and are not in plaintext.
    """

    @staticmethod
    def encrypt(plaintext: str) -> str:
        """
        Encrypts a plaintext string.
        
        Returns:
            A base64 encoded string containing the (nonce + ciphertext).
        """
        if not plaintext:
            return ""
            
        aesgcm = AESGCM(AES_KEY)
        # A 12-byte nonce is recommended for AES-GCM
        nonce = os.urandom(12)
        
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)
        
        # We store the nonce and ciphertext together, then base64-encode
        # the whole thing so it's a clean string for Firestore.
        encrypted_data = nonce + ciphertext
        return base64.b64encode(encrypted_data).decode('utf-8')

    @staticmethod
    def decrypt(encrypted_data_b64: str) -> str:
        """
        Decrypts a base64 encoded string (nonce + ciphertext).
        
        Returns:
            The decrypted plaintext string.
        """
        if not encrypted_data_b64:
            return ""

        try:
            encrypted_data = base64.b64decode(encrypted_data_b64)
            
            # Extract the nonce (first 12 bytes) and the ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            aesgcm = AESGCM(AES_KEY)
            
            # Decrypt and return the utf-8 string
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted_bytes.decode('utf-8')
            
        except (InvalidTag, TypeError, binascii.Error) as e:
            # Handle decryption errors (e.g., tampered data, incorrect key)
            print(f"Error decrypting data: {e}")
            # In a real app, you'd log this securely.
            # For this assignment, we'll raise an error.
            raise ValueError("Failed to decrypt token. Data may be corrupt or key is incorrect.")