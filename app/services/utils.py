import asyncio
from cassandra.cluster import ResponseFuture
from typing import Any


def cassandra_future_to_asyncio(
    cassandra_future: ResponseFuture
) -> asyncio.Future[Any]:
    """
    Converts a Cassandra future object into a Python asyncio future object.

    This function provides a way to integrate Cassandra asynchronous operations
    with Python's asyncio event loop by translating a Cassandra future into an
    Asyncio-compatible future. The function listens for both success and error
    callbacks from the Cassandra future and resolves the asyncio future accordingly.

    :param cassandra_future: A future object provided by the Cassandra driver.
    :type cassandra_future: cassandra.concurrent.Future
    :return: An asyncio future that resolves or rejects based on the Cassandra future's result or error.
    :rtype: asyncio.Future
    """
    loop = asyncio.get_event_loop()
    asyncio_future = loop.create_future()

    def on_result(result: Any) -> None:
        loop.call_soon_threadsafe(asyncio_future.set_result, result)

    def on_error(exception: Exception) -> None:
        loop.call_soon_threadsafe(asyncio_future.set_exception, exception)

    cassandra_future.add_callback(on_result)
    cassandra_future.add_errback(on_error)

    return asyncio_future
