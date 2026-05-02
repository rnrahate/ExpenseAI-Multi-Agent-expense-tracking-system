from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
import bcrypt as bcrypt_module
from passlib.context import CryptContext
from backend.config import settings
from backend.logger import setup_logger

logger = setup_logger(__name__)


if not hasattr(bcrypt_module, "__about__") and hasattr(bcrypt_module, "__version__"):
    class _BcryptAbout:
        __version__ = bcrypt_module.__version__

    bcrypt_module.__about__ = _BcryptAbout()


pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.TOKEN_EXPIRE_HOURS)
    payload.update({"exp": expire})
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug(f"Token created for: {data.get('email')}")
    return token


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
