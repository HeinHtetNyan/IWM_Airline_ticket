from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_current_admin_optional
from backend.app.auth.security import get_password_hash, verify_password
from backend.app.auth.tokens import create_access_token
from backend.app.crud.admin_auth import authenticate_admin, create_admin, get_admin_by_email
from backend.app.db.deps import get_db
from backend.app.models.admin_user import AdminUser
from backend.app.models.customer_user import CustomerUser
from backend.app.core.rate_limit import enforce_rate_limit
from backend.app.schemas.auth import AdminOut, AdminSignupRequest, CustomerSignupIn, LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


# CUSTOMER
@router.post("/customer/signup", response_model=TokenOut, status_code=201)
def customer_signup(
    payload: CustomerSignupIn,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, action="customer_signup", max_requests=5, window_seconds=60)
    email = payload.email.lower().strip()

    existing = db.query(CustomerUser).filter(CustomerUser.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = CustomerUser(
        email=email,
        password_hash=get_password_hash(payload.password),
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
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
        },
    )


@router.post("/customer/login", response_model=TokenOut)
def customer_login(
    payload: LoginIn,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, action="customer_login", max_requests=5, window_seconds=60)
    email = payload.email.lower().strip()

    user = db.query(CustomerUser).filter(CustomerUser.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    token = create_access_token(subject=str(user.id), role="CUSTOMER")
    return TokenOut(
        access_token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
        },
    )


@router.post("/customer/token", response_model=TokenOut)
def customer_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, action="customer_token", max_requests=5, window_seconds=60)
    email = form_data.username.lower().strip()
    password = form_data.password

    user = db.query(CustomerUser).filter(CustomerUser.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    token = create_access_token(subject=str(user.id), role="CUSTOMER")
    return TokenOut(
        access_token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
        },
    )


# ADMIN
@router.post("/admin/signup", response_model=AdminOut, status_code=201)
def admin_signup(
    payload: AdminSignupRequest,
    request: Request,
    db: Session = Depends(get_db),
    acting_admin: AdminUser | None = Depends(get_current_admin_optional),
):
    enforce_rate_limit(request, action="admin_signup", max_requests=5, window_seconds=60)
    existing = get_admin_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    has_existing_admin = db.query(AdminUser.id).first() is not None
    if has_existing_admin and (not acting_admin or acting_admin.role != "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Only super admins can create admin accounts")

    if has_existing_admin:
        role = payload.role if payload.role in ("STAFF", "SUPER_ADMIN") else "STAFF"
    else:
        role = "SUPER_ADMIN"

    admin = create_admin(
        db=db,
        name=payload.name,
        email=payload.email,
        password=payload.password,
        role=role,
    )

    return AdminOut(
        id=str(admin.id),
        name=admin.name,
        email=admin.email,
        role=admin.role,
        is_active=admin.is_active,
    )


@router.post("/admin/token")
def admin_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, action="admin_token", max_requests=5, window_seconds=60)
    admin = authenticate_admin(db, form_data.username.lower().strip(), form_data.password)
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token = create_access_token(subject=str(admin.id), role=admin.role)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin": {
            "id": str(admin.id),
            "name": admin.name,
            "email": admin.email,
            "role": admin.role,
        },
    }
