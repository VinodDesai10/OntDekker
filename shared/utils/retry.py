import time
import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger(__name__)

def retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    tries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    logger_instance: Any = None
):
    log = logger_instance or logger
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                mtries, mdelay = tries, delay
                while mtries > 1:
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        log.warning(f"Operation failed with {e.__class__.__name__}: {e}. Retrying in {mdelay}s... ({mtries-1} attempts left)")
                        await asyncio.sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                mtries, mdelay = tries, delay
                while mtries > 1:
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        log.warning(f"Operation failed with {e.__class__.__name__}: {e}. Retrying in {mdelay}s... ({mtries-1} attempts left)")
                        time.sleep(mdelay)
                        mtries -= 1
                        mdelay *= backoff
                return func(*args, **kwargs)
            return sync_wrapper
    return decorator
