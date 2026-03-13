from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_BCRYPT_BYTES = 72


def _truncate_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > MAX_BCRYPT_BYTES:
        pwd_bytes = pwd_bytes[:MAX_BCRYPT_BYTES]
    return pwd_bytes.decode("utf-8", "ignore")


def get_password_hash(password: str) -> str:
    password = _truncate_password(password)
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    password = _truncate_password(password)
    return pwd_context.verify(password, password_hash)