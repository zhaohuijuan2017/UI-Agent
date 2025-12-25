"""IDE 控制主控制器。"""

import time
from typing import Any

from src.automation.executor import AutomationExecutor
from src.automation.actions import Action, ActionType
from src.config.config_manager import ConfigManager
from src.config.schema import ActionConfig as SchemaActionConfig
from src.config.schema import MainConfig, OperationConfig
from src.locator.screenshot import ScreenshotCapture
from src.locator.visual_locator import VisualLocator
from src.models.command import ParsedCommand
from src.models.element import UIElement
from src.models.result import ExecutionResult, ExecutionStatus
from src.parser.command_parser import CommandParser


class IDEController:
    """IDE 控制主控制器。"""

    def __init__(self, config_path: str, api_key: str) -> None:
        """初始化控制器。

        Args:
            config_path: 配置文件路径
            api_key: 智谱 AI API Key
        """
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config: MainConfig = self.config_manager.load_config()

        # 初始化各模块
        self.parser = CommandParser(
            config_manager=self.config_manager,
            api_key=api_key,
            model=self.config.api.model,
        )

        self.screenshot = ScreenshotCapture(self.config.system)
        self.locator = VisualLocator(
            api_key=api_key,
            model=self.config.api.model,
            screenshot_capture=self.screenshot,
        )

        # 设置坐标偏移量（如果有配置）
        if hasattr(self.config.automation, 'coordinate_offset') and self.config.automation.coordinate_offset:
            self.locator.set_coordinate_offset(self.config.automation.coordinate_offset)
            print(f"[初始化] 坐标偏移量: {self.config.automation.coordinate_offset}")

        self.executor = AutomationExecutor(
            default_timeout=self.config.automation.default_timeout,
            max_retries=self.config.automation.max_retries,
            action_delay=self.config.automation.action_delay,
        )

        # 上下文
        self._context: dict[str, Any] = {
            "current_file": None,
            "cursor_position": None,
        }

        # 运行状态
        self._running = True

    def execute_command(self, command: str) -> ExecutionResult:
        """执行自然语言命令。

        Args:
            command: 自然语言命令

        Returns:
            执行结果
        """
        start_time = time.time()

        try:
            # 1. 解析命令
            parsed = self.parser.parse(command, self._context)
            if not parsed.validate():
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message="命令解析失败",
                    error="无法理解该命令",
                )

            # 2. 获取操作配置
            op_config = self.config_manager.get_operation(parsed.action)
            if op_config is None:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message=f"未找到操作: {parsed.action}",
                    error="操作未定义",
                )

            # 3. 检查是否需要确认
            if op_config.requires_confirmation or self._is_dangerous(op_config):
                if not self._request_confirmation(command, op_config):
                    return ExecutionResult(
                        status=ExecutionStatus.CANCELLED,
                        message="操作已取消",
                    )

            # 4. 执行操作
            result = self._execute_operation(op_config, parsed.parameters)

            duration_ms = int((time.time() - start_time) * 1000)
            result.duration_ms = duration_ms

            return result

        except KeyboardInterrupt:
            return ExecutionResult(
                status=ExecutionStatus.CANCELLED,
                message="操作被中断",
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="执行失败",
                error=str(e),
                duration_ms=duration_ms,
            )

    def _execute_operation(
        self,
        op_config: OperationConfig,
        parameters: dict[str, Any],
    ) -> ExecutionResult:
        """执行操作。

        Args:
            op_config: 操作配置
            parameters: 命令参数

        Returns:
            执行结果
        """
        try:
            # 1. 捕获屏幕截图
            screenshot = self.screenshot.capture_fullscreen()

            # 2. 定位 UI 元素
            # 替换提示词中的参数
            prompt = self._format_prompt(op_config.visual_prompt, parameters)

            # 提取目标文件名用于过滤
            target_filter = parameters.get("filename", None)

            elements = self.locator.locate(prompt, screenshot, target_filter=target_filter)

            # 显示定位结果（调试用）
            if elements and target_filter:
                for i, elem in enumerate(elements):
                    center_x, center_y = elem.center
                    print(f"[定位] 元素 {i}: {elem.description}")
                    print(f"       bbox={elem.bbox}, 中心=({center_x}, {center_y}), 置信度={elem.confidence}")
                print(f"[定位] 选择最匹配 '{target_filter}' 的元素")

            if not elements:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message="UI 元素定位失败",
                    error="无法找到目标 UI 元素",
                )

            # 3. 转换操作配置为 Action 对象
            actions = []
            for action_cfg in op_config.actions:
                # 安全地转换操作类型
                try:
                    action_type = ActionType(action_cfg.type)
                except (ValueError, KeyError):
                    # 如果类型不匹配，尝试按字符串匹配
                    action_type_map = {
                        "click": ActionType.CLICK,
                        "double_click": ActionType.DOUBLE_CLICK,
                        "right_click": ActionType.RIGHT_CLICK,
                        "drag": ActionType.DRAG,
                        "type": ActionType.TYPE,
                        "shortcut": ActionType.SHORTCUT,
                        "wait": ActionType.WAIT,
                        "wait_for_dialog": ActionType.WAIT_FOR_DIALOG,
                    }
                    action_type = action_type_map.get(action_cfg.type, ActionType.SHORTCUT)

                actions.append(
                    Action(
                        type=action_type,
                        target=action_cfg.target,
                        parameters=action_cfg.parameters,
                        timeout=action_cfg.timeout,
                        retry=action_cfg.retry,
                    )
                )

            # 替换参数中的占位符
            for action in actions:
                if action.parameters:
                    action.parameters = self._format_parameters(action.parameters, parameters)

            # 4. 执行操作序列
            elements_map = {str(i): elem for i, elem in enumerate(elements)}
            success = self.executor.execute_sequence(actions, elements_map)

            if success:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"操作执行成功: {op_config.description}",
                    data={"operation": op_config.name},
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message="操作执行失败",
                    error="自动化执行过程中出错",
                )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="操作执行失败",
                error=str(e),
            )

    def _format_prompt(self, template: str, parameters: dict[str, Any]) -> str:
        """格式化提示词模板。

        Args:
            template: 提示词模板
            parameters: 参数

        Returns:
            格式化后的提示词
        """
        for key, value in parameters.items():
            template = template.replace(f"{{{key}}}", str(value))
        return template

    def _format_parameters(self, params: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        """格式化操作参数。

        Args:
            params: 参数模板
            values: 参数值

        Returns:
            格式化后的参数
        """
        result = {}
        for key, value in params.items():
            if isinstance(value, str):
                for k, v in values.items():
                    value = value.replace(f"{{{k}}}", str(v))
            result[key] = value
        return result

    def _is_dangerous(self, op_config: OperationConfig) -> bool:
        """检查是否为危险操作。

        Args:
            op_config: 操作配置

        Returns:
            是否危险
        """
        if self.config.safety.dangerous_operations:
            return op_config.name in self.config.safety.dangerous_operations
        return op_config.risk_level in ("high", "critical")

    def _request_confirmation(self, command: str, op_config: OperationConfig) -> bool:
        """请求用户确认。

        Args:
            command: 原始命令
            op_config: 操作配置

        Returns:
            用户是否确认
        """
        if not self.config.safety.require_confirmation:
            return True

        print(f"\n即将执行操作: {op_config.description}")
        print(f"命令: {command}")
        print(f"风险等级: {op_config.risk_level}")

        response = input("确认执行？(y/n): ").strip().lower()
        return response in ("y", "yes", "是")

    def get_context(self) -> dict[str, Any]:
        """获取当前上下文。"""
        return self._context.copy()

    def update_context(self, key: str, value: Any) -> None:
        """更新上下文。

        Args:
            key: 键
            value: 值
        """
        self._context[key] = value

    def stop(self) -> None:
        """停止控制器。"""
        self._running = False

        # 停止配置热更新
        if self.config_manager._enable_hot_reload:
            self.config_manager.stop_hot_reload()

    @property
    def is_running(self) -> bool:
        """是否正在运行。"""
        return self._running
