# backend/utils/security_ops.py
"""
Security Operations (Hashing + Verification)
-------------------------------------------

Platform‑grade hashing utilities:
- SHA‑256 / SHA‑512
- BLAKE2b
- PBKDF2‑HMAC‑SHA256 (recommended)
- Salted + unsalted modes
- Optional pepper support
- Constant‑time comparison
- Structured return objects
- Never throws exceptions
"""

from hashlib import sha256, sha512, pbkdf2_hmac, blake2b
from secrets import token_hex, compare_digest
from typing import Dict, Any, Optional
import os


# ============================================================
# CONFIG
# ============================================================

DEFAULT_ITERATIONS = 100_000
DEFAULT_SALT_BYTES = 16
PEPPER = os.getenv("ASSISTANT_PEPPER", "")  # optional global pepper


# ============================================================
# BASIC HASHES (deterministic)
# ============================================================

def hash_sha256(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def hash_sha512(value: str) -> str:
    return sha512(value.encode("utf-8")).hexdigest()


def hash_blake2(value: str) -> str:
    return blake2b(value.encode("utf-8"), digest_size=64).hexdigest()


# ============================================================
# PBKDF2 (recommended)
# ============================================================

def hash_pbkdf2(
    value: str,
    salt: Optional[str] = None,
    iterations: int = DEFAULT_ITERATIONS,
    pepper: Optional[str] = PEPPER,
) -> Dict[str, Any]:
    """
    PBKDF2-HMAC-SHA256 salted hash.
    Returns structured object:
    {
        "success": True,
        "method": "pbkdf2",
        "salt": "...",
        "iterations": 100000,
        "hash": "...",
        "peppered": bool
    }
    """
    try:
        if salt is None:
            salt = token_hex(DEFAULT_SALT_BYTES)

        raw = value + (pepper or "")
        dk = pbkdf2_hmac(
            "sha256",
            raw.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )

        return {
            "success": True,
            "method": "pbkdf2",
            "salt": salt,
            "iterations": iterations,
            "hash": dk.hex(),
            "peppered": bool(pepper),
        }

    except Exception as e:
        return {"success": False, "error": str(e), "code": "PBKDF2_ERROR"}


def verify_pbkdf2(
    value: str,
    salt: str,
    iterations: int,
    expected_hash: str,
    pepper: Optional[str] = PEPPER,
) -> Dict[str, Any]:
    """
    Constant-time PBKDF2 verification.
    Returns:
    {
        "success": True/False,
        "verified": True/False
    }
    """
    try:
        raw = value + (pepper or "")
        dk = pbkdf2_hmac(
            "sha256",
            raw.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        ok = compare_digest(dk.hex(), expected_hash)
        return {"success": True, "verified": ok}

    except Exception as e:
        return {"success": False, "error": str(e), "code": "VERIFY_ERROR"}


# ============================================================
# UNIVERSAL HASH WRAPPER
# ============================================================

def hash_value(value: str, method: str = "sha256") -> Dict[str, Any]:
    """
    Universal hashing interface.
    method: sha256 | sha512 | blake2 | pbkdf2
    """
    try:
        method = method.lower()

        if method == "sha256":
            return {"success": True, "method": "sha256", "hash": hash_sha256(value)}

        if method == "sha512":
            return {"success": True, "method": "sha512", "hash": hash_sha512(value)}

        if method == "blake2":
            return {"success": True, "method": "blake2", "hash": hash_blake2(value)}

        if method == "pbkdf2":
            return hash_pbkdf2(value)

        return {"success": False, "error": f"Unknown hash method '{method}'", "code": "UNKNOWN_METHOD"}

    except Exception as e:
        return {"success": False, "error": str(e), "code": "HASH_ERROR"}
