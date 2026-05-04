import os

import redis

_LOG_PREFIX = "log\x1f"
_STATUS_PREFIX = "status\x1f"
_DONE_PREFIX = "__done__\x1f"
_ERROR_SEPARATOR = "\x1e"


class RedisLogger:
    def __init__(self, job_id: str) -> None:
        self._client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
        self._channel = f"jobs:{job_id}"

    def publish_log(self, line: str) -> None:
        self._client.publish(self._channel, _LOG_PREFIX + line)

    def publish_status(self, status: str, error: str | None = None) -> None:
        payload = status if error is None else f"{status}{_ERROR_SEPARATOR}{error}"
        self._client.publish(self._channel, _STATUS_PREFIX + payload)

    def publish_done(self) -> None:
        self._client.publish(self._channel, _DONE_PREFIX)

    def close(self) -> None:
        self._client.close()
