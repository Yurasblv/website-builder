from cryptography.fernet import Fernet

from app.core import settings


class PasswordEncryptor:
    """
    Utility class for encrypting and decrypting passwords using Fernet symmetric encryption.
    """

    _key = settings.ENCRYPTION_KEY
    _cipher = Fernet(_key.encode())

    @classmethod
    def encrypt(cls, password: str) -> str:
        """
        Encrypt a plaintext password.

        Args:
            password: The plaintext password to encrypt

        Returns:
            str: The encrypted password as a string
        """

        return cls._cipher.encrypt(password.encode()).decode()

    @classmethod
    def decrypt(cls, encrypted_password: str) -> str:
        """
        Decrypt an encrypted password.

        Args:
            encrypted_password: The encrypted password to decrypt

        Returns:
            str: The decrypted plaintext password
        """

        return cls._cipher.decrypt(encrypted_password.encode()).decode()
