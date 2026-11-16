"""Command router — queue commands for devices, track status, get results."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.models.command import Command, CommandStatus
from app.models.device import Device
from app.models.user import User
from app.schemas.command import CommandCreate, CommandOut, CommandResult
from app.services.dispatcher import dispatch_command

router = APIRouter(prefix="/commands", tags=["commands"])
log = get_logger("zoya.commands")


@router.post("", response_model=CommandOut, status_code=status.HTTP_201_CREATED)
async def create_command(
    data: CommandCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Command:
    device = db.query(Device).filter(Device.id == data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    command = Command(
        device_id=device.id,
        command_type=data.command_type,
        payload=json.dumps(data.payload or {}),
        text=data.text,
        created_by_id=user.id,
    )
    db.add(command)
    db.commit()
    db.refresh(command)
    command = await dispatch_command(db, command)
    log.info("Command %s (%s) created for device %s", command.id, command.command_type, device.device_id)
    return command


@router.get("", response_model=list[CommandOut])
def list_commands(
    device_id: int | None = None,
    status_filter: CommandStatus | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Command]:
    query = db.query(Command).order_by(Command.created_at.desc())
    if device_id is not None:
        query = query.filter(Command.device_id == device_id)
    if status_filter is not None:
        query = query.filter(Command.status == status_filter)
    return query.limit(limit).all()


@router.get("/{command_id}", response_model=CommandOut)
def get_command(command_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> Command:
    command = db.query(Command).filter(Command.id == command_id).first()
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    return command


@router.post("/{command_id}/result", response_model=CommandOut)
def report_result(
    command_id: int,
    data: CommandResult,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Command:
    """Device (via dashboard) reports the outcome of a command."""
    command = db.query(Command).filter(Command.id == command_id).first()
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    if data.status not in (CommandStatus.COMPLETED, CommandStatus.FAILED, CommandStatus.DELIVERED):
        raise HTTPException(status_code=400, detail="Invalid result status")
    command.status = data.status
    command.result = data.result
    db.commit()
    db.refresh(command)
    return command


@router.post("/{command_id}/cancel", response_model=CommandOut)
def cancel_command(command_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> Command:
    command = db.query(Command).filter(Command.id == command_id).first()
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    if command.status in (CommandStatus.COMPLETED, CommandStatus.FAILED):
        raise HTTPException(status_code=400, detail="Command already finished")
    command.status = CommandStatus.CANCELLED
    db.commit()
    db.refresh(command)
    return command
