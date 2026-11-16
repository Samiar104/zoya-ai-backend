"""User memory service — ZOYA's brain: what she remembers about the user.

Reads and writes UserMemory rows (preferences, facts, topics, moods).
Extraction is rule-based and transparent:
- "I like X" / "mujhe X pasand hai" -> preference
- "my name is X" / "mera naam X hai" -> fact
- "I am a student" / "main student hoon" -> fact
- every message's dominant topic keywords -> topic
- every message's detected emotion -> mood (kept as history)

The reply engine calls ``context_for_user()`` to get a short summary it
can use when answering (e.g. remembering a favourite singer, or that the
user was sad yesterday).
"""
import re

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.memory import UserMemory
from app.services.emotion import detect_emotion

log = get_logger("zoya.memory")

TOPIC_WORDS = [
    "cricket", "football", "music", "song", "gaana", "गाना", "movie", "film",
    "study", "exam", "exams", "school", "college", "job", "work", "kaam",
    "family", "mom", "dad", "mummy", "papa", "friend", "dost", "game", "games",
    "food", "khana", "chai", "health", "gym", "sleep", "neend", "travel",
    "phone", "youtube", "instagram", "whatsapp",
]

MAX_MOODS_KEPT = 20


def remember(db: Session, user_id: int, kind: str, key: str, value: str, confidence: float = 1.0) -> UserMemory:
    row = (
        db.query(UserMemory)
        .filter(UserMemory.user_id == user_id, UserMemory.kind == kind, UserMemory.key == key)
        .first()
    )
    if row:
        row.value = value
        row.confidence = confidence
    else:
        row = UserMemory(user_id=user_id, kind=kind, key=key, value=value, confidence=confidence)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def record_mood(db: Session, user_id: int, emotion: str, confidence: float) -> None:
    """Append an emotion snapshot; prune history to the last N moods."""
    remember(db, user_id, "mood", f"mood_{int(__import__('time').time())}", f"{emotion}:{confidence:.2f}", confidence)
    moods = (
        db.query(UserMemory)
        .filter(UserMemory.user_id == user_id, UserMemory.kind == "mood")
        .order_by(UserMemory.created_at.desc())
        .all()
    )
    for extra in moods[MAX_MOODS_KEPT:]:
        db.delete(extra)
    db.commit()


def learn_from_message(db: Session, user_id: int, text: str) -> list[str]:
    """Extract preferences/facts/topics from one user message. Returns what was learned."""
    learned: list[str] = []
    low = text.lower()

    m = re.search(r"(?:i like|i love|mujhe|मुझे)\s+([a-z\u0900-\u097f ]{2,30}?)\s*(?:pasand|पसंद|hai|है|very much|bohat)?\s*$", low)
    if m:
        thing = m.group(1).strip()
        # Drop trailing filler words the lazy group may have swallowed.
        for filler in ("pasand", "पसंद", "hai", "है"):
            if thing.endswith(" " + filler):
                thing = thing[: -len(filler) - 1].strip()
        if thing and len(thing) > 1:
            remember(db, user_id, "preference", f"likes_{thing.replace(' ', '_')[:40]}", thing)
            learned.append(f"likes {thing}")

    m = re.search(r"(?:my name is|mera naam|मेरा नाम)\s+([a-z\u0900-\u097f]+)", low)
    if m:
        remember(db, user_id, "fact", "name", m.group(1).strip())
        learned.append(f"name is {m.group(1).strip()}")

    m = re.search(r"(?:i am a|main|मैं)\s+(student|teacher|doctor|engineer|driver|shopkeeper)", low)
    if m:
        remember(db, user_id, "fact", "profession", m.group(1))
        learned.append(f"profession is {m.group(1)}")

    for topic in TOPIC_WORDS:
        if topic in low:
            remember(db, user_id, "topic", topic, f"talked about {topic}")
            learned.append(f"topic: {topic}")
    return learned


def context_for_user(db: Session, user_id: int) -> dict:
    """Short context summary for the reply engine."""
    rows = db.query(UserMemory).filter(UserMemory.user_id == user_id).order_by(UserMemory.updated_at.desc()).limit(50).all()
    prefs = {r.key: r.value for r in rows if r.kind == "preference"}
    facts = {r.key: r.value for r in rows if r.kind == "fact"}
    topics = sorted({r.key for r in rows if r.kind == "topic"})
    moods = [r.value.split(":")[0] for r in rows if r.kind == "mood"][:5]
    last_emotion = moods[0] if moods else None
    return {
        "preferences": prefs,
        "facts": facts,
        "recent_topics": topics[:10],
        "recent_moods": moods,
        "last_emotion": last_emotion,
    }


def list_memory(db: Session, user_id: int) -> list[UserMemory]:
    return db.query(UserMemory).filter(UserMemory.user_id == user_id).order_by(UserMemory.updated_at.desc()).limit(100).all()
