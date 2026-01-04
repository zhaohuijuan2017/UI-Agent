"""任务执行器。"""

import logging
import time

from src.orchestration.adapters import SystemAdapter
from src.orchestration.context import ExecutionContext, StepExecutionResult
from src.templates.models import TemplateStep

logger = logging.getLogger(__name__)


class TaskExecutor:
    """任务执行器。

    负责执行单个任务步骤，管理跨系统切换和数据传递。
    """

    def __init__(self):
        """初始化任务执行器。"""
        self._adapters: dict[str, SystemAdapter] = {}
        self._current_system: str | None = None

    def register_adapter(self, system: str, adapter: SystemAdapter) -> None:
        """注册系统适配器。

        Args:
            system: 系统名称（browser、ide、terminal 等）
            adapter: 系统适配器
        """
        self._adapters[system] = adapter
        logger.info(f"[系统适配器] 已注册系统适配器: {system}")

    def execute_step(
        self, step: TemplateStep, context: ExecutionContext, step_index: int
    ) -> StepExecutionResult:
        """执行单个任务步骤。

        Args:
            step: 模板步骤
            context: 执行上下文
            step_index: 步骤索引

        Returns:
            步骤执行结果
        """
        start_time = time.time()

        logger.info("-" * 50)
        logger.info(f"[任务执行] 步骤 [{step_index}] 开始执行")
        logger.info(f"[任务执行] 目标系统: {step.system}")
        logger.info(f"[任务执行] 执行动作: {step.action}")
        logger.info(f"[任务执行] 动作参数: {step.parameters}")

        # 记录跨系统切换
        if self._current_system and self._current_system != step.system:
            logger.info(f"[系统切换] {self._current_system} -> {step.system}")
        self._current_system = step.system

        try:
            # 检查是否有对应的适配器
            adapter = self._adapters.get(step.system)
            if not adapter:
                logger.error(f"[任务执行失败] 未找到系统适配器: {step.system}")
                return StepExecutionResult(
                    step_index=step_index,
                    success=False,
                    error=f"未找到系统适配器: {step.system}",
                )

            logger.debug(f"[任务执行] 使用适配器: {adapter.__class__.__name__}")

            # 执行动作
            logger.info("[任务执行] 正在执行动作...")
            result = adapter.execute(step.action, step.parameters)

            # 保存输出数据到上下文
            if result.success:
                logger.info("[任务执行成功] 动作执行完成")
                if result.output:
                    logger.debug(f"[任务执行] 输出数据: {result.output}")
                    if step.output_to:
                        context.set_data(step.output_to, result.output)
                        logger.debug(f"[任务执行] 数据已保存到上下文: {step.output_to}")
                    # 同时也保存到步骤特定的键
                    context.set_data(f"step_{step_index}_output", result.output)
            else:
                logger.error(f"[任务执行失败] 动作执行失败: {result.error}")

            # 计算执行时长
            result.duration = time.time() - start_time
            result.step_index = step_index

            logger.info(f"[任务执行] 步骤 [{step_index}] 执行时长: {result.duration:.2f}秒")
            logger.info(
                f"[任务执行] 步骤 [{step_index}] 执行状态: {'成功' if result.success else '失败'}"
            )
            logger.info("-" * 50)

            return result

        except Exception as e:
            logger.error(f"[任务执行异常] 步骤执行异常: {e}", exc_info=True)
            logger.info("-" * 50)
            return StepExecutionResult(
                step_index=step_index,
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
