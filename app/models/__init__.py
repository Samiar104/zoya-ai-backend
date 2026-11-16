"""Models package — imports every model so SQLAlchemy registers them."""
from app.models.command import Command, CommandStatus, CommandType  # noqa: F401
from app.models.conversation import ConversationMessage, ConversationSession  # noqa: F401
from app.models.device import Device  # noqa: F401
from app.models.feature import Feature  # noqa: F401
from app.models.memory import UserMemory  # noqa: F401
from app.models.user import User  # noqa: F401
