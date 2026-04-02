from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.auth.deps import get_current_admin_optional
from backend.app.auth.security import get_password_hash, verify_password
from backend.app.auth.tokens import create_access_token
from backend.app.crud.admin_auth import authenticate_admin, create_admin, get_admin_by_email
from backend.app.core.config import settings
from backend.app.db.deps import get_db
from backend.app.models.admin_user import AdminUser
from backend.app.models.customer_user import CustomerUser
from backend.app.core.rate_limit import enforce_rate_limit
from backend.app.schemas.auth import (
    AdminOut,
    AdminSignupRequest,
    CustomerSignupIn,
    ForgotPasswordRequest,
    LoginIn,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenOut,
    VerifyEmailRequest,
)
from backend.app.schemas.common import Message
from backend.app.services.auth_token_service import (
    RESET_PASSWORD,
    VERIFY_EMAIL,
    create_email_verification_token,
    create_password_reset_token,
    get_valid_auth_token,
    mark_token_used,
)
from backend.app.services.email_service import send_reset_password_email, send_verification_email
from backend.app.services.rate_limit_service import enforce_email_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


# CUSTOMER
@router.post("/customer/signup", response_model=TokenOut, status_code=201)
def customer_signup(
    payload: CustomerSignupIn,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        action="customer_signup",
        max_requests=5,
        window_seconds=60,
        fail_open=False,
    )
    email = payload.email.lower().strip()

    existing = db.query(CustomerUser).filter(CustomerUser.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = CustomerUser(
        email=email,
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        is_email_verified=False,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(user)
    verification_token = create_email_verification_token(db, user_id=user.id)
    background_tasks.add_task(send_verification_email, user.email, verification_token)

    token = create_access_token(subject=str(user.id), role="CUSTOMER")
    return TokenOut(
        access_token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "is_email_verified": user.is_email_verified,
        },
    )


@router.post("/customer/login", response_model=TokenOut)
def customer_login(
    payload: LoginIn,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        action="customer_login",
        max_requests=5,
        window_seconds=60,
        fail_open=False,
    )
    email = payload.email.lower().strip()

    user = db.query(CustomerUser).filter(CustomerUser.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    token = create_access_token(subject=str(user.id), role="CUSTOMER")
    return TokenOut(
        access_token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "is_email_verified": user.is_email_verified,
        },
    )


@router.post("/customer/token", response_model=TokenOut)
def customer_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        request,
        action="customer_token",
        max_requests=5,
        window_seconds=60,
        fail_open=False,
    )
    email = form_data.username.lower().strip()
    password = form_data.password

    user = db.query(CustomerUser).filter(CustomerUser.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    token = create_access_token(subject=str(user.id), role="CUSTOMER")
    return TokenOut(
        access_token=token,
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "is_email_verified": user.is_email_verified,
        },
    )


@router.post("/verify-email", response_model=Message)
def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    token_record = get_valid_auth_token(db, raw_token=payload.token, token_type=VERIFY_EMAIL)
    user = db.query(CustomerUser).filter(CustomerUser.id == token_record.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid token")

    user.is_email_verified = True
    db.add(user)
    mark_token_used(db, token_record)
    return Message(message="Email verified successfully")


@router.post("/resend-verification", response_model=Message)
def resend_verification_email(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    enforce_email_rate_limit(
        "resend_verification",
        payload.email,
        settings.RATE_LIMIT_RESEND_EMAIL,
        settings.RATE_LIMIT_WINDOW_SECONDS,
        fail_open=False,
    )

    user = db.query(CustomerUser).filter(CustomerUser.email == payload.email).first()
    if user and not user.is_email_verified:
        verification_token = create_email_verification_token(db, user_id=user.id)
        background_tasks.add_task(send_verification_email, user.email, verification_token)

    return Message(message="If the account exists, a verification email has been sent")


@router.post("/forgot-password", response_model=Message)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    enforce_email_rate_limit(
        "forgot_password",
        payload.email,
        settings.RATE_LIMIT_FORGOT_PASSWORD,
        settings.RATE_LIMIT_WINDOW_SECONDS,
        fail_open=False,
    )

    user = db.query(CustomerUser).filter(CustomerUser.email == payload.email).first()
    if user is not None:
        reset_token = create_password_reset_token(db, user_id=user.id)
        background_tasks.add_task(send_reset_password_email, user.email, reset_token)

    return Message(message="If the account exists, a password reset email has been sent")


@router.post("/reset-password", response_model=Message)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    token_record = get_valid_auth_token(db, raw_token=payload.token, token_type=RESET_PASSWORD)
    user = db.query(CustomerUser).filter(CustomerUser.id == token_record.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid token")

    user.password_hash = get_password_hash(payload.new_password)
    db.add(user)
    mark_token_used(db, token_record)
    return Message(message="Password reset successfully")


# ADMIN
@router.post("/admin/signup", response_model=AdminOut, status_code=201)
def admin_signup(
    payload: AdminSignupRequest,
    request: Request,
    db: Session = Depends(get_db),
    acting_admin: AdminUser | None = Depends(get_current_admin_optional),
):
    enforce_rate_limit(
        request,
        action="admin_signup",
        max_requests=5,
        window_seconds=60,
        fail_open=False,
    )
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
    enforce_rate_limit(
        request,
        action="admin_token",
        max_requests=5,
        window_seconds=60,
        fail_open=False,
    )
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
