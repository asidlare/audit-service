import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.schemas.enums import ChangeCode


def generate_institutions(num: int) -> list[dict[str, str]]:
    """
    Generates a list of dictionaries representing institutions with unique identifiers, names,
    and randomly assigned types. This function is useful for creating mock data sets of institutions.

    :param num: The number of institutions to generate.
    :type num: int
    :return: A list of dictionaries, where each dictionary contains the `id`, `name`,
        and `type` of an institution.
    :rtype: list[dict[str, str]]
    """
    return [
        {
            "id": str(uuid.uuid4()),
            "name": f"Institution {i}",
            "type": random.choice(["Bank", "Hospital", "University", "Government", "Enterprise"])
        }
        for i in range(num)
    ]


def generate_persons(num: int) -> list[dict[str, str]]:
    """
    Generates a list of dictionaries, where each dictionary represents a person
    with a unique identifier, name, and email address.

    :param num: Number of person dictionaries to generate.
    :type num: int
    :return: A list of dictionaries, each containing an "id", "name", and "email"
        for a person.
    :rtype: list[dict[str, str]]
    """
    return [
        {
            "id": str(uuid.uuid4()),
            "name": f"Person {i}",
            "email": f"person{i}@example.com"
        }
        for i in range(num)
    ]


def create_payload_for_code(code: ChangeCode, index: int) -> dict[str, Any]:
    """
    Creates a payload dictionary based on the `ChangeCode` and an index.

    For each `ChangeCode`, this function generates a unique payload with structured
    data relevant to the operation described by the code. The payload is dynamically
    populated with random or computed values, depending on the specific change being
    handled.

    :param code: A value of the `ChangeCode` enumeration that specifies the type
        of change for which the payload will be generated.
    :param index: An integer used for generating certain payload data, such as
        email addresses or other indexed values.
    :return: A dictionary containing the generated payload data corresponding
        to the specified `ChangeCode`.
    """
    payloads = {
        ChangeCode.PASSWORD_RESET: {
            "new_password_hash": f"hash_{uuid.uuid4().hex[:16]}",
            "reset_by": random.choice(["admin", "self", "support"]),
            "timestamp": datetime.now().isoformat()
        },
        ChangeCode.EMAIL_CHANGE: {
            "old_email": f"old_{index}@example.com",
            "new_email": f"new_{index}@example.com",
            "verified": random.choice([True, False])
        },
        ChangeCode.ADDRESS_UPDATE: {
            "street": f"{random.randint(1, 999)} {random.choice(['Main', 'Oak', 'Maple', 'Pine'])} St",
            "city": random.choice(["Warsaw", "Krakow", "Gdansk", "Wroclaw", "Poznan"]),
            "zip": f"{random.randint(0, 99):02d}-{random.randint(0, 999):03d}"
        },
        ChangeCode.PERMISSION_GRANT: {
            "permission": random.choice(["read", "write", "admin", "delete", "export"]),
            "granted_by": random.choice(["system", "admin", "manager"]),
            "scope": random.choice(["full", "limited", "temporary"])
        },
        ChangeCode.STATUS_INACTIVE: {
            "reason": random.choice(["suspended", "terminated", "retired", "on_leave"]),
            "date": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
            "reversible": random.choice([True, False])
        },
        ChangeCode.LIMIT_INCREASE: {
            "old_limit": (old := random.randint(1000, 5000)),
            "new_limit": old + random.randint(1000, 5000),
            "currency": "PLN",
            "approved_by": random.choice(["manager", "director", "system"])
        }
    }
    return payloads[code]


def generate_change_events(
        num: int,
        persons: list[dict[str, str]],
        institutions: list[dict[str, str]]
) -> list[dict[str, Any]]:
    """
    Generate a list of change events based on provided details.

    This function creates a specified number of change event records by randomly
    selecting a person and an institution from the provided lists. Each event
    includes details such as a person ID, institution ID, a change code, and a
    generated payload.

    :param num: The number of change events to generate.
    :type num: int
    :param persons: A list of dictionaries, where each dictionary represents
        a person and contains at least an "id" key.
    :type persons: list[dict[str, str]]
    :param institutions: A list of dictionaries, where each dictionary
        represents an institution and contains at least an "id" key.
    :type institutions: list[dict[str, str]]
    :return: A list of dictionaries, where each dictionary represents a
        change event containing "person_id," "institution_id," "change_code,"
        and "payload".
    :rtype: list[dict[str, Any]]
    """
    changes = []
    for i in range(num):
        person = random.choice(persons)
        institution = random.choice(institutions)
        code = random.choice(list(ChangeCode))

        changes.append({
            "person_id": person["id"],
            "institution_id": institution["id"],
            "change_code": code.value,
            "payload": create_payload_for_code(code, i)
        })

    return changes


def generate_read_events(
        num: int,
        persons: list[dict[str, str]],
        institutions: list[dict[str, str]]
) -> list[dict[str, Any]]:
    """
    Generates a specified number of "read events" by randomly associating institutions with
    a set of persons. Each "read event" contains the identifier of an institution and a
    list of person identifiers. The number of persons in a single read event is selected
    randomly, with an upper limit of either 5 or the total number of persons provided,
    whichever is smaller.

    :param num: The number of "read events" to generate.
    :type num: int
    :param persons: A list of dictionaries, where each dictionary represents a person
        and includes their attributes such as an `"id"` key.
    :type persons: list[dict[str, str]]
    :param institutions: A list of dictionaries, where each dictionary represents
        an institution and includes their attributes such as an `"id"` key.
    :type institutions: list[dict[str, str]]
    :return: A list of dictionaries, where each dictionary represents a "read event,"
        containing an `institution_id` and a list of `person_ids`.
    :rtype: list[dict[str, Any]]
    """
    reads = []
    for _ in range(num):
        institution = random.choice(institutions)
        num_persons_in_read = random.randint(1, min(5, len(persons)))
        person_ids = [random.choice(persons)["id"] for _ in range(num_persons_in_read)]

        reads.append({
            "institution_id": institution["id"],
            "person_ids": person_ids
        })

    return reads
