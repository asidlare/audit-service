import uuid
from fastapi import APIRouter, status

from app.api.audit import (
    get_institution_changes,
    get_changes_by_type,
    get_person_history,
)
from app.schemas.audit import AuditResponse, AuditChangeResponse


router = APIRouter()


@router.get(
    "/person/{p_id}",
    status_code=status.HTTP_200_OK,
    response_model=list[AuditResponse],
)
async def get_person_history_endpoint(p_id: uuid.UUID, limit: int = 20):
    """
    Endpoint to retrieve the audit history of a specific person, identified by their unique
    ID. Supports optional limiting of the number of records returned.
    """
    return await get_person_history(p_id, limit)


@router.get(
    "/institution/{i_id}",
    status_code=status.HTTP_200_OK,
    response_model=list[AuditChangeResponse],
)
async def get_institution_changes_endpoint(i_id: uuid.UUID, limit: int = 20):
    """
    Retrieve a list of audit change records for a specific institution.

    This endpoint fetches a list of audit logs associated with an institution,
    identified by its unique ID. The number of audit records retrieved can
    be limited by specifying the `limit` parameter.
    """
    return await get_institution_changes(i_id, limit)


@router.get(
    "/code/{code}",
    status_code=status.HTTP_200_OK,
    response_model=list[AuditChangeResponse],
)
async def get_changes_by_type_endpoint(code: str, limit: int = 20):
    """
    Fetch a list of audit changes filtered by a specific type.

    This endpoint retrieves audit changes based on the specified type code.
    It allows for an optional limit on the number of results to be returned.
    The response is provided as a list of `AuditChangeResponse` objects.
    """
    return await get_changes_by_type(code, limit)
