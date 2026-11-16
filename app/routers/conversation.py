"""Conversation intelligence router — emotion analysis and user memory.

- POST /conversation/analyze-emotion — detect how the user feels.
- GET  /conversation/memory — what ZOYA remembers about you.
- POST /conversation/memory — teach ZOYA something about you.
- DELETE /conversation/memory/{id} — make ZOYA forget one item.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.memory import UserMemory
from app.models.user import User
from app.schemas.emotion import EmotionRequest, EmotionResponse, MemoryCreate, MemoryEntryOut
from app.services import memory as memory_service
from app.services.emotion import describe_emotion, detect_emotion

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("/analyze-emotion", response_model=EmotionResponse)
def analyze_emotion(data: EmotionRequest, _user: User = Depends(get_current_user)) -> EmotionResponse:
    emotion, confidence = detect_emotion(data.text, data.voice_metadata)
    return EmotionResponse(
        emotion=emotion,
        confidence=confidence,
        label=describe_emotion(emotion, data.language or "hi"),
    )


@router.get("/memory", response_model=list[MemoryEntryOut])
def get_memory(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[UserMemory]:
    return memory_service.list_memory(db, user.id)


@router.post("/memory", response_model=MemoryEntryOut, status_code=201)
def add_memory(data: MemoryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> UserMemory:
    if data.kind not in ("preference", "fact", "topic"):
        raise HTTPException(status_code=400, detail="kind must be preference, fact or topic")
    return memory_service.remember(db, user.id, data.kind, data.key, data.value)


@router.delete("/memory/{memory_id}", status_code=204)
def delete_memory(memory_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    row = db.query(UserMemory).filter(UserMemory.id == memory_id, UserMemory.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(row)
    db.commit()
