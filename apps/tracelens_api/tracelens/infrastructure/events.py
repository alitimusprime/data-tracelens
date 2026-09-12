import json
import logging
from collections.abc import AsyncIterator

import redis
import redis.asyncio as async_redis

logger = logging.getLogger(__name__)
CHANNEL = "tracelens:events"


class EventPublisher:
    def __init__(self, redis_url: str) -> None:
        self.client = redis.from_url(redis_url, decode_responses=True)

    def publish(self, event_type: str, payload: dict) -> None:
        message = json.dumps({"type": event_type, "payload": payload}, default=str)
        try:
            self.client.publish(CHANNEL, message)
        except redis.RedisError:
            logger.warning("Live event could not be published", exc_info=True)


async def subscribe(redis_url: str) -> AsyncIterator[str]:
    client = async_redis.from_url(redis_url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield message["data"]
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.close()
        await client.close()
