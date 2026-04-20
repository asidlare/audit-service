import uuid
import json
from cassandra.util import datetime_from_uuid1
from typing import Any

from app.services.database import db



def map_row_to_response(row) -> dict[str, Any]:
    """
    Maps a database row to a response dictionary.

    This function converts a given database row to a dictionary, extracts and standardizes
    field naming and formats, parses JSON fields, and ensures datetime values are properly
    handled. It is particularly designed to handle rows with fields that include UUID-based
    timestamps and JSON strings.

    :param row: A database row, expected to have fields accessible as dictionary keys or
        named tuple attributes. The row should include either an `event_time` or `changed_at`
        field as a timestamp, optionally a `change_json` field as a JSON string,
        and other relevant data fields.
    :type row: RowType

    :return: A dictionary representation of the row with standardized field naming
        (`event_time` and `human_time` for timestamp fields) and JSON fields parsed into
        dictionary objects. If the JSON parsing fails, the `change_json` field will return
        an error dictionary.
    :rtype: Dict
    """
    data = dict(row._asdict())

    # TimeUUID handling -> datetime and field name standardization
    ts_field = "event_time" if "event_time" in data else "changed_at"
    if data.get(ts_field):
        data["event_time"] = data[ts_field]
        data["human_time"] = datetime_from_uuid1(data[ts_field])

    # JSON parsing
    if data.get("change_json"):
        try:
            data["change_json"] = json.loads(data["change_json"])
        except (json.JSONDecodeError, TypeError):
            data["change_json"] = {"error": "Invalid JSON payload"}

    return data


async def get_person_history(p_id: uuid.UUID, limit: int = 20) -> list[dict[str, Any]]:
    """
    Retrieve the history of changes associated with a given person identifier.

    This function queries the `audit_by_person` table to fetch up to a specified
    number of audit entries related to a particular person. The result is mapped
    into a list of dictionaries suitable for response serialization.

    :param p_id: A UUID identifying the person whose history is being retrieved.
    :param limit: The maximum number of audit entries to retrieve. Defaults to 20.
    :return: A list of dictionaries, where each dictionary represents a single
        audit entry containing details about the change.
    """
    query = "SELECT * FROM audit_by_person WHERE person_id = %s LIMIT %s"
    rows = await db.execute_async(query, (p_id, limit))
    return [map_row_to_response(r) for r in rows]


async def get_institution_changes(i_id: uuid.UUID, limit: int = 20) -> list[dict[str, Any]]:
    """
    Fetches a list of changes pertaining to a specific institution asynchronously.

    This function queries a database to retrieve records of changes associated with
    a given institution ID. It allows an optional limit on the number of records
    retrieved. The result is returned as a list of dictionary objects, where each
    dictionary represents a row mapped into a structured response.

    :param i_id: The unique identifier of the institution for which changes are
        queried.
    :type i_id: uuid.UUID
    :param limit: The maximum number of changes to fetch. Defaults to 20.
    :type limit: int
    :return: A list of dictionaries representing the changes made for the
        specified institution.
    :rtype: list[dict[str, Any]]
    """
    query = "SELECT * FROM changes_by_inst WHERE institution_id = %s LIMIT %s"
    rows = await db.execute_async(query, (i_id, limit))
    return [map_row_to_response(r) for r in rows]


async def get_changes_by_type(code: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Fetches a list of changes from the database filtered by a specific code and limited
    to the specified number of results.

    This asynchronous function queries the database for changes based on the provided
    change code. The results are then transformed to a response format before being
    returned as a list.

    :param code: The code used to filter the changes. Must be a string.
    :type code: str
    :param limit: The maximum number of changes to retrieve. Defaults to 20 if not
        specified.
    :type limit: int
    :return: A list of dictionaries containing changes, with each dictionary mapping
        column names to their corresponding values.
    :rtype: list[dict[str, Any]]
    """
    query = "SELECT * FROM changes_by_code WHERE change_code = %s LIMIT %s"
    rows = await db.execute_async(query, (code, limit))
    return [map_row_to_response(r) for r in rows]
