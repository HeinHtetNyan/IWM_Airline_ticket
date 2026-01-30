from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.schemas.auth import CustomerSignupIn, LoginIn, TokenOut
from app.auth.security import hash_password, verify_password
from app.auth.tokens import create_access_token
from app.models.customer_user import CustomerUser
from app.models.admin_user import AdminUser
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/customer/signup", response_model=TokenOut, status_code=201)
def customer_signup(payload: CustomerSignupIn, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    existing = db.query(CustomerUser).filter(CustomerUser.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = CustomerUser(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        is_verified=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), role="CUSTOMER")
    return TokenOut(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "full_name": user.full_name, "phone": user.phone},
    )

@router.post("/customer/login", response_model=TokenOut)
def customer_login(payload: LoginIn, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    user = db.query(CustomerUser).filter(CustomerUser.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    token = create_access_token(subject=str(user.id), role="CUSTOMER")
    return TokenOut(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "full_name": user.full_name, "phone": user.phone},
    )

@router.post("/admin/login", response_model=TokenOut)
def admin_login(payload: LoginIn, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Admin is inactive")

    token = create_access_token(subject=str(user.id), role="ADMIN")
    return TokenOut(access_token=token, user={"id": str(user.id), "email": user.email})

@router.post("/customer/token", response_model=TokenOut)
def customer_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Swagger sends username/password
    email = form_data.username
    password = form_data.password

    user = db.query(CustomerUser).filter(CustomerUser.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    token = create_access_token(subject=str(user.id), role="CUSTOMER")
    return TokenOut(
        access_token=token,
        user={"id": str(user.id), "email": user.email, "full_name": user.full_name, "phone": user.phone},
    )
