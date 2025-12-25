"""配置管理器。"""

import os
import threading
import time
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from .schema import (
    ActionConfig,
    IDEConfig,
    MainConfig,
    OperationConfig,
    PostCheckConfig,
)


class ActionConfigModel(BaseModel):
    """Action 配置的 Pydantic 模型。"""

    type: str
    target: str | None = None
    parameters: dict[str, Any] | None = None
    timeout: float = 5.0
    retry: int = 3

    # 支持扁平化配置的额外字段
    keys: list[str] | None = None
    text: str | None = None
    duration: float | None = None
    delay: float | None = None
    dialog_title: str | None = None

    def to_action_config(self) -> ActionConfig:
        """转换为 ActionConfig。"""
        # 合并 parameters 和扁平字段
        merged_params = self.parameters.copy() if self.parameters else {}

        # 将扁平字段添加到 parameters 中
        if self.keys is not None:
            merged_params["keys"] = self.keys
        if self.text is not None:
            merged_params["text"] = self.text
        if self.duration is not None:
            merged_params["duration"] = self.duration
        if self.delay is not None:
            merged_params["delay"] = self.delay
        if self.dialog_title is not None:
            merged_params["dialog_title"] = self.dialog_title

        return ActionConfig(
            type=self.type,
            target=self.target,
            parameters=merged_params if merged_params else None,
            timeout=self.timeout,
            retry=self.retry,
        )


class PostCheckConfigModel(BaseModel):
    """PostCheck 配置的 Pydantic 模型。"""

    type: str
    parameters: dict[str, Any] | None = None

    def to_post_check_config(self) -> PostCheckConfig:
        """转换为 PostCheckConfig。"""
        return PostCheckConfig(
            type=self.type,
            parameters=self.parameters,
        )


class OperationConfigModel(BaseModel):
    """Operation 配置的 Pydantic 模型。"""

    name: str
    aliases: list[str]
    intent: str
    description: str
    visual_prompt: str | None = None
    actions: list[ActionConfigModel]
    preconditions: list[str] | None = None
    post_check: PostCheckConfigModel | None = None
    requires_confirmation: bool = False
    risk_level: str = "low"

    def to_operation_config(self) -> OperationConfig:
        """转换为 OperationConfig。"""
        return OperationConfig(
            name=self.name,
            aliases=self.aliases,
            intent=self.intent,
            description=self.description,
            visual_prompt=self.visual_prompt or "",
            actions=[a.to_action_config() for a in self.actions],
            preconditions=self.preconditions,
            post_check=self.post_check.to_post_check_config() if self.post_check else None,
            requires_confirmation=self.requires_confirmation,
            risk_level=self.risk_level,
        )


class IDEConfigModel(BaseModel):
    """IDE 配置的 Pydantic 模型。"""

    ide: str
    version: str
    operations: list[OperationConfigModel] = Field(default_factory=list)

    def to_ide_config(self) -> IDEConfig:
        """转换为 IDEConfig。"""
        return IDEConfig(
            name=self.ide,
            version=self.version,
            operations=[op.to_operation_config() for op in self.operations],
        )


class ConfigManager:
    """配置管理器。"""

    def __init__(
        self,
        config_path: str | None = None,
        enable_hot_reload: bool = False,
        reload_interval: float = 5.0,
    ) -> None:
        """初始化配置管理器。

        Args:
            config_path: 配置文件路径
            enable_hot_reload: 是否启用配置热更新
            reload_interval: 热更新检查间隔（秒）
        """
        self.config_path = config_path
        self._main_config: MainConfig | None = None
        self._ide_config: IDEConfig | None = None
        self._operation_map: dict[str, OperationConfig] = {}

        # 热更新相关
        self._enable_hot_reload = enable_hot_reload
        self._reload_interval = reload_interval
        self._last_modified: float | None = None
        self._reload_thread: threading.Thread | None = None
        self._stop_reload = threading.Event()
        self._reload_lock = threading.Lock()

        if enable_hot_reload and config_path:
            self._start_hot_reload()

    def load_config(self, path: str | None = None) -> MainConfig:
        """加载配置文件。

        Args:
            path: 配置文件路径

        Returns:
            主配置对象

        Raises:
            FileNotFoundError: 配置文件不存在
            ValidationError: 配置格式错误
        """
        if path:
            self.config_path = path

        if not self.config_path:
            raise ValueError("配置文件路径未指定")

        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        # 记录文件修改时间
        self._last_modified = config_file.stat().st_mtime

        # 环境变量替换
        with open(config_file, encoding="utf-8") as f:
            content = f.read()
            content = os.path.expandvars(content)

        data = yaml.safe_load(content)

        # 验证并加载配置
        try:
            with self._reload_lock:
                self._main_config = self._parse_main_config(data)
            return self._main_config
        except ValidationError as e:
            raise ValueError(f"配置验证失败: {e}") from e

    def _parse_main_config(self, data: dict[str, Any]) -> MainConfig:
        """解析主配置。"""
        # 这里简化处理，实际应该根据完整的 schema 进行验证
        # 为了实现简单，暂时返回一个基础配置对象
        from src.config.schema import (
            APIConfig,
            AutomationConfig,
            IDEConfig,
            SafetyConfig,
            SystemConfig,
        )

        system_data = data.get("system", {})
        ide_data = data.get("ide", {})
        api_data = data.get("api", {})
        automation_data = data.get("automation", {})
        safety_data = data.get("safety", {})

        # 加载 IDE 操作配置
        ide_config_path = ide_data.get("config_path")
        if ide_config_path:
            self._ide_config = self.load_ide_config(ide_config_path)
        else:
            self._ide_config = IDEConfig(name="unknown", version=">=0.0", operations=[])

        return MainConfig(
            system=SystemConfig(**system_data),
            ide=self._ide_config,
            api=APIConfig(
                zhipuai_api_key=api_data.get("zhipuai", {}).get("api_key", ""),
                model=api_data.get("zhipuai", {}).get("model", "glm-4v-flash"),
                timeout=api_data.get("zhipuai", {}).get("timeout", 30),
            ),
            automation=AutomationConfig(**automation_data),
            safety=SafetyConfig(**safety_data),
        )

    def load_ide_config(self, path: str) -> IDEConfig:
        """加载 IDE 操作配置。

        Args:
            path: IDE 配置文件路径

        Returns:
            IDE 配置对象
        """
        config_file = Path(path)
        if not config_file.exists():
            raise FileNotFoundError(f"IDE 配置文件不存在: {path}")

        with open(config_file, encoding="utf-8") as f:
            content = f.read()

        data = yaml.safe_load(content)

        try:
            model = IDEConfigModel(**data)
            self._ide_config = model.to_ide_config()

            # 构建操作映射
            for op in self._ide_config.operations:
                self._operation_map[op.name] = op
                for alias in op.aliases:
                    self._operation_map[alias] = op

            return self._ide_config
        except ValidationError as e:
            raise ValueError(f"IDE 配置验证失败: {e}") from e

    def get_operation(self, name: str) -> OperationConfig | None:
        """获取操作配置。

        Args:
            name: 操作名称或别名

        Returns:
            操作配置，如果不存在则返回 None
        """
        return self._operation_map.get(name)

    def list_operations(self) -> list[str]:
        """列出所有可用操作。"""
        return list(self._operation_map.keys())

    def validate_config(self, config: dict[str, Any]) -> bool:
        """验证配置。

        Args:
            config: 配置字典

        Returns:
            是否验证通过
        """
        try:
            IDEConfigModel(**config)
            return True
        except ValidationError:
            return False

    @property
    def main_config(self) -> MainConfig:
        """获取主配置。"""
        if self._main_config is None:
            raise ValueError("配置未加载")
        return self._main_config

    @property
    def ide_config(self) -> IDEConfig:
        """获取 IDE 配置。"""
        if self._ide_config is None:
            raise ValueError("IDE 配置未加载")
        return self._ide_config

    def _start_hot_reload(self) -> None:
        """启动配置热更新线程。"""
        self._stop_reload.clear()
        self._reload_thread = threading.Thread(target=self._reload_worker, daemon=True)
        self._reload_thread.start()

    def stop_hot_reload(self) -> None:
        """停止配置热更新。"""
        self._stop_reload.set()
        if self._reload_thread:
            self._reload_thread.join(timeout=2.0)

    def _reload_worker(self) -> None:
        """热更新工作线程。"""
        while not self._stop_reload.is_set():
            try:
                if self._check_and_reload():
                    # 配置已更新，可以触发回调或日志
                    pass
            except Exception:
                # 热更新失败不应影响主线程
                pass

            time.sleep(self._reload_interval)

    def _check_and_reload(self) -> bool:
        """检查并重新加载配置。

        Returns:
            是否重新加载了配置
        """
        if not self.config_path:
            return False

        config_file = Path(self.config_path)
        if not config_file.exists():
            return False

        try:
            current_mtime = config_file.stat().st_mtime
            if self._last_modified is None or current_mtime > self._last_modified:
                # 文件已修改，重新加载
                self.load_config()
                return True
        except OSError:
            return False

        return False

    def reload_now(self) -> bool:
        """立即重新加载配置。

        Returns:
            是否成功重新加载
        """
        try:
            self.load_config()
            return True
        except Exception:
            return False
