import hashlib
import hmac
import os
import base64
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db_pool
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest

router = APIRouter()


def _hash_password(password: str) -> str:
    """Simple SHA-256 password hash with a random salt stored together."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return base64.b64encode(salt + digest).decode()


def _verify_password(password: str, stored: str) -> bool:
    decoded = base64.b64decode(stored.encode())
    salt, digest = decoded[:16], decoded[16:]
    new_digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return hmac.compare_digest(digest, new_digest)


def _make_token(user_id: int) -> str:
    """Simple non-expiring opaque token (replace with JWT in production)."""
    raw = f"{user_id}:{os.urandom(32).hex()}"
    return base64.b64encode(raw.encode()).decode()


@router.post("/auth/register", response_model=AuthResponse, status_code=201)
def register(body: RegisterRequest):
    pool = get_db_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", (body.email,))
            if cur.fetchone():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
            hashed = _hash_password(body.password)
            cur.execute(
                "INSERT INTO users (email, password_hash, display_name, phone) VALUES (%s, %s, %s, %s) RETURNING id",
                (body.email.lower(), hashed, body.display_name, body.phone),
            )
            user_id = cur.fetchone()[0]
        conn.commit()
    token = _make_token(user_id)
    return AuthResponse(user_id=user_id, email=body.email, display_name=body.display_name, token=token)


@router.post("/auth/login", response_model=AuthResponse)
def login(body: LoginRequest):
    pool = get_db_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, display_name, password_hash FROM users WHERE LOWER(email) = LOWER(%s)",
                (body.email,),
            )
            row = cur.fetchone()
    if not row or not _verify_password(body.password, row[3]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = _make_token(row[0])
    return AuthResponse(user_id=row[0], email=row[1], display_name=row[2] or "", token=token)
