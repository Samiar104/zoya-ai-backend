"""Command dispatcher — delivers queued commands to devices.

If the device is connected over WebSocket, the command is sent immediately
and marked ``sent``; otherwise it stays ``queued`` until the device
connects (the device pulls pending commands on connect via the API).
"""
import json

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.command import Command, CommandStatus
from app.models.device import Device
from app.ws.manager import manager

log = get_logger("zoya.dispatcher")


async def dispatch_command(db: Session, command: Command) -> Command:
    device = db.query(Device).filter(Device.id == command.device_id).first()
    if device is None:
        command.status = CommandStatus.FAILED
        command.result = "Device not found"
        db.commit()
        return command

    payload = {
        "type": "command",
        "command_id": command.id,
        "command_type": command.command_type.value,
        "payload": json.loads(command.payload) if command.payload else {},
        "text": command.text,
    }
    sent = await manager.send_to_device(device.device_id, payload)
    if sent:
        command.status = CommandStatus.SENT
        log.info("Command %s sent to device %s", command.id, device.device_id)
    else:
        command.status = CommandStatus.QUEUED
        log.info("Device %s offline — command %s queued", device.device_id, command.id)
    db.commit()
    db.refresh(command)
    return command


def pending_commands_for_device(db: Session, device_id: int) -> list[Command]:
    return (
        db.query(Command)
        .filter(Command.device_id == device_id, Command.status == CommandStatus.QUEUED)
        .order_by(Command.created_at.asc())
        .all()
    )
