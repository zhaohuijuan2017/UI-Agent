"""基础设施模块。"""

from .cache import SimpleCache, hash_dict, memoize as cache_memoize
from .logger import Logger
from .utils import (
    format_duration,
    retry,
    safe_cast,
    timeout,
    truncate,
)

# 使用 cache 模块的 memoize 作为默认实现
memoize = cache_memoize

__all__ = [
    "Logger",
    "SimpleCache",
    "hash_dict",
    "memoize",
    "retry",
    "timeout",
    "format_duration",
    "truncate",
    "safe_cast",
]
