import asyncio
import time
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster, Session, ResponseFuture, ResultSet
from cassandra.policies import DCAwareRoundRobinPolicy
from cassandra.io.asyncioreactor import AsyncioConnection
from typing import Optional

from app.logger import logger
from app.services.schema import SCHEMA


class CassandraClient:
    """
    Implements a client for interacting with a Cassandra cluster.

    This class provides functionality to establish connections to a
    Cassandra cluster, execute asynchronous queries, and manage the
    connection lifecycle. It includes retry logic for establishing
    connections and utilities for initializing the schema upon a
    successful connection.

    :ivar cluster: Represents the Cassandra cluster connection.
    :type cluster: Cluster
    :ivar session: Represents the session used for executing queries.
    :type session: Session
    """
    def __init__(self) -> None:
        self.cluster: Optional[Cluster] = None
        self.session: Optional[Session] = None

    async def execute_async(self, query: str, parameters: tuple = ()) -> ResultSet:
        """
        Executes a CQL query asynchronously and returns the result.

        This method utilizes `asyncio` to execute the query in a non-blocking
        manner while integrating with Cassandra's asynchronous query execution.

        :param query: A CQL query string to be executed.
        :param parameters: A tuple containing parameters to be used in the query. Defaults to an empty tuple.
        :return: Result of the executed query.
        :rtype: Any
        """
        loop = asyncio.get_event_loop()
        future: ResponseFuture = self.session.execute_async(query, parameters)

        # Convert Cassandra Future to asyncio Future
        result = await loop.run_in_executor(None, future.result)
        return result

    def connect(self, hosts: list[str], retry_count: int = 5, retry_delay: int = 10) -> None:
        """
        Establishes a connection to a Cassandra cluster with retry logic, sets the session's default
        consistency level, initializes the cluster schema, and switches to the specified keyspace.

        This method uses a load balancing policy based on the specified local data center and
        attempts to connect with a set retry limit. If the connection fails after all retries,
        an exception is raised.

        :param hosts: A list of Cassandra cluster host addresses to connect to.
        :param retry_count: The number of times to retry connecting in case of failure. Defaults to 5.
        :param retry_delay: The delay in seconds between retries. Defaults to 10.
        :return: None
        """
        # DCAwareRoundRobinPolicy: routes queries to nodes in the local datacenter ('datacenter1')
        # Falls back to other datacenters only if local nodes are unavailable
        # Uses round-robin distribution among available nodes for load balancing
        load_balancing_policy = DCAwareRoundRobinPolicy(local_dc='datacenter1')
        
        for attempt in range(retry_count):
            try:
                logger.info(f"Attempting to connect to Cassandra cluster (attempt {attempt + 1}/{retry_count}): {hosts}")
                
                self.cluster = Cluster(
                    hosts,
                    load_balancing_policy=load_balancing_policy,
                    protocol_version=4,
                    connect_timeout=20,
                    connection_class=AsyncioConnection,
                )
                self.session = self.cluster.connect()
                
                # For a 3-node cluster, use QUORUM consistency level
                # QUORUM requires a majority of replica nodes to respond (2 out of 3 nodes)
                # This ensures strong consistency and fault tolerance - reads/writes succeed even if 1 node is down
                self.session.default_consistency_level = ConsistencyLevel.QUORUM

                # SCHEMA initialization
                logger.info("Creating keyspace and tables...")
                for statement in SCHEMA:
                    self.session.execute(statement.strip())

                self.session.set_keyspace('audit_logs')
                
                logger.info(f"Successfully connected to Cassandra cluster: {hosts}")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to Cassandra (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to Cassandra after all retries")
                    raise

    def close(self) -> None:
        """
        Closes the Cassandra database connection.

        This method ensures that the connection to the Cassandra cluster is
        closed, releasing any resources used by the connection. It logs an
        informational message prior to the shutdown process.

        :return: None
        """
        if self.cluster:
            logger.info("Closing Cassandra connection")
            self.cluster.shutdown()


# Global CassandraClient instance - provides singleton access to Cassandra cluster operations
# This instance is used throughout the application for all database interactions
db = CassandraClient()
