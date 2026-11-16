"""Chat router — conversation sessions + WebSocket channels.

REST:
- POST /chat/sessions — new session
- GET  /chat/sessions — list sessions
- GET  /chat/sessions/{id}/messages — history
- POST /chat/message — send a message, get ZOYA's reply

WebSockets:
- /ws/chat — live chat (JSON: {"session_id": n, "content": "..."})
- /ws/device/{device_id}?api_key=... — device channel: server pushes
  commands, device sends {"type": "result", "command_id": n, ...} and
  {"type": "heartbeat"} messages.
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.config import ensure_api_key, get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.models.command import Command, CommandStatus
from app.models.conversation import ConversationMessage, ConversationSession
from app.models.device import Device
from app.models.user import User
from app.schemas.conversation import ChatMessage, ChatReply, MessageOut, SessionCreate, SessionOut
from app.services import memory as memory_service
from app.services.conversation import ZoyaBrain
from app.services.dispatcher import pending_commands_for_device
from app.ws.manager import manager

router = APIRouter(tags=["chat"])
log = get_logger("zoya.chat")


@router.post("/chat/sessions", response_model=SessionOut, status_code=201)
def create_session(
    data: SessionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ConversationSession:
    settings = get_settings()
    language = data.language if data.language in settings.languages else "hi"
    if data.mode not in ("assistant", "companion"):
        raise HTTPException(status_code=400, detail="mode must be 'assistant' or 'companion'")
    session = ConversationSession(user_id=user.id, device_id=data.device_id, language=language, mode=data.mode, title=data.title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/chat/sessions", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ConversationSession]:
    return (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == user.id)
        .order_by(ConversationSession.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/chat/sessions/{session_id}/messages", response_model=list[MessageOut])
def session_messages(
    session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ConversationMessage]:
    session = db.query(ConversationSession).filter(ConversationSession.id == session_id).first()
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return db.query(ConversationMessage).filter(ConversationMessage.session_id == session_id).order_by(ConversationMessage.created_at.asc()).all()


@router.post("/chat/message", response_model=ChatReply)
def send_message(data: ChatMessage, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ChatReply:
    session = db.query(ConversationSession).filter(ConversationSession.id == data.session_id).first()
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    # The brain: understand, remember, feel, reply.
    # Learn FIRST so the reply can use what was just taught.
    brain = ZoyaBrain(language=session.language, mode=session.mode)
    understanding = brain.understand(data.content)
    history = [
        {"role": m.role, "content": m.content}
        for m in db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == session.id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(10)
        .all()
    ]
    db.add(ConversationMessage(
        session_id=session.id, role="user", content=data.content,
        emotion=understanding.emotion, emotion_confidence=understanding.confidence,
    ))
    db.flush()
    memory_service.learn_from_message(db, user.id, data.content)
    memory_service.record_mood(db, user.id, understanding.emotion, understanding.confidence)
    context = memory_service.context_for_user(db, user.id)
    reply_text, understanding = brain.reply(data.content, user_context=context, history=history)

    db.add(ConversationMessage(
        session_id=session.id, role="assistant", content=reply_text,
        emotion=understanding.emotion, emotion_confidence=understanding.confidence,
    ))
    db.commit()
    return ChatReply(
        session_id=session.id,
        reply=reply_text,
        language=session.language,
        mode=session.mode,
        intent=understanding.intent,
        emotion=understanding.emotion,
        emotion_confidence=understanding.confidence,
    )


# --- WebSockets ----------------------------------------------------------


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect_chat(websocket)
    db = next(get_db())
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "detail": "Invalid JSON"}))
                continue
            session_id = payload.get("session_id")
            content = payload.get("content", "")
            session = db.query(ConversationSession).filter(ConversationSession.id == session_id).first() if session_id else None
            language = session.language if session else get_settings().voice_default_language
            mode = session.mode if session else "assistant"
            brain = ZoyaBrain(language=language, mode=mode)
            reply, understanding = brain.reply(content, user_context={}, history=[])
            if session:
                db.add(ConversationMessage(session_id=session.id, role="user", content=content, emotion=understanding.emotion, emotion_confidence=understanding.confidence))
                db.add(ConversationMessage(session_id=session.id, role="assistant", content=reply, emotion=understanding.emotion, emotion_confidence=understanding.confidence))
                db.commit()
            await websocket.send_text(json.dumps({"type": "reply", "session_id": session_id, "reply": reply, "intent": understanding.intent, "emotion": understanding.emotion, "emotion_confidence": understanding.confidence}))
    except WebSocketDisconnect:
        manager.disconnect_chat(websocket)
    finally:
        db.close()


@router.websocket("/ws/device/{device_id}")
async def websocket_device(websocket: WebSocket, device_id: str, api_key: str = Query("")):
    """Device channel. Auth: ?api_key=<static API key>."""
    if api_key != ensure_api_key():
        await websocket.close(code=1008)
        log.warning("Device WS rejected (bad API key): %s", device_id)
        return
    await manager.connect_device(device_id, websocket)
    db = next(get_db())
    try:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if device is None:
            await websocket.send_text(json.dumps({"type": "error", "detail": "Device not registered. Register first."}))
            return
        device.is_online = True
        db.commit()
        # Push any queued commands right away.
        for cmd in pending_commands_for_device(db, device.id):
            payload = {
                "type": "command",
                "command_id": cmd.id,
                "command_type": cmd.command_type.value,
                "payload": json.loads(cmd.payload) if cmd.payload else {},
                "text": cmd.text,
            }
            if await manager.send_to_device(device_id, payload):
                cmd.status = CommandStatus.SENT
        db.commit()
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg_type = payload.get("type")
            if msg_type == "heartbeat":
                if device:
                    from datetime import datetime, timezone

                    device.last_seen_at = datetime.now(timezone.utc)
                    db.commit()
            elif msg_type == "result":
                cmd = db.query(Command).filter(Command.id == payload.get("command_id")).first()
                if cmd:
                    try:
                        cmd.status = CommandStatus(payload.get("status", "completed"))
                    except ValueError:
                        cmd.status = CommandStatus.COMPLETED
                    cmd.result = payload.get("result")
                    db.commit()
                    log.info("Command %s result from %s: %s", cmd.id, device_id, cmd.status)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_device(device_id)
        db2 = next(get_db())
        dev = db2.query(Device).filter(Device.device_id == device_id).first()
        if dev:
            dev.is_online = False
            db2.commit()
        db2.close()
        db.close()
