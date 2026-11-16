"""Plugin/feature registry service.

Features are metadata records in the database (see models/feature.py).
This service enforces the rules: unique slug names, no code execution,
and safe enable/disable/remove. Installing a feature's code is handled
by the Android app / Feature Builder in later phases.
"""
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.feature import Feature
from app.schemas.feature import FeatureCreate, FeatureUpdate

log = get_logger("zoya.plugins")

# Features shipped with Phase 1 (built-in, always available).
BUILTIN_FEATURES: list[dict] = [
    {"name": "voice_assistant", "display_name": "Voice Assistant", "version": "1.0.0",
     "description": "Voice and text conversation with ZOYA.", "category": "core"},
    {"name": "device_control", "display_name": "Device Control", "version": "1.0.0",
     "description": "Touch, apps, media and calls via Accessibility Service.", "category": "core"},
    {"name": "youtube_control", "display_name": "YouTube Control", "version": "1.0.0",
     "description": "Open YouTube, search and control playback.", "category": "media"},
    {"name": "whatsapp_control", "display_name": "WhatsApp Control", "version": "1.0.0",
     "description": "Compose and send messages after confirmation.", "category": "messaging"},
    {"name": "camera_control", "display_name": "Camera Control", "version": "1.0.0",
     "description": "Open camera, take photos and record video.", "category": "media"},
    {"name": "smart_reminders", "display_name": "Smart Reminders", "version": "1.0.0",
     "description": "Voice-controlled reminders.", "category": "productivity"},
]


def seed_builtin_features(db: Session) -> int:
    created = 0
    for item in BUILTIN_FEATURES:
        if db.query(Feature).filter(Feature.name == item["name"]).first():
            continue
        db.add(Feature(**item))
        created += 1
    if created:
        db.commit()
        log.info("Seeded %d built-in features", created)
    return created


def create_feature(db: Session, data: FeatureCreate) -> Feature:
    feature = Feature(**data.model_dump())
    db.add(feature)
    db.commit()
    db.refresh(feature)
    log.info("Feature registered: %s v%s", feature.name, feature.version)
    return feature


def update_feature(db: Session, feature: Feature, data: FeatureUpdate) -> Feature:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(feature, key, value)
    db.commit()
    db.refresh(feature)
    return feature


def set_enabled(db: Session, feature: Feature, enabled: bool) -> Feature:
    feature.enabled = enabled
    db.commit()
    db.refresh(feature)
    log.info("Feature %s %s", feature.name, "enabled" if enabled else "disabled")
    return feature
