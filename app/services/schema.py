"""
Schema for creating Cassandra keyspace and tables for audit logging.

This module contains a predefined schema represented as CQL statements for
managing audit log data within a Cassandra database. The schema includes
definitions for structures to store changes by institution, audits by person,
and changes by specific codes.

Keyspace:
---------
audit_logs :
    Main keyspace for storing all audit-related data. Configured with SimpleStrategy
    replication and replication factor of 3 for high availability and fault tolerance.

Tables:
-------
changes_by_inst :
    Stores change events partitioned by institution ID. Optimized for querying all
    changes that occurred within a specific institution, ordered chronologically.

    Fields:
        - institution_id (uuid, partition key): Unique identifier of the institution
        - changed_at (timeuuid, clustering key): TimeUUID representing when the change occurred
        - person_id (uuid): Unique identifier of the person who made the change
        - change_code (text): Type of change (e.g., PASSWORD_RESET, EMAIL_CHANGE)
        - change_json (text): JSON string containing detailed change information

    Primary key: (institution_id, changed_at)
    Clustering order: changed_at DESC (newest changes first)

audit_by_person :
    Stores all audit events (both READ and CHANGE) partitioned by person ID. Enables
    efficient retrieval of complete audit history for individual users, ordered by
    event time in descending order.

    Fields:
        - person_id (uuid, partition key): Unique identifier of the person
        - event_time (timeuuid, clustering key): TimeUUID representing when the event occurred
        - event_type (text): Type of event - either 'READ' or 'CHANGE'
        - institution_id (uuid): Unique identifier of the associated institution
        - change_code (text): Type of change (null for READ events)
        - change_json (text): JSON string with change details (null for READ events)

    Primary key: (person_id, event_time)
    Clustering order: event_time DESC (newest events first)

changes_by_code :
    Stores change events partitioned by change code type. Allows efficient querying
    of all changes of a specific type (e.g., PASSWORD_RESET, EMAIL_CHANGE) across
    all institutions and persons, ordered chronologically.

    Fields:
        - change_code (text, partition key): Type of change being logged
        - changed_at (timeuuid, clustering key): TimeUUID representing when the change occurred
        - person_id (uuid): Unique identifier of the person who made the change
        - institution_id (uuid): Unique identifier of the associated institution
        - change_json (text): JSON string containing detailed change information

    Primary key: (change_code, changed_at)
    Clustering order: changed_at DESC (newest changes first)

Attributes
----------
SCHEMA : list of str
    A list of CQL statements to create the Cassandra keyspace and associated
    tables for managing audit logs.
"""


SCHEMA = [
    """
    CREATE KEYSPACE IF NOT EXISTS audit_logs 
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs.changes_by_inst
    (
        institution_id uuid,
        changed_at timeuuid,
        person_id uuid,
        change_code text,
        change_json text,
        PRIMARY KEY (institution_id, changed_at)
    ) WITH CLUSTERING ORDER BY (changed_at DESC);
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs.audit_by_person
    (
        person_id uuid,
        event_time timeuuid,
        event_type text,
        institution_id uuid,
        change_code text,
        change_json text,
        PRIMARY KEY (person_id, event_time)
    ) WITH CLUSTERING ORDER BY (event_time DESC);
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs.changes_by_code
    (
        change_code text,
        changed_at timeuuid,
        person_id uuid,
        institution_id uuid,
        change_json text,
        PRIMARY KEY (change_code, changed_at)
    ) WITH CLUSTERING ORDER BY (changed_at DESC);
    """
]
