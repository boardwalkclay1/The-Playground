# backend/utils/security_ops.py
"""
Security Operations (Hashing + Verification)
-------------------------------------------

Provides:
- SHA-256 / SHA-512 hashing
- BLAKE2b hashing
- PBKDF2-HMAC (recommended)
- Salted + unsalted modes
- Constant-time comparison
- Structured return objects
"""

from hashlib import sha256, sha512, pbkdf2_hmac, blake2b
from secrets import token_hex, compare_digest
from typing import Dict, Any


# ---------------------------------------------------------
# BASIC HASHES (deterministic)
# ---------------------------------------------------------

def hash_sha256(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def hash_sha512(value: str) -> str:
    return sha512(value.encode("utf-8")).hexdigest()


def hash_blake2(value: str) -> str:
    return blake2b(value.encode("utf-8"), digest_size=64).hexdigest()


# ---------------------------------------------------------
# SALTED HASHES (recommended)
# ---------------------------------------------------------

def hash_pbkdf2(value: str, salt: str | None = None, iterations: int = 100_000) -> Dict[str, Any]:
    """
    PBKDF2-HMAC-SHA256 salted hash.
    Returns:
    {
        "success": True,
        "salt": "...",
        "iterations": 100000,
        "hash": "..."
    }
    """
    if salt is None:
        salt = token_hex(16)

    dk = pbkdf2_hmac(
        "sha256",
        value.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )

    return {
        "success": True,
        "salt": salt,
        "iterations": iterations,
        "hash": dk.hex(),
    }


def verify_pbkdf2(value: str, salt: str, iterations: int, expected_hash: str) -> bool:
    """
    Constant-time PBKDF2 verification.
    """
    dk = pbkdf2_hmac(
        "sha256",
        value.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return compare_digest(dk.hex(), expected_hash)


# ---------------------------------------------------------
# UNIVERSAL HASH WRAPPER
# ---------------------------------------------------------

def hash_value(value: str, method: str = "sha256") -> Dict[str, Any]:
    """
    Universal hashing interface.
    method: sha256 | sha512 | blake2 | pbkdf2
    """
    method = method.lower()

    if method == "sha256":
        return {"success": True, "method": "sha256", "hash": hash_sha256(value)}

    if method == "sha512":
        return {"success": True, "method": "sha512", "hash": hash_sha512(value)}

    if method == "blake2":
        return {"success": True, "method": "blake2", "hash": hash_blake2(value)}

    if method == "pbkdf2":
        return hash_pbkdf2(value)

    return {"success": False, "error": f"Unknown hash method '{method}'"}
