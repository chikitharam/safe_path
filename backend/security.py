from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
import secrets

# We will use this to hash passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# We will use this for Login (JWT Tokens)
SECRET_KEY = "super_secret_safepath_key_change_this_in_production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# --- PASSWORD HASHING ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- JWT TOKENS ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- EMAIL VERIFICATION TOKENS (THIS WAS MISSING) ---
def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)