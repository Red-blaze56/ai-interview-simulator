import secrets, hashlib, jwt, uuid
from datetime import datetime, timezone, timedelta
from pwdlib import PasswordHash
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

ALGORITHM = "HS256"
_hasher = PasswordHash.recommended()

# --- passwords ---------------------------------------------------------------

def hash_password(raw: str)->str:
    """Hash a password using the recommended algorithm."""
    return _hasher.hash(raw)

def verify_password(raw: str, hashed: str)->bool:
    """Verify a password against its hash."""
    return _hasher.verify(raw, hashed)

# --- access tokens ---------------------------------------------------------------

def create_access_token(subject: str | uuid.UUID) -> str:
    """Create a new access token for a given subject."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "jti": str(uuid.uuid4()),
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
 
def decode_access_token(token: str) -> dict| None:
    """Decode your jwt to get paytoad"""
    try:
      claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    if claims.get("typ") != "access":
        return None
    if not claims.get("sub") or not claims.get("jti") or not claims.get("iat"):
        return None 
    return claims

# --- refresh token ---------------------------------------------------------------

def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def new_refresh_token() -> tuple[str,str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)

def refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)

