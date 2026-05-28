from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.pricing_config import PricingConfig

DEFAULT_GLOBAL_MARKUP_PERCENTAGE = 15.0


def _get_or_create_pricing_config(db: Session) -> PricingConfig:
    config = db.query(PricingConfig).filter(PricingConfig.id == 1).first()
    if config:
        return config

    config = PricingConfig(
        id=1, global_markup_percentage=DEFAULT_GLOBAL_MARKUP_PERCENTAGE
    )
    db.add(config)
    try:
        db.commit()
        db.refresh(config)
        return config
    except IntegrityError:
        db.rollback()
        config = db.query(PricingConfig).filter(PricingConfig.id == 1).first()
        if config:
            return config
        raise


def get_pricing_config(db: Session) -> PricingConfig:
    return _get_or_create_pricing_config(db)


def get_global_markup(db: Session) -> Decimal:
    config = _get_or_create_pricing_config(db)
    return Decimal(str(config.global_markup_percentage))


def update_global_markup(db: Session, percentage: float) -> PricingConfig:
    config = _get_or_create_pricing_config(db)
    config.global_markup_percentage = percentage
    db.commit()
    db.refresh(config)
    return config
