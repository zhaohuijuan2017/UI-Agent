"""工具函数。"""

import time
from functools import wraps
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """重试装饰器。

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍增因子
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception  # type: ignore

        return wrapper

    return decorator


def timeout(seconds: float) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """超时装饰器。

    Args:
        seconds: 超时时间（秒）

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import signal

            def timeout_handler(_signum: int, _frame: Any) -> None:
                raise TimeoutError(f"函数 {func.__name__} 执行超时")

            # 设置超时信号
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(seconds))

            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

            return result

        return wrapper

    return decorator


def format_duration(milliseconds: int) -> str:
    """格式化持续时间。

    Args:
        milliseconds: 毫秒数

    Returns:
        格式化后的字符串
    """
    if milliseconds < 1000:
        return f"{milliseconds}ms"
    elif milliseconds < 60000:
        seconds = milliseconds / 1000
        return f"{seconds:.1f}s"
    else:
        minutes = milliseconds / 60000
        seconds = (milliseconds % 60000) / 1000
        return f"{int(minutes)}m {seconds:.0f}s"


def truncate(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """截断文本。

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def safe_cast(value: Any, target_type: type[T], default: T | None = None) -> T | None:
    """安全类型转换。

    Args:
        value: 原始值
        target_type: 目标类型
        default: 默认值

    Returns:
        转换后的值，失败则返回默认值
    """
    try:
        return target_type(value)
    except (ValueError, TypeError):
        return default
