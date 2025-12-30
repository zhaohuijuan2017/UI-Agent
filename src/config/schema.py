"""配置数据模型和验证。"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ActionConfig:
    """单个操作配置。

    Attributes:
        type: 操作类型（click, drag, type, shortcut 等）
        target: 目标元素名称
        parameters: 操作参数
        timeout: 超时时间（秒）
        retry: 重试次数
    """

    type: str
    target: str | None = None
    parameters: dict[str, Any] | None = None
    timeout: float = 5.0
    retry: int = 3


@dataclass
class PostCheckConfig:
    """后置检查配置。"""

    type: str
    parameters: dict[str, Any] | None = None


@dataclass
class OperationConfig:
    """IDE 操作配置。

    Attributes:
        name: 操作名称
        aliases: 别名列表
        intent: 所属意图
        description: 操作描述
        visual_prompt: 视觉定位提示词
        actions: 操作序列
        preconditions: 前置条件
        post_check: 后置检查
        requires_confirmation: 是否需要确认
        risk_level: 风险等级
        template: 模板图片文件名（用于 template_match 意图）
        confidence: 模板匹配置信度阈值
    """

    name: str
    aliases: list[str]
    intent: str
    description: str
    visual_prompt: str = ""
    actions: list[ActionConfig] | None = None
    preconditions: list[str] | None = None
    post_check: PostCheckConfig | None = None
    requires_confirmation: bool = False
    risk_level: str = "low"
    template: str | None = None
    confidence: float | None = None


@dataclass
class IDEConfig:
    """IDE 配置。"""

    name: str
    version: str
    operations: list[OperationConfig]


@dataclass
class SystemConfig:
    """系统配置。"""

    log_level: str = "INFO"
    log_file: str = "logs/ide_controller.log"
    screenshot_dir: str = "screenshots/"


@dataclass
class APIConfig:
    """API 配置。"""

    zhipuai_api_key: str
    model: str = "glm-4v-flash"
    timeout: int = 30
    # LLM API Base URL（可选，用于自定义代理或兼容接口）
    base_url: str | None = None


@dataclass
class AutomationConfig:
    """自动化配置。"""

    default_timeout: float = 5.0
    max_retries: int = 3
    retry_delay: float = 1.0
    action_delay: float = 0.2
    # 坐标校准偏移量 [x_offset, y_offset]
    coordinate_offset: list[int] = None


@dataclass
class SafetyConfig:
    """安全配置。"""

    dangerous_operations: list[str] | None = None
    require_confirmation: bool = True
    enable_undo: bool = True


@dataclass
class VisionConfig:
    """视觉识别配置。"""

    enabled: bool = True


@dataclass
class TemplateMatchingConfig:
    """模板匹配配置。"""

    # 模板图片存储目录（相对于项目根目录）
    template_dir: str = "templates/"
    # 默认匹配置信度阈值 (0.0-1.0)
    default_confidence: float = 0.8
    # 匹配方法: TM_CCOEFF_NORMED（推荐）、TM_CCORR_NORMED、TM_SQDIFF
    method: str = "TM_CCOEFF_NORMED"
    # 是否支持多尺度匹配（应对不同 DPI/缩放）
    enable_multiscale: bool = False
    # 多尺度匹配时的缩放比例列表
    scales: list[float] = None

    def __post_init__(self):
        if self.scales is None:
            self.scales = [0.8, 0.9, 1.0, 1.1, 1.2]


@dataclass
class MainConfig:
    """主配置文件。"""

    system: SystemConfig
    ide: IDEConfig
    api: APIConfig
    automation: AutomationConfig
    safety: SafetyConfig
    vision: VisionConfig = None
    template_matching: TemplateMatchingConfig = None
