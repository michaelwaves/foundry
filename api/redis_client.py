import os

import redis


def make_redis() -> redis.Redis:
    return redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


def channel_for(job_id: str) -> str:
    return f"jobs:{job_id}"


def publish_log(client: redis.Redis, job_id: str, line: str) -> None:
    client.publish(channel_for(job_id), f"log\x1f{line}")


def publish_status(client: redis.Redis, job_id: str, status: str, error: str | None = None) -> None:
    payload = status if error is None else f"{status}\x1e{error}"
    client.publish(channel_for(job_id), f"status\x1f{payload}")


def publish_done(client: redis.Redis, job_id: str) -> None:
    client.publish(channel_for(job_id), "__done__\x1f")
