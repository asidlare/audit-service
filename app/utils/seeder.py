import asyncio
import json
import uuid
from typing import Any

from app.config import config
from app.services.database import db
from app.services.utils import cassandra_future_to_asyncio


# Batch size for inserting events
BATCH_SIZE = 50


QUERIES = [
    """
    INSERT INTO audit_by_person
    (person_id, event_time, event_type, institution_id, change_code, change_json)
    VALUES (?, ?, 'CHANGE', ?, ?, ?)
    """,
    """
    INSERT INTO changes_by_inst
        (institution_id, changed_at, person_id, change_code, change_json)
    VALUES (?, ?, ?, ?, ?)
    """,
    """
    INSERT INTO changes_by_code
        (change_code, changed_at, person_id, institution_id, change_json)
    VALUES (?, ?, ?, ?, ?)
    """
]


async def insert_change_event(
        change: dict,
        prepared_queries: list[Any]
) -> None:
    """
    Asynchronously inserts a change event into multiple database tables. This function
    prepares and executes database insert operations for a given change event, targeting
    specific tables (`audit_by_person`, `changes_by_inst`, and `changes_by_code`) in
    parallel for optimized performance.

    :param change: Dictionary containing the details of the change event. Expected keys
        include 'person_id' (str), 'institution_id' (str), 'change_code' (str), and
        'payload' (dict).
    :param prepared_queries: A list of precompiled database query objects. Each query
        corresponds to one of the target tables to which the event will be added.
    :return: None
    """
    p_id = uuid.UUID(change["person_id"])
    i_id = uuid.UUID(change["institution_id"])
    code = change["change_code"]
    js = json.dumps(change["payload"])
    event_time = uuid.uuid1()  # Generate a single TimeUUID for consistency

    # Params preparation for each table
    params = [
        (p_id, event_time, i_id, code, js),  # audit_by_person
        (i_id, event_time, p_id, code, js),  # changes_by_inst
        (code, event_time, p_id, i_id, js)  # changes_by_code
    ]

    # Async execution for each table - 3 inserts in parallel
    futures = [
        db.session.execute_async(prepared_queries[i], params[i])
        for i in range(len(prepared_queries))
    ]

    # Convert Cassandra futures to asyncio futures and await them
    await asyncio.gather(*[cassandra_future_to_asyncio(f) for f in futures])


async def seed() -> None:
    """
    Seeds the database with initial data from a JSON file, inserting events in
    batches to prevent overload and saving example IDs for testing purposes.

    The function connects to the database, reads the seed data from a JSON file,
    prepares database queries for efficient execution, and processes the change
    events sequentially in batches. Once the data is seeded, it saves a subset of
    test identifiers to a file for testing purposes and then closes the database
    connection.

    :raises IOError: If the seed data file or test ID file cannot be read or written.
    :raises Exception: If any errors occur during database operations or event insertion.

    :return: None
    """
    # Database connection using configuration
    db.connect(config.CASSANDRA_HOSTS)

    with open("seed_data.json", "r") as f:
        data = json.load(f)

    changes = data["events"]["changes"]
    print(f"Loading {len(changes)} change events into database...")

    # Preparation of queries (once at the beginning for performance
    prepared_queries = [db.session.prepare(query) for query in QUERIES]

    tasks = [
        insert_change_event(change, prepared_queries)
        for change in changes
    ]

    total = len(tasks)

    for i in range(0, total, BATCH_SIZE):
        batch = tasks[i:i + BATCH_SIZE]
        await asyncio.gather(*batch)
        print(f"Progress: {min(i + BATCH_SIZE, total)}/{total} events inserted")

    # Writing example test IDs for testing purposes
    with open("test_ids.json", "w") as f:
        json.dump(
            {
                "person_id": changes[0]["person_id"],
                "institution_id": changes[0]["institution_id"],
                "code": changes[0]["change_code"],
            },
            f,
            indent=2
        )

    print("Data uploaded into database.")
    print("Test IDs saved to test_ids.json")

    # Closing database connection
    db.close()


if __name__ == "__main__":
    asyncio.run(seed())
