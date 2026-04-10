# backend/utils/security_ops.py

import hashlib

def hash_value(value: str):
    return hashlib.sha256(value.encode()).hexdigest()
