import asyncio
import hashlib
import json
import time
from functools import wraps


def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def hash_id(input_string: str) -> str:
    hash_object = hashlib.sha256(input_string.encode("utf-8"))
    return hash_object.hexdigest()


def retry(attempts: int = 5, delay: float = 1, backoff: bool = True):
    def decorator(func):
        is_async = asyncio.iscoroutinefunction(func)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            for i in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == attempts:
                        raise e
                    wait = delay * (2 * i) if backoff else delay
                    time.sleep(wait)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            for i in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if i == attempts:
                        raise e
                    # Apply longer delay for rate limiting errors (429)
                    error_msg = str(e)
                    if "RATE_LIMIT_429" in error_msg or "429" in error_msg:
                        wait = delay * (4 * i)  # More aggressive backoff for 429
                    else:
                        wait = delay * (2 * i) if backoff else delay
                    await asyncio.sleep(wait)

        return async_wrapper if is_async else sync_wrapper

    return decorator
