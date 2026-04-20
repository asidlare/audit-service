import uuid
from pydantic import BaseModel, Field
from typing import Any

from app.schemas.enums import ChangeCode


class ReadEventRequest(BaseModel):
    """
    Represents a request to read an event related to an institution and specific persons.

    This class is used to encapsulate the necessary data required for retrieving event
    information. It includes an identifier for the institution and a list of identifiers
    for the associated persons.
    """
    institution_id: uuid.UUID = Field(
        description="Unique identifier of the institution for which events are being retrieved",
    )
    person_ids: list[uuid.UUID] = Field(
        description="List of unique identifiers for persons whose events should be retrieved",
    )


class ChangeEventRequest(BaseModel):
    """
    Represents a request to initiate a change event.

    This class is used to capture details for a change event request involving a
    specific person, institution, and the nature of the change. It acts as a
    container for passing data related to a change event, facilitating its
    processing and handling.
    """
    person_id: uuid.UUID = Field(
        description="Unique identifier of the person associated with this change event",
    )
    institution_id: uuid.UUID = Field(
        description="Unique identifier of the institution where the change occurred",
    )
    change_code: ChangeCode = Field(
        description="""Code representing the specific type of change being logged. Possible values:
            - PASSWORD_RESET: User password has been reset or changed
            - EMAIL_CHANGE: User email address has been modified
            - ADDRESS_UPDATE: User physical or mailing address has been updated
            - PERMISSION_GRANT: New permissions or access rights have been granted to the user
            - STATUS_INACTIVE: User account status has been set to inactive
            - LIMIT_INCREASE: User's operational or financial limit has been increased"""
    )
    change_json: dict[str, Any] = Field(
        description="JSON object containing detailed information about the change",
    )


class LogEventResponse(BaseModel):
    """
    Summary of what the class does.

    Represents the response for a log event operation. This class holds the
    status of the operation and the unique identifier for the event.
    """
    status: str = Field(
        description="Operation status indicating success or failure of the log event",
        examples=["success"]
    )
    event_id: str = Field(
        description="Unique identifier (UUID1) of the created audit event",
        examples=["a1b2c3d4-e5f6-11eb-9a03-0242ac130003"]
    )
