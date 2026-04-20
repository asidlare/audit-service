import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, Union

from app.schemas.enums import ChangeCode


class AuditEventBase(BaseModel):
    """
    Represents the base model for audit events.

    Provides a foundational structure for defining audit events, including attributes
    such as event identification, type, associated institution, and optional human-readable
    time. This class leverages Pydantic's `BaseModel` for data validation and serialization.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    event_id: uuid.UUID = Field(
        alias="event_time",
        description="Unique identifier for the audit event"
    )
    event_type: str = Field(
        description="Type of the audit event (e.g., READ, CHANGE)",
    )
    institution_id: uuid.UUID = Field(
        description="Unique identifier of the institution associated with this event",
    )
    human_time: Optional[datetime] = Field(
        default=None,
        description="Human-readable timestamp when the event occurred",
    )


class AuditReadResponse(AuditEventBase):
    """
    Represents a response for an audit read event.

    This class is used to encapsulate the details of an audit read
    event response. It inherits from `AuditEventBase` and defines
    specific properties related to read events.
    """
    event_type: str = Field(
        default="READ",
        description="Type of the audit event, fixed as READ for this response",
    )


class AuditChangeResponse(AuditEventBase):
    """
    Represents an audit change event response.

    This class is used to define the response for an audit event
    involving a change. It extends the base functionality of the
    `AuditEventBase` class and contains attributes specific to
    change-related audit events.
    """
    event_type: str = Field(
        default="CHANGE",
        description="Type of the audit event, fixed as CHANGE for this response",
    )
    change_code: ChangeCode = Field(
        description="Code representing the specific type of change that occurred",
    )
    change_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="JSON object containing detailed information about the change",
    )


AuditResponse = Union[AuditChangeResponse, AuditReadResponse]
