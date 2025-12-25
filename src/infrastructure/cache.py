"""缓存系统。"""

import hashlib
import json
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class SimpleCache:
    """简单缓存实现。"""

    def __init__(self, max_size: int = 100, ttl: float = 300.0) -> None:
        """初始化缓存。

        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间（秒）
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl

    def get(self, key: str) -> Any | None:
        """获取缓存值。

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]

        # 检查是否过期
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存值。

        Args:
            key: 缓存键
            value: 缓存值
        """
        # 如果缓存已满，删除最旧的条目
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """清空缓存。"""
        self._cache.clear()

    def remove(self, key: str) -> bool:
        """移除缓存条目。

        Args:
            key: 缓存键

        Returns:
            是否成功移除
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False


def memoize(cache: SimpleCache | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """函数结果缓存装饰器。

    Args:
        cache: 缓存实例，如果不提供则创建新的

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """装饰器。"""
        _cache = cache or SimpleCache()

        def wrapper(*args: Any, **kwargs: Any) -> T:
            """包装函数。"""
            # 生成缓存键
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()

            # 尝试从缓存获取
            result = _cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            _cache.set(cache_key, result)
            return result

        return wrapper

    return decorator


def hash_dict(data: dict[str, Any]) -> str:
    """计算字典的哈希值。

    Args:
        data: 字典数据

    Returns:
        哈希字符串
    """
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
