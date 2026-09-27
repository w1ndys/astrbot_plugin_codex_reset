# 业务层：算下一轮至少要等多久。不能快于来源限制。

from ..entity.constants import MIN_POLL_SECONDS


def next_wait(poll_seconds: int, cache_max_age: int, retry_after: int) -> int:
    """取配置间隔、缓存秒数、429 重试秒数里更大的那个，且不低于 60。"""
    wait = poll_seconds
    # 配置写得再小，也不能快于来源的每分钟 1 次
    if wait < MIN_POLL_SECONDS:
        wait = MIN_POLL_SECONDS
    # Cache-Control 要求的缓存时间更长时，跟着等
    if cache_max_age > wait:
        wait = cache_max_age
    # 429 的 Retry-After 更长时，必须听它
    if retry_after > wait:
        wait = retry_after
    return wait
