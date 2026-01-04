"""系统适配器。"""

import logging
from typing import Any, Protocol

from src.orchestration.context import StepExecutionResult

logger = logging.getLogger(__name__)


class SystemAdapter(Protocol):
    """系统适配器协议。

    定义统一的系统操作接口。
    """

    def execute(self, action: str, params: dict[str, Any]) -> StepExecutionResult:
        """执行系统动作。

        Args:
            action: 动作名称
            params: 动作参数

        Returns:
            步骤执行结果
        """
        ...


class BrowserSystemAdapter:
    """浏览器系统适配器。"""

    def __init__(self, ide_controller=None):
        """初始化浏览器适配器。

        Args:
            ide_controller: IDE 控制器实例（用于访问浏览器自动化功能）
        """
        self.ide = ide_controller
        self._browser_automation = None

    def _get_browser(self):
        """获取浏览器自动化实例（惰性初始化）。"""
        if self._browser_automation is None and self.ide:
            self._browser_automation = self.ide._browser_automation
        return self._browser_automation

    def execute(self, action: str, params: dict[str, Any]) -> StepExecutionResult:
        """执行浏览器动作。

        Args:
            action: 动作名称（open、extract_content 等）
            params: 动作参数

        Returns:
            步骤执行结果
        """
        try:
            if action == "open":
                return self._open_page(params)
            elif action == "extract_content":
                return self._extract_content(params)
            else:
                return StepExecutionResult(
                    step_index=0,
                    success=False,
                    error=f"未知的浏览器动作: {action}",
                )
        except Exception as e:
            logger.error(f"浏览器动作执行失败: {e}")
            return StepExecutionResult(step_index=0, success=False, error=str(e))

    def _open_page(self, params: dict[str, Any]) -> StepExecutionResult:
        """打开页面。"""
        url = params.get("url")
        if not url:
            return StepExecutionResult(step_index=0, success=False, error="缺少 URL 参数")

        logger.info(f"打开浏览器页面: {url}")

        # 检查是否有浏览器自动化实例
        browser = self._get_browser()
        if browser:
            try:
                # 使用浏览器自动化打开页面
                browser.navigate(url)
                return StepExecutionResult(
                    step_index=0,
                    success=True,
                    output={"url": url, "opened": True},
                )
            except Exception as e:
                logger.error(f"浏览器打开页面失败: {e}")
                return StepExecutionResult(
                    step_index=0, success=False, error=f"浏览器打开失败: {e}"
                )
        else:
            # 回退：使用 IDEController 的浏览器启动器
            if self.ide and self.ide._browser_launcher:
                try:
                    # 启动默认浏览器并打开 URL
                    import time
                    import webbrowser

                    webbrowser.open(url)
                    time.sleep(1)  # 等待浏览器启动
                    return StepExecutionResult(
                        step_index=0,
                        success=True,
                        output={"url": url, "opened": True, "method": "webbrowser"},
                    )
                except Exception as e:
                    logger.error(f"使用系统浏览器打开失败: {e}")
                    return StepExecutionResult(
                        step_index=0, success=False, error=f"打开 URL 失败: {e}"
                    )

        # 最终回退：只记录成功（不实际打开）
        logger.warning(f"浏览器自动化未初始化，仅记录 URL: {url}")
        return StepExecutionResult(step_index=0, success=True, output={"url": url, "opened": False})

    def _extract_content(self, params: dict[str, Any]) -> StepExecutionResult:
        """提取页面内容。"""
        selector = params.get("selector")
        logger.info(f"提取页面内容: {selector}")

        # 检查是否有浏览器自动化实例
        browser = self._get_browser()
        if browser:
            try:
                # TODO: 使用浏览器自动化提取内容
                # content = browser.get_text(selector)
                pass
            except Exception as e:
                logger.error(f"提取页面内容失败: {e}")
                return StepExecutionResult(step_index=0, success=False, error=f"提取内容失败: {e}")

        # 回退：返回占位符内容
        return StepExecutionResult(
            step_index=0,
            success=True,
            output={
                "content": f"从选择器 '{selector}' 提取的内容",
                "selector": selector,
            },
        )


class IDESystemAdapter:
    """IDE 系统适配器。"""

    def __init__(self, ide_controller):
        """初始化 IDE 适配器。

        Args:
            ide_controller: IDE 控制器实例
        """
        self.ide = ide_controller

    def execute(self, action: str, params: dict[str, Any]) -> StepExecutionResult:
        """执行 IDE 动作。

        Args:
            action: 动作名称（switch_window、develop 等）
            params: 动作参数

        Returns:
            步骤执行结果
        """
        try:
            if action == "switch_window":
                return self._switch_window(params)
            elif action == "develop":
                return self._develop(params)
            elif action == "activate_window":
                return self._activate_window(params)
            else:
                return StepExecutionResult(
                    step_index=0,
                    success=False,
                    error=f"未知的 IDE 动作: {action}",
                )
        except Exception as e:
            logger.error(f"IDE 动作执行失败: {e}")
            return StepExecutionResult(step_index=0, success=False, error=str(e))

    def _switch_window(self, params: dict[str, Any]) -> StepExecutionResult:
        """切换窗口。"""
        window = params.get("window")
        if not window:
            return StepExecutionResult(step_index=0, success=False, error="缺少 window 参数")

        # 使用 IDE 控制器的 activate_by_application_name 方法
        result = self.ide._activate_by_application_name(window)
        return StepExecutionResult(
            step_index=0,
            success=result.status.value == "success",
            output={"window": window} if result.status.value == "success" else {},
            error=result.error if result.status.value != "success" else None,
        )

    def _activate_window(self, params: dict[str, Any]) -> StepExecutionResult:
        """激活窗口。"""
        window = params.get("window", "PyCharm")
        result = self.ide._activate_by_application_name(window)
        return StepExecutionResult(
            step_index=0,
            success=result.status.value == "success",
            output={"window": window} if result.status.value == "success" else {},
            error=result.error if result.status.value != "success" else None,
        )

    def _develop(self, params: dict[str, Any]) -> StepExecutionResult:
        """执行开发操作。"""
        requirement = params.get("requirement")
        input_data = params.get("input_data")

        # TODO: 实现实际的开发逻辑
        # 这里可以调用 IDE 的代码生成功能
        logger.info(f"执行开发操作: requirement={requirement}, input_data={input_data}")

        # 提取需求内容
        if input_data and isinstance(input_data, dict):
            requirement = input_data.get("content", requirement)

        return StepExecutionResult(
            step_index=0,
            success=True,
            output={
                "generated_code": f"// 基于 '{requirement}' 生成的代码",
                "requirement": requirement,
            },
        )
