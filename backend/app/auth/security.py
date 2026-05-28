from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_BCRYPT_BYTES = 72


def _validate_password_length(password: str) -> None:
    if len(password.encode("utf-8")) > MAX_BCRYPT_BYTES:
        raise ValueError(f"Password cannot exceed {MAX_BCRYPT_BYTES} bytes")


def get_password_hash(password: str) -> str:
    _validate_password_length(password)
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _validate_password_length(password)
    except ValueError:
        return False
    return pwd_context.verify(password, password_hash)
