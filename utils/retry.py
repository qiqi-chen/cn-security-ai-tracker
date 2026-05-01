import time
import functools
from dataclasses import dataclass, field
from typing import Tuple, Type


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 30.0
    exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (ConnectionError, TimeoutError, OSError)
    )


def retry_with_backoff(config: RetryConfig = None):
    if config is None:
        config = RetryConfig()

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.exceptions as e:
                    last_exc = e
                    if attempt == config.max_retries:
                        break
                    delay = min(config.base_delay * (2 ** attempt), config.max_delay)
                    time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
