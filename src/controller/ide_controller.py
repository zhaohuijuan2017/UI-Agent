"""IDE 控制主控制器。"""

import re
import time
from typing import Any

from src.automation.actions import Action, ActionType
from src.automation.executor import AutomationExecutor
from src.config.config_manager import ConfigManager
from src.config.schema import MainConfig, OperationConfig
from src.locator.screenshot import ScreenshotCapture
from src.locator.template_matcher import TemplateMatcher
from src.locator.visual_locator import VisualLocator
from src.models.result import ExecutionResult, ExecutionStatus
from src.parser.command_parser import CommandParser
from src.browser.browser_launcher import BrowserLauncher
from src.browser.automation import BrowserAutomation
from src.browser.exceptions import (
    BrowserLaunchError,
    BrowserNotFoundError,
    InvalidURLError,
)
from src.window.exceptions import WindowActivationError, WindowNotFoundError
from src.window.window_manager import WindowManager
from src.workflow.executor import WorkflowExecutor
from src.workflow.parser import WorkflowParser
from src.workflow.validator import WorkflowValidator
from src.workflow.exceptions import WorkflowError


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

        # 获取 base_url（如果配置了）
        base_url = self.config.api.base_url

        # 初始化各模块
        self.parser = CommandParser(
            config_manager=self.config_manager,
            api_key=api_key,
            model=self.config.api.model,
            base_url=base_url,
        )

        self.screenshot = ScreenshotCapture(self.config.system)
        self.locator = VisualLocator(
            api_key=api_key,
            model=self.config.api.model,
            screenshot_capture=self.screenshot,
            vision_enabled=self.config.vision.enabled,
            base_url=base_url,
        )

        # 初始化模板匹配器
        if self.config.template_matching:
            self.template_matcher = TemplateMatcher(
                template_dir=self.config.template_matching.template_dir,
                default_confidence=self.config.template_matching.default_confidence,
                method=self.config.template_matching.method,
                enable_multiscale=self.config.template_matching.enable_multiscale,
                scales=self.config.template_matching.scales,
            )
        else:
            self.template_matcher = None

        # 设置坐标偏移量（如果有配置）
        if (
            hasattr(self.config.automation, "coordinate_offset")
            and self.config.automation.coordinate_offset
        ):
            self.locator.set_coordinate_offset(self.config.automation.coordinate_offset)
            print(f"[初始化] 坐标偏移量: {self.config.automation.coordinate_offset}")

        self.executor = AutomationExecutor(
            default_timeout=self.config.automation.default_timeout,
            max_retries=self.config.automation.max_retries,
            action_delay=self.config.automation.action_delay,
        )

        # 初始化窗口管理器
        self._window_manager = WindowManager()

        # 初始化浏览器启动器
        self._browser_launcher = BrowserLauncher()

        # 初始化浏览器自动化控制器（惰性初始化）
        self._browser_automation: BrowserAutomation | None = None

        # 初始化工作流模块
        self._workflow_parser = WorkflowParser()
        # 获取所有可用操作用于验证
        available_operations = {op.name for op in self.config.ide.operations}
        self._workflow_validator = WorkflowValidator(available_operations)
        self._workflow_executor: WorkflowExecutor | None = None

        # 初始化意图识别和任务编排模块
        self._intent_recognizer = None
        self._task_orchestrator = None
        self._task_executor = None
        self._template_loader = None

        # 尝试初始化意图识别模块
        try:
            from zhipuai import ZhipuAI
            from src.intent.recognizer import IntentRecognizer
            from src.templates.loader import TemplateLoader
            from src.orchestration.executor import TaskExecutor
            from src.orchestration.orchestrator import TaskOrchestrator
            from src.orchestration.adapters import BrowserSystemAdapter, IDESystemAdapter

            # 初始化 LLM 客户端（支持自定义 base_url）
            llm_kwargs = {"api_key": api_key}
            if self.config.api.base_url:
                llm_kwargs["base_url"] = self.config.api.base_url
                print(f"[初始化] 使用自定义 LLM API: {self.config.api.base_url}")
            llm_client = ZhipuAI(**llm_kwargs)

            # 初始化意图识别器
            intent_definitions_path = "config/intent_definitions.yaml"
            self._intent_recognizer = IntentRecognizer(
                intent_definitions_path=intent_definitions_path,
                llm_client=llm_client,
                llm_model=self.config.api.model,
            )

            # 初始化模板加载器
            self._template_loader = TemplateLoader()
            self._template_loader.load_from_directory("workflows/templates")

            # 初始化任务执行器
            self._task_executor = TaskExecutor()

            # 注册系统适配器（IDE 适配器）
            self._task_executor.register_adapter("ide", IDESystemAdapter(self))

            # 注册浏览器适配器（传入 IDE 控制器实例）
            self._task_executor.register_adapter("browser", BrowserSystemAdapter(self))

            # 初始化任务编排器
            self._task_orchestrator = TaskOrchestrator(self._task_executor, self._template_loader)

            print("[初始化] 意图识别和任务编排模块已启用")
        except Exception as e:
            print(f"[初始化] 意图识别模块初始化失败: {e}")
            print("[初始化] 将使用传统命令解析模式")

        # 上下文
        self._context: dict[str, Any] = {
            "current_file": None,
            "cursor_position": None,
        }

        # 运行状态
        self._running = True

    def execute_command(self, command: str, template_name: str | None = None) -> ExecutionResult:
        """执行自然语言命令。

        Args:
            command: 自然语言命令
            template_name: 模板图片文件名（可选）

        Returns:
            执行结果
        """
        start_time = time.time()

        try:
            # 尝试使用意图识别
            if self._intent_recognizer and self._task_orchestrator:
                intent_result = self._intent_recognizer.recognize(command)

                if intent_result.has_match:
                    print(f"[意图识别] 识别到意图: {intent_result.intent.type}")
                    print(f"[意图识别] 置信度: {intent_result.intent.confidence:.2f}")

                    # 如果置信度低于阈值，请求用户确认
                    if intent_result.intent.confidence < 0.85:
                        print(f"[意图识别] 置信度较低，请确认是否继续执行")
                        # TODO: 添加用户确认逻辑

                    # 显示执行计划
                    plan = self._task_orchestrator.show_execution_plan(intent_result.intent)
                    print(f"[执行计划] {plan}")

                    # 执行任务编排
                    context = self._task_orchestrator.orchestrate(intent_result.intent)

                    # 返回执行结果
                    summary = context.get_execution_summary()
                    duration_ms = int((time.time() - start_time) * 1000)

                    if context.status == "completed":
                        return ExecutionResult(
                            status=ExecutionStatus.SUCCESS,
                            message=f"任务执行成功: {intent_result.intent.type}",
                            data=summary,
                            duration_ms=duration_ms,
                        )
                    else:
                        return ExecutionResult(
                            status=ExecutionStatus.FAILED,
                            message=f"任务执行失败: {intent_result.intent.type}",
                            error=summary,
                            duration_ms=duration_ms,
                        )

            # 1. 解析命令（传统模式）
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

            # 4. 检查是否是窗口管理操作（不需要定位元素）
            if op_config.intent == "window_management":
                if op_config.name == "activate_window":
                    # 尝试从命令中提取窗口标题
                    # 如果命令包含 "切换到 XXX" 或 "激活 XXX"，则提取 XXX 作为窗口标题
                    window_title = None  # 默认为 None，表示未提取到

                    # 尝试从命令中提取窗口标题
                    # 命令格式: "切换到微信窗口" -> 提取 "微信"
                    # 命令格式: "激活 WeChat" -> 提取 "WeChat"
                    # 命令格式: "切换到微信" -> 提取 "微信"
                    # 匹配 "切换到xxx窗口" 或 "激活xxx" 或 "切换到xxx"
                    # 注意: 正则表达式顺序很重要，更具体的模式应该放在前面
                    patterns = [
                        r"切换到\s*(.+?)\s*窗口",  # "切换到 xxx 窗口"
                        r"切换到\s*(.+)",  # "切换到xxx" (支持无空格)
                        r"激活\s*(.+?)(?:\s|$)",  # "激活xxx" (支持无空格)
                        r"切换\s*(.+)",  # "切换xxx"
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, command)
                        if match:
                            window_title = match.group(1).strip()
                            break

                    # 如果没有提取到窗口标题，使用默认值
                    if not window_title:
                        window_title = "PyCharm"

                    # 检查是否是已知的应用，优先使用进程名匹配
                    # 先去除窗口标题两端的空格
                    window_title = window_title.strip()

                    # 清理常见的后缀词
                    suffixes_to_remove = ["浏览器", "窗口", "软件", "程序", "应用"]
                    original_title = window_title
                    for suffix in suffixes_to_remove:
                        if window_title.endswith(suffix):
                            window_title = window_title[: -len(suffix)].strip()
                            break

                    # 如果清理后为空，使用原始标题
                    if not window_title:
                        window_title = original_title

                    result = self._activate_by_application_name(window_title)
                    duration_ms = int((time.time() - start_time) * 1000)
                    result.duration_ms = duration_ms
                    return result

            # 4.5 检查是否是浏览器启动操作
            if op_config.intent == "browser_launch":
                if op_config.name == "open_browser":
                    # 尝试从命令中提取 URL 和浏览器类型
                    # 命令格式: "打开浏览器访问 https://www.example.com"
                    # 命令格式: "在 Chrome 中打开 https://www.example.com"
                    # 命令格式: "访问 https://www.example.com"
                    url = None
                    browser = None  # 默认浏览器

                    # 首先尝试从命令中提取 URL
                    # URL 模式: http:// 或 https:// 开头，或者域名格式
                    url_pattern = r"(https?://[^\s]+|[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+)"
                    url_match = re.search(url_pattern, command)
                    if url_match:
                        url = url_match.group(1)

                    # 提取浏览器类型
                    # 命令格式: "在 Chrome 中打开" -> browser = "Chrome"
                    # 命令格式: "使用 Edge 访问" -> browser = "Edge"
                    browser_patterns = [
                        r"在\s*(Chrome|Edge|Firefox|Safari|Opera)\s*中",  # "在 Chrome 中"
                        r"使用\s*(Chrome|Edge|Firefox|Safari|Opera)\s*",  # "使用 Chrome"
                        r"用\s*(Chrome|Edge|Firefox|Safari|Opera)\s*",  # "用 Chrome"
                    ]
                    for pattern in browser_patterns:
                        match = re.search(pattern, command, re.IGNORECASE)
                        if match:
                            browser = match.group(1)
                            break

                    # 如果没有找到 URL，返回错误
                    if not url:
                        return ExecutionResult(
                            status=ExecutionStatus.FAILED,
                            message="未找到有效的 URL",
                            error="请提供要访问的网址，例如: https://www.example.com",
                        )

                    result = self.open_browser(url, browser)
                    duration_ms = int((time.time() - start_time) * 1000)
                    result.duration_ms = duration_ms
                    return result

            # 4.6 检查是否是浏览器自动化操作
            if op_config.intent == "browser_automation":
                result = self._execute_browser_automation(op_config, parsed.parameters)
                duration_ms = int((time.time() - start_time) * 1000)
                result.duration_ms = duration_ms
                return result

            # 5. 执行操作
            result = self._execute_operation(
                op_config, parsed.parameters, template_name=template_name
            )

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
        template_name: str | None = None,
    ) -> ExecutionResult:
        """执行操作。

        Args:
            op_config: 操作配置
            parameters: 命令参数
            template_name: 命令行指定的模板名称（优先级高于配置）

        Returns:
            执行结果
        """
        try:
            # 1. 捕获屏幕截图
            screenshot = self.screenshot.capture_fullscreen()

            # 2. 定位 UI 元素
            elements = []

            # 优先级 1: 模板匹配（如果配置了 template 或命令行指定了模板）
            template_to_use = template_name or op_config.template
            if template_to_use and self.template_matcher:
                print(f"[定位] 使用模板匹配: {template_to_use}")
                # 使用操作配置中的置信度，或使用默认值
                threshold = op_config.confidence or self.template_matcher.default_confidence
                elements = self.template_matcher.match(
                    screenshot,
                    template_to_use,
                    threshold=threshold,
                )
                if elements:
                    print(f"[定位] 模板匹配成功，找到 {len(elements)} 个结果")
                    for i, elem in enumerate(elements):
                        center_x, center_y = elem.center
                        print(f"       元素 {i}: {elem.description}")
                        print(
                            f"       bbox={elem.bbox}, 中心=({center_x}, {center_y}), 置信度={elem.confidence}"
                        )
                else:
                    print("[定位] 模板匹配未找到结果")

            # 优先级 2: 视觉识别/OCR（如果没有配置模板或模板匹配失败）
            if not elements:
                # 替换提示词中的参数
                prompt = self._format_prompt(op_config.visual_prompt, parameters)

                # 提取目标过滤参数（根据操作类型选择合适的参数）
                # - file_operation: 使用 filename
                # - input: 使用 context_text（用于定位参考元素）
                # - 其他: 使用 filename 或 context_text
                if op_config.intent == "input":
                    target_filter = parameters.get("context_text", None)
                else:
                    target_filter = parameters.get("filename", None)

                elements = self.locator.locate(prompt, screenshot, target_filter=target_filter)

                # 显示定位结果（调试用）
                if elements and target_filter:
                    for i, elem in enumerate(elements):
                        center_x, center_y = elem.center
                        print(f"[定位] 元素 {i}: {elem.description}")
                        print(
                            f"       bbox={elem.bbox}, 中心=({center_x}, {center_y}), 置信度={elem.confidence}"
                        )
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
                # 检查条件执行：如果操作标记为 conditional 且相关参数不存在，则跳过
                if action_cfg.parameters and action_cfg.parameters.get("conditional"):
                    # 检查是否满足条件（例如 submit_action 存在）
                    conditional_param = action_cfg.parameters.get(
                        "conditional_param", "submit_action"
                    )
                    if conditional_param not in parameters or not parameters[conditional_param]:
                        continue  # 跳过此操作

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

    def activate_window(self, title: str) -> ExecutionResult:
        """激活指定窗口。

        Args:
            title: 窗口标题

        Returns:
            执行结果
        """
        try:
            success = self._window_manager.activate_window(title)
            if success:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"窗口已激活: {title}",
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message=f"窗口激活失败: {title}",
                )
        except WindowNotFoundError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="窗口未找到",
                error=str(e),
            )
        except WindowActivationError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="窗口激活失败",
                error=str(e),
            )

    def activate_pycharm(self) -> ExecutionResult:
        """激活 PyCharm 窗口。"""
        # PyCharm 的进程名通常是 pycharm64.exe
        # 这是最可靠的方式来识别 PyCharm
        try:
            success = self._window_manager.activate_by_process("pycharm64.exe")
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                message="已激活 PyCharm 窗口",
            )
        except WindowNotFoundError:
            # 如果按进程名找不到，回退到窗口标题匹配
            return self._activate_by_fallback_patterns()
        except WindowActivationError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="窗口激活失败",
                error=str(e),
            )

    def _activate_by_fallback_patterns(self) -> ExecutionResult:
        """使用窗口标题模式作为回退方案。

        Returns:
            执行结果
        """
        try:
            # 获取所有窗口
            all_windows = self._window_manager.list_windows()

            # 策略 1: 查找包含 .py 的窗口（PyCharm 编辑器窗口）
            for title in all_windows:
                if ".py" in title and "–" in title:
                    window = self._window_manager.find_window(title)
                    if window:
                        return self._activate_window_object(window)

            # 策略 2: 查找包含 JetBrains 的窗口
            for title in all_windows:
                if "JetBrains" in title:
                    window = self._window_manager.find_window(title)
                    if window:
                        return self._activate_window_object(window)

            # 策略 3: 查找包含 PyCharm 的窗口
            for title in all_windows:
                if "PyCharm" in title:
                    window = self._window_manager.find_window(title)
                    if window:
                        return self._activate_window_object(window)

            # 如果都没找到，返回错误
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="未找到 PyCharm 窗口",
                error="请确保 PyCharm 正在运行并有打开的项目",
            )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="查找窗口失败",
                error=str(e),
            )

    def open_browser(self, url: str, browser: str | None = None) -> ExecutionResult:
        """打开浏览器并访问指定网址。

        Args:
            url: 目标网址
            browser: 浏览器名称（可选），如 "chrome"、"edge"、"firefox" 等
                    如果为 None，使用默认浏览器

        Returns:
            执行结果
        """
        try:
            if browser:
                success = self._browser_launcher.open_browser(url, browser)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"已使用 {browser} 浏览器打开: {url}",
                )
            else:
                success = self._browser_launcher.open_default_browser(url)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"已使用默认浏览器打开: {url}",
                )
        except InvalidURLError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="URL 格式无效",
                error=str(e),
            )
        except BrowserNotFoundError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="浏览器未找到",
                error=str(e),
            )
        except BrowserLaunchError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="浏览器启动失败",
                error=str(e),
            )

    def activate_by_process(self, process_name: str) -> ExecutionResult:
        """通过进程名激活窗口。

        Args:
            process_name: 进程名称（如 "WeChatApp.exe", "pycharm64.exe"）

        Returns:
            执行结果
        """
        try:
            success = self._window_manager.activate_by_process(process_name)
            if success:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"已激活进程窗口: {process_name}",
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message=f"无法激活进程窗口: {process_name}",
                    error="进程可能不存在或窗口不可见",
                )
        except WindowNotFoundError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="进程窗口未找到",
                error=str(e),
            )
        except WindowActivationError as e:
            error_msg = str(e)
            # 检查是否是权限问题（Windows Error Code 5）
            if "Error code from Windows: 5" in error_msg or "拒绝访问" in error_msg:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message="权限不足，无法激活窗口",
                    error=f"目标应用可能以管理员权限运行。请以管理员身份运行此脚本，或关闭目标应用后以普通用户身份重新打开。",
                )
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="窗口激活失败",
                error=str(e),
            )

    def _activate_window_object(self, window) -> ExecutionResult:
        """激活窗口对象。

        Args:
            window: pygetwindow 窗口对象

        Returns:
            执行结果
        """
        try:
            if window.isMinimized:
                window.restore()
            window.activate()

            # 尝试使用 Win32 API 强制激活
            try:
                import win32gui

                hwnd = win32gui.FindWindow(None, window.title)
                if hwnd:
                    win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                message=f"窗口已激活: {window.title}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="窗口激活失败",
                error=str(e),
            )

    def _activate_by_application_name(self, app_name: str) -> ExecutionResult:
        """根据应用名称智能选择激活方式。

        Args:
            app_name: 应用名称（如 "PyCharm", "微信", "Chrome"）

        Returns:
            执行结果
        """
        # 应用名称到进程名的映射
        app_process_map = {
            "PyCharm": "pycharm64.exe",
            "pycharm": "pycharm64.exe",
            "IDEA": "idea64.exe",
            "WebStorm": "webstorm64.exe",
            "微信": "WeChatApp.exe",
            "WeChat": "WeChatApp.exe",
            "wechat": "WeChatApp.exe",
            "Chrome": "chrome.exe",
            "chrome": "chrome.exe",
            "谷歌": "chrome.exe",
            "谷歌浏览器": "chrome.exe",
            "浏览器": "chrome.exe",
            "Edge": "msedge.exe",
            "edge": "msedge.exe",
            "微软": "msedge.exe",
            "Firefox": "firefox.exe",
            "firefox": "firefox.exe",
            "火狐": "firefox.exe",
            "火狐浏览器": "firefox.exe",
            "VSCode": "Code.exe",
            "vscode": "Code.exe",
            "Code": "Code.exe",
            "代码": "Code.exe",
        }

        # 检查是否有映射的进程名
        process_name = app_process_map.get(app_name)
        if process_name:
            print(f"[调试] 使用进程名激活: {app_name} -> {process_name}")
            try:
                return self.activate_by_process(process_name)
            except Exception as e:
                print(f"[调试] 进程名激活失败，回退到窗口标题: {e}")

        # 回退到窗口标题匹配
        print(f"[调试] 使用窗口标题激活: {app_name}")
        try:
            return self.activate_window(app_name)
        except Exception as e:
            # 返回友好的错误信息
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message=f"未找到 '{app_name}' 窗口",
                error="请确保应用正在运行",
            )

    def _execute_browser_automation(
        self,
        op_config: OperationConfig,
        parameters: dict[str, Any],
    ) -> ExecutionResult:
        """执行浏览器自动化操作（基于 OCR + 视觉定位）。

        Args:
            op_config: 操作配置
            parameters: 命令参数

        Returns:
            执行结果
        """
        # 惰性初始化浏览器自动化控制器
        if self._browser_automation is None:
            self._browser_automation = BrowserAutomation(
                api_key=self.config.api.zhipuai_api_key if self.config else None,
                model=self.config.api.model if self.config else "glm-4-flash",
                config=self.config.system if self.config else None,
            )

        try:
            # 根据操作名称执行相应的浏览器操作
            if op_config.name == "browser_click":
                # 获取元素文本描述
                text = parameters.get("locator", parameters.get("filename", ""))

                if not text:
                    return ExecutionResult(
                        status=ExecutionStatus.FAILED,
                        message="缺少元素描述",
                        error="请提供要点击的元素文本，例如：网页点击 百度一下按钮",
                    )

                print(f"[浏览器自动化] 正在查找元素: {text}")
                self._browser_automation.click(text)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"已点击元素: {text}",
                )

            elif op_config.name == "browser_scroll":
                # 从参数中获取滚动方向
                direction = parameters.get("direction", "down")
                print(f"[浏览器自动化] 向{direction}滚动页面")
                self._browser_automation.scroll(direction)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"已{direction}滚动页面",
                )

            elif op_config.name == "browser_type":
                # 获取输入框描述和输入文本
                text = parameters.get("locator", parameters.get("filename", ""))
                input_text = parameters.get("input_text", "")
                clear = parameters.get("clear", False)

                if not text:
                    return ExecutionResult(
                        status=ExecutionStatus.FAILED,
                        message="缺少输入框描述",
                        error="请提供输入框的描述，例如：网页输入 搜索框 Python",
                    )
                if not input_text:
                    return ExecutionResult(
                        status=ExecutionStatus.FAILED,
                        message="缺少输入文本",
                        error="请提供要输入的文本内容",
                    )

                print(f"[浏览器自动化] 在 '{text}' 中输入: {input_text}")
                self._browser_automation.type_text(text, input_text, clear=clear)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"已在 {text} 输入: {input_text}",
                )

            elif op_config.name == "browser_wait":
                text = parameters.get("locator", parameters.get("filename", ""))

                if not text:
                    return ExecutionResult(
                        status=ExecutionStatus.FAILED,
                        message="缺少元素描述",
                        error="请提供要等待的元素描述",
                    )

                print(f"[浏览器自动化] 等待元素出现: {text}")
                self._browser_automation.wait_for_element(text)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"已等待元素: {text}",
                )

            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message=f"未知的浏览器自动化操作: {op_config.name}",
                )

        except Exception as e:
            import traceback
            error_msg = str(e)
            traceback.print_exc()

            # 检查是否是元素未找到错误
            if "not found" in error_msg.lower() or "未找到" in error_msg:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message="浏览器元素未找到",
                    error=f"无法在屏幕上找到指定的元素。请确保：\n"
                           f"1. 浏览器已打开正确的页面\n"
                           f"2. 页面已完全加载\n"
                           f"3. 元素文本正确且在屏幕可见范围内\n\n"
                           f"详细错误: {error_msg}",
                )

            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="浏览器自动化操作失败",
                error=f"{error_msg}\n\n请确保浏览器已打开正确的页面。",
            )

    def execute_workflow_file(
        self, path: str, dry_run: bool = False
    ) -> ExecutionResult:
        """执行工作流文件。

        Args:
            path: 工作流文件路径
            dry_run: 是否仅验证不执行

        Returns:
            执行结果
        """
        try:
            start_time = time.time()

            # 解析工作流文件
            config = self._workflow_parser.parse_file(path)

            # 验证工作流配置
            errors = self._workflow_validator.validate(config)
            if errors:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message="工作流验证失败",
                    error="\n".join(errors),
                )

            # 初始化工作流执行器（惰性初始化）
            if self._workflow_executor is None:
                self._workflow_executor = WorkflowExecutor(self)

            # 执行工作流
            result = self._workflow_executor.execute(config, dry_run=dry_run)

            duration_ms = int((time.time() - start_time) * 1000)

            if result.success:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    message=f"工作流执行成功: {config.name}",
                    data={
                        "workflow_name": result.workflow_name,
                        "completed_steps": result.completed_steps,
                        "total_steps": result.total_steps,
                        "duration": result.duration,
                    },
                    duration_ms=duration_ms,
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message=f"工作流执行失败: {result.error_message}",
                    error=result.error_message,
                    data={
                        "workflow_name": result.workflow_name,
                        "failed_step": result.failed_step,
                        "completed_steps": result.completed_steps,
                    },
                    duration_ms=duration_ms,
                )

        except WorkflowError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="工作流执行失败",
                error=str(e),
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="工作流执行异常",
                error=str(e),
            )

    def validate_workflow_file(self, path: str) -> ExecutionResult:
        """验证工作流文件。

        Args:
            path: 工作流文件路径

        Returns:
            验证结果
        """
        try:
            # 解析工作流文件
            config = self._workflow_parser.parse_file(path)

            # 验证工作流配置
            errors = self._workflow_validator.validate(config)
            if errors:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message="工作流验证失败",
                    error="\n".join(errors),
                )

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                message=f"工作流验证通过: {config.name}",
                data={
                    "workflow_name": config.name,
                    "step_count": len(config.steps),
                },
            )

        except WorkflowError as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message="工作流验证失败",
                error=str(e),
            )
