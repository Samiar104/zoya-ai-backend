"""Device router — register, list, heartbeat, remove devices."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_user, require_api_key
from app.models.command import Command, CommandStatus
from app.models.device import Device
from app.models.user import User
from app.schemas.command import CommandOut
from app.schemas.device import DeviceHeartbeat, DeviceOut, DeviceRegister
from app.services.dispatcher import pending_commands_for_device

router = APIRouter(prefix="/devices", tags=["devices"])
log = get_logger("zoya.devices")

@router.post("/register", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def register_device(
    data: DeviceRegister,
    db: Session = Depends(get_db),
    _key: str = Depends(require_api_key),
) -> Device:
    """Register (or re-register) a device. Devices authenticate with the API key."""
    device = db.query(Device).filter(Device.device_id == data.device_id).first()
    if device:
        device.name = data.name
        device.model = data.model
        device.android_version = data.android_version
        device.last_seen_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(device)
        return device
    device = Device(
        device_id=data.device_id,
        name=data.name,
        model=data.model,
        android_version=data.android_version,
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    log.info("Registered device %s (%s)", device.device_id, device.name)
    return device


@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[Device]:
    return db.query(Device).order_by(Device.created_at.desc()).all()


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> Device:
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/heartbeat")
def heartbeat(data: DeviceHeartbeat, db: Session = Depends(get_db), _key: str = Depends(require_api_key)) -> dict:
    device = db.query(Device).filter(Device.device_id == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not registered")
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "device_id": device.device_id}


@router.get("/{device_id}/pending-commands", response_model=list[CommandOut])
def pending_commands(
    device_id: int, db: Session = Depends(get_db), _key: str = Depends(require_api_key)
) -> list[Command]:
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return pending_commands_for_device(db, device.id)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> None:
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
    log.info("Deleted device %s", device.device_id)
