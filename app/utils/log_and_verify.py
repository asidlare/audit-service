import json
import httpx
import asyncio
import uuid
from datetime import datetime
from typing import Any

from app.config import config
from app.services.database import db
from app.api.audit import map_row_to_response
from app.schemas.enums import ChangeCode


# ============================================================================
# API CALLS (INSERT via endpoints)
# ============================================================================

async def insert_read_event_via_api(
    client: httpx.AsyncClient,
    person_ids: list[str],
    institution_id: str
) -> dict[str, Any]:
    """
    Inserts a read event via an API endpoint. This function sends a POST request
    to log a read event, associating it with specified person IDs and the given
    institution ID. It raises an HTTPStatusError if the response status code
    is not 201, indicating a failure during the request.

    :param client: The asynchronous HTTP client used to send the POST request.
    :type client: httpx.AsyncClient
    :param person_ids: A list of person IDs to be associated with the read event.
    :type person_ids: list[str]
    :param institution_id: The ID of the institution related to the read event.
    :type institution_id: str
    :return: The JSON response from the API, parsed into a dictionary.
    :rtype: dict[str, Any]
    :raises httpx.HTTPStatusError: If the POST request does not return a 201
        status code.
    """
    payload = {
        "institution_id": institution_id,
        "person_ids": person_ids
    }

    response = await client.post("/api_v1/log/read", json=payload)

    if response.status_code != 201:
        raise httpx.HTTPStatusError(
            f"POST /log/read failed: {response.status_code} - {response.text}",
            request=response.request,
            response=response
        )

    return response.json()


async def insert_change_event_via_api(
    client: httpx.AsyncClient,
    person_id: str,
    institution_id: str,
    change_code: str,
    change_json: dict
) -> dict[str, Any]:
    """
    Sends a change event to the API via a POST request and returns the response data.

    The function is asynchronous and uses httpx.AsyncClient to perform the HTTP
    request. It sends the provided details about a change event, such as person ID,
    institution ID, change code, and additional change details as a JSON payload.

    :param client: An instance of httpx.AsyncClient used to make the HTTP request.
    :param person_id: The unique identifier of the person associated with the
        change event.
    :param institution_id: The unique identifier of the institution associated
        with the change event.
    :param change_code: A code representing the type or category of the change
        event.
    :param change_json: A dictionary containing additional details regarding
        the change event.
    :return: The JSON response from the API, parsed into a dictionary.
    """
    payload = {
        "person_id": person_id,
        "institution_id": institution_id,
        "change_code": change_code,
        "change_json": change_json
    }

    response = await client.post("/api_v1/log/change", json=payload)

    if response.status_code != 201:
        raise httpx.HTTPStatusError(
            f"POST /log/change failed: {response.status_code} - {response.text}",
            request=response.request,
            response=response
        )

    return response.json()


# ============================================================================
# DATABASE QUERIES (READ via direct queries)
# ============================================================================

async def query_person_events(person_id: uuid.UUID) -> list[dict[str, Any]]:
    """
    Query the events associated with a specific person from the database asynchronously.

    This function executes a query to fetch up to 10 records related to a given
    person's ID from the `audit_by_person` table. The results are then mapped to
    a response format using `map_row_to_response`.

    :param person_id: The unique identifier of the person whose events are to be queried.
    :type person_id: uuid.UUID
    :return: A list containing up to 10 records from the `audit_by_person` table
        mapped to a specific response format.
    :rtype: list[dict[str, Any]]
    """
    query = "SELECT * FROM audit_by_person WHERE person_id = %s LIMIT 10"
    rows = await db.execute_async(query, (person_id,))
    return [map_row_to_response(row) for row in rows]


async def query_institution_changes(institution_id: uuid.UUID) -> list[dict[str, Any]]:
    """
    Query the most recent changes related to a specific institution from the database.

    This function executes an asynchronous query to fetch up to ten change records
    for the institution matching the provided `institution_id`. Each record is
    processed into a dictionary structure before it is returned.

    :param institution_id: The unique identifier of the institution.
    :type institution_id: uuid.UUID
    :return: A list containing up to ten dictionaries where each dictionary
        represents a change associated with the specified institution.
    :rtype: list[dict[str, Any]]
    """
    query = "SELECT * FROM changes_by_inst WHERE institution_id = %s LIMIT 10"
    rows = await db.execute_async(query, (institution_id,))
    return [map_row_to_response(row) for row in rows]


async def query_code_changes_for_person(
    change_code: str,
    person_id: uuid.UUID
) -> list[dict[str, Any]]:
    """
    Query the code changes associated with a specific person.

    This asynchronous function interacts with the changes_by_code table
    to retrieve up to 10 rows that match the provided change code and
    person ID. It processes and maps the resulting rows to the response
    format before returning them.

    :param change_code: The code identifying the type or category of changes
    :param person_id: The unique identifier of the person whose changes
                      are being queried
    :return: A list of dictionaries containing the mapped rows corresponding
             to the matching code changes and person ID
    """
    query = """
        SELECT * FROM changes_by_code
        WHERE change_code = %s AND person_id = %s
        LIMIT 10
        ALLOW FILTERING
    """
    rows = await db.execute_async(query, (change_code, person_id))
    return [map_row_to_response(row) for row in rows]


# ============================================================================
# SERIALIZATION HELPER
# ============================================================================

def serialize_for_json(obj: Any) -> Any:
    """
    Serialize an object to make it compatible with JSON encoding.

    This function takes an object and serializes its data, converting certain
    types such as `uuid.UUID` and `datetime` into formats that are natively
    supported by JSON encoding. For collections like dictionaries and lists,
    this function applies serialization recursively to their elements.

    :param obj: The object to be serialized. Can be of any data type, such as
        a UUID, datetime, dictionary, list, or other primitive types.
    :type obj: Any

    :return: The serialized version of the object, where specific types like
        `uuid.UUID` are converted to `str`, `datetime` to `isoformat` strings,
        and collections are recursively processed.
    :rtype: Any
    """
    if isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    return obj


# ============================================================================
# TEST SCENARIOS
# ============================================================================

async def test_read_event_scenario(
    client: httpx.AsyncClient,
    person_id: uuid.UUID,
    institution_id: uuid.UUID
) -> dict[str, Any]:
    """
    Asynchronously tests the "READ" event scenario for a specific person within an
    institution. This function first simulates an event insertion via an API, waits
    for data propagation, and verifies the event's presence in the database. The
    test collects and returns detailed information about the API insertion and
    database query results.

    :param client: HTTP client for making asynchronous requests to the API
    :type client: httpx.AsyncClient
    :param person_id: Unique identifier of the person whose event is being tested
    :type person_id: uuid.UUID
    :param institution_id: Unique identifier of the institution associated with the event
    :type institution_id: uuid.UUID
    :return: Dictionary containing event type, associated person and institution,
             API insertion details, and database query results
    :rtype: dict[str, Any]
    """
    print(f"\n  Test: READ event for person {person_id}")

    # Insert via API
    api_response = await insert_read_event_via_api(
        client,
        [str(person_id)],
        str(institution_id)
    )
    event_id = api_response.get("event_id")
    print(f"    Inserted via API, event_id: {event_id}")

    # Wait for propagation
    await asyncio.sleep(0.5)

    # Query from database
    results = await query_person_events(person_id)

    # Find our event
    our_event = next(
        (r for r in results if str(r.get("event_time")) == str(event_id)),
        None
    )

    return {
        "event_type": "READ",
        "person_id": str(person_id),
        "institution_id": str(institution_id),
        "api_insert": {
            "endpoint": "POST /api_v1/log/read",
            "response": api_response
        },
        "database_query": {
            "query": f"SELECT * FROM audit_by_person WHERE person_id = {person_id}",
            "found": our_event is not None,
            "retrieved_event": serialize_for_json(our_event),
            "total_events": len(results)
        }
    }


async def test_change_event_scenario(
    client: httpx.AsyncClient,
    person_id: uuid.UUID,
    institution_id: uuid.UUID,
    change_code: str,
    change_json: dict
) -> dict[str, Any]:
    """
    Handles the testing of a 'CHANGE' event scenario for a specific person and institution
    by simulating the creation of a change event, waiting for processing, and verifying
    its presence across associated database tables.

    :param client: Async HTTP client utilized to send API requests.
    :type client: httpx.AsyncClient
    :param person_id: Unique identifier of the person involved in the change event.
    :type person_id: uuid.UUID
    :param institution_id: Unique identifier of the institution associated with the change event.
    :type institution_id: uuid.UUID
    :param change_code: Code representing the type of change event.
    :type change_code: str
    :param change_json: Dictionary containing additional details about the change event.
    :type change_json: dict
    :return: A dictionary summarizing the test results, including API response,
        database query insights, and verification of event propagation.
    :rtype: dict[str, Any]
    """
    print(f"\n  Test: CHANGE event ({change_code}) for person {person_id}")

    # Insert via API
    api_response = await insert_change_event_via_api(
        client,
        str(person_id),
        str(institution_id),
        change_code,
        change_json
    )
    event_id = api_response.get("event_id")
    print(f"    Inserted via API, event_id: {event_id}")

    # Wait for propagation
    await asyncio.sleep(0.5)

    # Query from all 3 tables
    person_results = await query_person_events(person_id)
    inst_results = await query_institution_changes(institution_id)
    code_results = await query_code_changes_for_person(change_code, person_id)

    # Find our event in each table
    event_id_str = str(event_id)
    person_event = next(
        (r for r in person_results if str(r.get("event_time")) == event_id_str),
        None
    )
    inst_event = next(
        (r for r in inst_results if str(r.get("event_time")) == event_id_str),
        None
    )
    code_event = next(
        (r for r in code_results if str(r.get("event_time")) == event_id_str),
        None
    )

    return {
        "event_type": "CHANGE",
        "change_code": change_code,
        "person_id": str(person_id),
        "institution_id": str(institution_id),
        "api_insert": {
            "endpoint": "POST /api_v1/log/change",
            "payload": {
                "person_id": str(person_id),
                "institution_id": str(institution_id),
                "change_code": change_code,
                "change_json": change_json
            },
            "response": api_response
        },
        "database_queries": {
            "by_person": {
                "query": f"SELECT * FROM audit_by_person WHERE person_id = {person_id}",
                "found": person_event is not None,
                "retrieved_event": serialize_for_json(person_event)
            },
            "by_institution": {
                "query": f"SELECT * FROM changes_by_inst WHERE institution_id = {institution_id}",
                "found": inst_event is not None,
                "retrieved_event": serialize_for_json(inst_event)
            },
            "by_code_filtered": {
                "query": f"SELECT * FROM changes_by_code WHERE change_code = '{change_code}' AND person_id = {person_id} ALLOW FILTERING",
                "found": code_event is not None,
                "retrieved_event": serialize_for_json(code_event)
            }
        },
        "found_in_all_tables": all([person_event, inst_event, code_event])
    }


# ============================================================================
# MAIN
# ============================================================================

async def run_insert_and_query_tests() -> None:
    """
    Executes a series of tests including insertions (via API) and queries (directly in the database)
    to validate the correctness of the data storage and retrieval mechanisms. The tests include scenarios
    for reading and changing event data, leveraging a set of predefined change codes and payloads. All test
    results are consolidated into a report saved in JSON format, and a summary is printed to the console.

    :return: None
    :rtype: NoneType

    :raises Exception: Raised if there are errors during the execution of individual test scenarios.

    :notes:
        - Connects to a Cassandra database based on configuration settings.
        - Utilizes the `httpx.AsyncClient` for asynchronous event API calls.
        - Generates reports with test results on success and error cases.
        - Ensures database connection is closed after execution, regardless of success or failure.
    """
    print(f"{'=' * 60}")
    print("Insert (API) and Query (Database) Test")
    print(f"{'=' * 60}")

    # Database connection using configuration (like seeder.py)
    db.connect(config.CASSANDRA_HOSTS)

    try:
        # Create test data
        institution_id = uuid.uuid4()
        person_ids = [uuid.uuid4() for _ in range(3)]

        print(f"\nTest Configuration:")
        print(f"  Institution: {institution_id}")
        for i, pid in enumerate(person_ids, 1):
            print(f"  Person {i}:    {pid}")

        report = {
            "timestamp": datetime.now().isoformat(),
            "test_configuration": {
                "institution_id": str(institution_id),
                "person_ids": [str(p) for p in person_ids]
            },
            "tests": []
        }

        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:

            # Test 1: READ event
            print(f"\n{'=' * 60}")
            print("Test 1: READ Event")
            print(f"{'=' * 60}")

            try:
                read_result = await test_read_event_scenario(
                    client,
                    person_ids[0],
                    institution_id
                )
                report["tests"].append(read_result)

                status = " FOUND" if read_result["database_query"]["found"] else " NOT FOUND"
                print(f"    Result: {status}")
            except Exception as e:
                print(f"     Error: {e}")
                report["tests"].append({
                    "event_type": "READ",
                    "error": str(e)
                })

            # Tests 2-7: CHANGE events
            print(f"\n{'=' * 60}")
            print("Tests 2-7: CHANGE Events")
            print(f"{'=' * 60}")

            payloads = {
                ChangeCode.PASSWORD_RESET: {
                    "new_password_hash": "hash_test123",
                    "reset_by": "admin",
                    "timestamp": datetime.now().isoformat()
                },
                ChangeCode.EMAIL_CHANGE: {
                    "old_email": "old@test.com",
                    "new_email": "new@test.com",
                    "verified": True
                },
                ChangeCode.ADDRESS_UPDATE: {
                    "street": "Test Street 123",
                    "city": "Warsaw",
                    "zip": "00-001"
                },
                ChangeCode.PERMISSION_GRANT: {
                    "permission": "admin",
                    "granted_by": "system",
                    "scope": "full"
                },
                ChangeCode.STATUS_INACTIVE: {
                    "reason": "suspended",
                    "date": datetime.now().isoformat(),
                    "reversible": True
                },
                ChangeCode.LIMIT_INCREASE: {
                    "old_limit": 1000,
                    "new_limit": 5000,
                    "currency": "PLN",
                    "approved_by": "manager"
                }
            }

            for i, change_code in enumerate(ChangeCode):
                person_id = person_ids[i % len(person_ids)]

                try:
                    change_result = await test_change_event_scenario(
                        client,
                        person_id,
                        institution_id,
                        change_code.value,
                        payloads[change_code]
                    )
                    report["tests"].append(change_result)

                    status = " FOUND IN ALL" if change_result["found_in_all_tables"] else " MISSING"
                    print(f"    Result: {status}")
                except Exception as e:
                    print(f"     Error: {e}")
                    report["tests"].append({
                        "event_type": "CHANGE",
                        "change_code": change_code.value,
                        "error": str(e)
                    })

        # Save reports
        with open("insert_query_report.json", "w") as f:
            json.dump(report, f, indent=2)

        with open("insert_test_ids.json", "w") as f:
            json.dump({
                "institution_id": str(institution_id),
                "person_id": str(person_ids[0]),
                "person_ids": [str(p) for p in person_ids],
                "code": ChangeCode.PERMISSION_GRANT.value
            }, f, indent=2)

        # Summary
        print(f"\n{'=' * 60}")
        print("Summary")
        print(f"{'=' * 60}")

        successful_tests = [t for t in report["tests"] if "error" not in t]
        read_tests = [t for t in successful_tests if t["event_type"] == "READ"]
        change_tests = [t for t in successful_tests if t["event_type"] == "CHANGE"]

        read_success = sum(1 for t in read_tests if t["database_query"]["found"])
        change_success = sum(1 for t in change_tests if t["found_in_all_tables"])

        print(f"READ events:   {read_success}/{len(read_tests)} found in database")
        print(f"CHANGE events: {change_success}/{len(change_tests)} found in all tables")
        print(f"Errors:        {len(report['tests']) - len(successful_tests)}")
        print(f"\nReports saved:")
        print(f"  - insert_query_report.json")
        print(f"  - insert_test_ids.json")
        print(f"{'=' * 60}")

    finally:
        # Closing database connection
        db.close()


if __name__ == "__main__":
    asyncio.run(run_insert_and_query_tests())
