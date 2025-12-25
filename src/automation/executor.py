"""GUI 自动化执行器。"""

import time
from typing import Any

import keyboard
import pyautogui

from src.automation.actions import Action, ActionType
from src.models.element import UIElement


class AutomationExecutor:
    """GUI 自动化执行器。"""

    def __init__(
        self,
        default_timeout: float = 5.0,
        max_retries: int = 3,
        action_delay: float = 0.2,
    ) -> None:
        """初始化自动化执行器。

        Args:
            default_timeout: 默认超时时间（秒）
            max_retries: 最大重试次数
            action_delay: 操作间隔延迟（秒）
        """
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.action_delay = action_delay

        # pyautogui 安全设置
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = action_delay

    def execute(
        self,
        action: Action,
        element: UIElement | None = None,
    ) -> bool:
        """执行单个操作。

        Args:
            action: 要执行的操作
            element: 目标 UI 元素（如果需要）

        Returns:
            是否执行成功
        """
        max_attempts = action.retry + 1

        for attempt in range(max_attempts):
            try:
                if action.type == ActionType.CLICK:
                    return self._execute_click(action, element)
                elif action.type == ActionType.DOUBLE_CLICK:
                    return self._execute_double_click(action, element)
                elif action.type == ActionType.RIGHT_CLICK:
                    return self._execute_right_click(action, element)
                elif action.type == ActionType.DRAG:
                    return self._execute_drag(action, element)
                elif action.type == ActionType.TYPE:
                    return self._execute_type(action)
                elif action.type == ActionType.SHORTCUT:
                    return self._execute_shortcut(action)
                elif action.type == ActionType.WAIT:
                    return self._execute_wait(action)
                elif action.type == ActionType.WAIT_FOR_DIALOG:
                    return self._execute_wait_for_dialog(action)
                else:
                    return False
            except pyautogui.FailSafeException:
                # 用户触发了安全中断
                return False
            except Exception:
                if attempt >= max_attempts - 1:
                    return False
                time.sleep(0.5)

        return False

    def execute_sequence(
        self,
        actions: list[Action],
        elements: dict[str, UIElement] | None = None,
    ) -> bool:
        """执行操作序列。

        Args:
            actions: 操作列表
            elements: UI 元素映射

        Returns:
            是否全部执行成功
        """
        elements = elements or {}

        for action in actions:
            element = elements.get(action.target) if action.target else None

            # 操作前短暂延迟，确保界面准备就绪
            time.sleep(0.2)

            if not self.execute(action, element):
                return False

            # 操作后根据 action 的 timeout 延迟
            time.sleep(action.timeout * 0.3)  # 使用 timeout 的一部分作为延迟

        return True

    def _execute_click(self, action: Action, element: UIElement | None) -> bool:
        """执行点击操作。"""
        if element is None:
            return False

        x, y = element.center
        pyautogui.click(x, y)
        return True

    def _execute_double_click(self, action: Action, element: UIElement | None) -> bool:
        """执行双击操作。"""
        if element is None:
            return False

        x, y = element.center
        pyautogui.doubleClick(x, y)
        return True

    def _execute_right_click(self, action: Action, element: UIElement | None) -> bool:
        """执行右键点击操作。"""
        if element is None:
            return False

        x, y = element.center
        pyautogui.rightClick(x, y)
        return True

    def _execute_drag(self, action: Action, element: UIElement | None) -> bool:
        """执行拖拽操作。"""
        params = action.parameters or {}

        start_x = params.get("start_x", 0)
        start_y = params.get("start_y", 0)
        end_x = params.get("end_x", 0)
        end_y = params.get("end_y", 0)
        duration = params.get("duration", 0.5)

        if element:
            start_x, start_y = element.center

        pyautogui.dragTo(end_x, end_y, duration=duration, button="left")
        return True

    def _execute_type(self, action: Action) -> bool:
        """执行文本输入操作。"""
        params = action.parameters or {}
        text = params.get("text", "")
        delay = params.get("delay", 0.1)

        pyautogui.typewrite(text, interval=delay)
        return True

    def _execute_shortcut(self, action: Action) -> bool:
        """执行快捷键操作。"""
        params = action.parameters or {}
        keys = params.get("keys", [])

        if isinstance(keys, str):
            keys = [keys]

        # 优先使用 pyautogui（更可靠），失败则回退到 keyboard
        success = False

        # 方法1: 使用 pyautogui
        try:
            pyautogui.hotkey(*keys, interval=0.05)
            success = True
        except Exception:
            pass

        # 方法2: 回退到 keyboard 库
        if not success:
            try:
                keyboard.press_and_release("+".join(keys))
                success = True
            except Exception:
                pass

        return success

    def _execute_wait(self, action: Action) -> bool:
        """执行等待操作。"""
        params = action.parameters or {}
        duration = params.get("duration", 1.0)

        time.sleep(duration)
        return True

    def _execute_wait_for_dialog(self, action: Action) -> bool:
        """执行等待对话框操作。

        注意：这是简化实现，实际需要检查对话框是否存在
        """
        params = action.parameters or {}
        dialog_title = params.get("dialog_title", "")
        timeout = params.get("timeout", self.default_timeout)

        # 简单等待，实际应该检测对话框
        time.sleep(timeout)
        return True

    def verify_action(
        self,
        action: Action,
        before_screenshot: Any,
        after_screenshot: Any,
    ) -> bool:
        """验证操作结果。

        Args:
            action: 执行的操作
            before_screenshot: 操作前截图
            after_screenshot: 操作后截图

        Returns:
            操作是否生效
        """
        # 简化实现：检查截图是否发生变化
        # 实际应该根据操作类型进行更精确的验证
        return before_screenshot != after_screenshot

    def move_to(self, x: int, y: int, duration: float = 0.5) -> None:
        """移动鼠标到指定位置。

        Args:
            x: X 坐标
            y: Y 坐标
            duration: 移动持续时间
        """
        pyautogui.moveTo(x, y, duration=duration)

    def get_mouse_position(self) -> tuple[int, int]:
        """获取当前鼠标位置。

        Returns:
            (x, y) 坐标
        """
        return pyautogui.position()
