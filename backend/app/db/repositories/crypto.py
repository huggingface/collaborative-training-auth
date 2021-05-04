from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import SECRET_KEY


PADDING = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)
HASH_ALGORITHM = hashes.SHA256()


def save_private_key(private_key):
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.BestAvailableEncryption(f"{SECRET_KEY}".encode()),
    )
    return pem


def save_public_key(public_key):
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )
    return pem


def load_private_key(string_in_db):
    private_key = serialization.load_pem_private_key(string_in_db, f"{SECRET_KEY}".encode())
    return private_key


def load_public_key(string_in_db):
    public_key = serialization.load_ssh_public_key(string_in_db)
    return public_key
