from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.customer_user import CustomerUser
from app.utils.security import hash_password, verify_password

async def get_customer_by_email(db: AsyncSession, email: str) -> CustomerUser | None:
    res = await db.execute(select(CustomerUser).where(CustomerUser.email == email))
    return res.scalar_one_or_none()

async def create_customer(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    phone: str | None = None,
) -> CustomerUser:
    user = CustomerUser(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        full_name=full_name,
        phone=phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_customer(db: AsyncSession, *, email: str, password: str) -> CustomerUser | None:
    user = await get_customer_by_email(db, email.lower().strip())
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
