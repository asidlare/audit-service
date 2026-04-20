import asyncio
import uuid
import json
from typing import Any

from app.logger import logger
from app.services.database import db


async def log_read_event(
    institution_id: uuid.UUID,
    person_ids: list[uuid.UUID]
) -> dict[str, Any]:
    """
    Logs a "READ" event for the specified institution and list of person IDs. Each event
    is recorded in the `audit_by_person` table with a unique event time (TimeUUID),
    and the type of event ("READ") is logged asynchronously for each person.

    :param institution_id: A UUID representing the institution the event is associated with.
    :param person_ids: A list of UUIDs representing the persons tied to the "READ" event.
    :return: A dictionary containing the result of the operation, including the status and
             the unique event ID generated for the operation.
    """
    event_time = uuid.uuid1()  # Generowanie TimeUUID

    query = """
        INSERT INTO audit_by_person (person_id, event_time, event_type, institution_id)
        VALUES (%s, %s, 'READ', %s)
        """

    # Async execution for each person ID
    tasks = [
        db.execute_async(query, (p_id, event_time, institution_id))
        for p_id in person_ids
    ]
    await asyncio.gather(*tasks)

    logger.info(f"Logged READ event for {len(person_ids)} person(s), event_id={event_time}")
    return {"status": "success", "event_id": str(event_time)}


async def log_change_event(
    person_id: uuid.UUID,
    institution_id: uuid.UUID,
    change_code: str,
    change_json: dict[str, Any]
) -> dict[str, Any]:
    """
    Logs a change event by recording relevant information into multiple database tables.
    This operation is asynchronous and performs database writes in parallel to ensure
    high performance. The function records changes in three tables categorized by
    person, institution, and change code. All changes are timestamped and include
    details about the person initiating the event.

    :param person_id: A UUID representing the identifier of the person associated with the
        change event.
    :param institution_id: A UUID representing the identifier of the institution related to
        the change event.
    :param change_code: A string representing the code or identifier of the specific change
        being logged.
    :param change_json: A dictionary containing the details of the change in JSON format.
    :return: A dictionary representing the status of the operation, including a unique
        event identifier.
    """
    event_time = uuid.uuid1()
    json_payload = json.dumps(change_json)

    # Convert ChangeCode enum to string if needed
    if hasattr(change_code, 'value'):
        change_code = change_code.value

    # Queries for each table
    queries_and_params = [
        (
            """INSERT INTO audit_by_person
               (person_id, event_time, event_type, institution_id, change_code, change_json)
               VALUES (%s, %s, 'CHANGE', %s, %s, %s)""",
            (person_id, event_time, institution_id, change_code, json_payload)
        ),
        (
            """INSERT INTO changes_by_inst
                   (institution_id, changed_at, person_id, change_code, change_json)
               VALUES (%s, %s, %s, %s, %s)""",
            (institution_id, event_time, person_id, change_code, json_payload)
        ),
        (
            """INSERT INTO changes_by_code
                   (change_code, changed_at, person_id, institution_id, change_json)
               VALUES (%s, %s, %s, %s, %s)""",
            (change_code, event_time, person_id, institution_id, json_payload)
        )
    ]

    # Async execution of all writes in parallel
    tasks = [db.execute_async(query, params) for query, params in queries_and_params]
    await asyncio.gather(*tasks)

    return {"status": "success", "event_id": str(event_time)}
