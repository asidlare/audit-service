from fastapi import APIRouter, status

from app.api.audit_log import (
    log_change_event,
    log_read_event,
)
from app.schemas.audit_log import (
    ChangeEventRequest,
    LogEventResponse,
    ReadEventRequest,
)


router = APIRouter()


@router.post(
    "/read",
    status_code=status.HTTP_201_CREATED,
    response_model=LogEventResponse,
)
async def log_read_event_endpoint(event: ReadEventRequest):
    """
    Post endpoint to log a read event. This endpoint is responsible for asynchronously
    logging read events by delegating the business logic to the `log_read_event` function.
    It ensures the event logging request is processed, and the resulting data is returned
    in the form of a `LogEventResponse` model.
    """
    return await log_read_event(
        institution_id=event.institution_id,
        person_ids=event.person_ids
    )


@router.post(
    "/change",
    status_code=status.HTTP_201_CREATED,
    response_model=LogEventResponse,
)
async def log_change_event_endpoint(event: ChangeEventRequest):
    """
    Handles HTTP POST requests for logging change events.

    This endpoint is used to log an event associated with a change that has occurred,
    such as a modification related to a person or institution. The details of the
    change are extracted from the request body and passed to the underlying
    `log_change_event` function for processing.
    """
    return await log_change_event(
        person_id=event.person_id,
        institution_id=event.institution_id,
        change_code=event.change_code,
        change_json=event.change_json
    )
