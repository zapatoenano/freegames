import time
from typing import Callable, Any


def ttl_cache(ttl_seconds: int):
    """Simple decorator to cache a no-arg function result for `ttl_seconds` seconds."""
    def decorator(func: Callable[[], Any]):
        cache = {"value": None, "time": 0}

        def wrapper(*args, **kwargs):
            now = time.time()
            if cache["value"] is not None and (now - cache["time"] < ttl_seconds):
                return cache["value"]
            val = func(*args, **kwargs)
            cache["value"] = val
            cache["time"] = now
            return val

        return wrapper

    return decorator
