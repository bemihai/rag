import hashlib


def hash8(s: str) -> int:
    """Hashes a string to an 8-digit integer."""
    return int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16) % 10**8