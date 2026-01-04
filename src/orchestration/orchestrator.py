"""任务编排器。"""

import logging
from typing import Any

from src.intent.models import Intent
from src.orchestration.context import ExecutionContext, StepExecutionResult
from src.orchestration.executor import TaskExecutor
from src.templates.engine import TemplateEngine
from src.templates.loader import TemplateLoader

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    """任务编排器。

    负责意图到模板的匹配、步骤编排和跨系统任务执行。
    """

    def __init__(self, executor: TaskExecutor, template_loader: TemplateLoader):
        """初始化任务编排器。

        Args:
            executor: 任务执行器
            template_loader: 模板加载器
        """
        self.executor = executor
        self.template_loader = template_loader
        self.template_engine = TemplateEngine()

    def orchestrate(
        self, intent: Intent, context: ExecutionContext | None = None
    ) -> ExecutionContext:
        """编排并执行任务。

        Args:
            intent: 识别到的意图
            context: 执行上下文（可选）

        Returns:
            执行上下文
        """
        if context is None:
            context = ExecutionContext()

        logger.info("=" * 60)
        logger.info("[任务编排] 开始编排任务流")
        logger.info(f"[任务编排] 意图类型: {intent.type}")
        logger.info(f"[任务编排] 意图参数: {intent.parameters}")
        logger.info(f"[任务编排] 意图置信度: {intent.confidence:.2f}")
        logger.info("=" * 60)

        context.status = "running"

        try:
            # 1. 匹配模板
            logger.info("[任务编排] 正在查找匹配的模板...")
            template = self.template_loader.get_template_by_intent(intent.type)
            if not template:
                logger.error(f"[任务编排失败] 未找到匹配的模板: {intent.type}")
                context.status = "failed"
                return context

            logger.info(f"[任务编排] 匹配到模板: {template.name}")
            logger.info(f"[任务编排] 模板描述: {template.description}")
            logger.info(f"[任务编排] 模板步骤数: {len(template.steps)}")

            # 2. 绑定参数
            logger.info("[任务编排] 正在绑定参数...")
            bound_template = self.template_engine.bind_parameters(
                template, intent, context.shared_data
            )
            logger.debug("[任务编排] 参数绑定完成")

            # 3. 执行步骤
            context.current_step = 0
            previous_success: bool | None = None

            logger.info("[任务编排] 开始执行步骤...")
            for i, step in enumerate(bound_template.steps):
                logger.info(f"[任务编排] 步骤 {i}: {step.system}.{step.action}")

                # 检查条件
                if not self.template_engine.should_execute_step(step, previous_success):
                    logger.info(f"[任务编排] 跳过步骤 {context.current_step}: 条件不满足")
                    context.save_step_result(
                        StepExecutionResult(
                            step_index=context.current_step,
                            success=True,
                            output={"skipped": True},
                        )
                    )
                    context.current_step += 1
                    continue

                # 执行步骤
                result = self.executor.execute_step(step, context, context.current_step)
                context.save_step_result(result)

                # 检查是否需要停止
                if not result.success and not step.continue_on_error:
                    logger.error(f"[任务编排] 步骤 {context.current_step} 失败，停止执行")
                    context.status = "failed"
                    self._log_execution_summary(context)
                    return context

                # 保存输出数据
                if step.output_to and result.output:
                    context.set_data(step.output_to, result.output)

                context.current_step += 1
                previous_success = result.success

            # 所有步骤执行完成
            context.status = "completed"
            logger.info("=" * 60)
            logger.info("[任务编排] 所有步骤执行完成")
            self._log_execution_summary(context)
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"[任务编排失败] 任务编排异常: {e}", exc_info=True)
            context.status = "failed"
            self._log_execution_summary(context)

        return context

    def _log_execution_summary(self, context: ExecutionContext) -> None:
        """记录执行摘要。

        Args:
            context: 执行上下文
        """
        summary = context.get_execution_summary()
        logger.info(f"[执行摘要] 状态: {summary['status']}")
        logger.info(f"[执行摘要] 总步骤数: {summary['total_steps']}")
        logger.info(f"[执行摘要] 成功步骤: {summary['successful_steps']}")
        logger.info(f"[执行摘要] 失败步骤: {summary['failed_steps']}")
        logger.info(f"[执行摘要] 总耗时: {summary['total_duration']:.2f}秒")

    def show_execution_plan(self, intent: Intent) -> dict[str, Any]:
        """显示执行计划。

        Args:
            intent: 识别到的意图

        Returns:
            执行计划信息
        """
        template = self.template_loader.get_template_by_intent(intent.type)
        if not template:
            return {"error": f"未找到匹配的模板: {intent.type}"}

        plan = {
            "intent": intent.type,
            "template": template.name,
            "description": template.description,
            "steps": [],
        }

        for i, step in enumerate(template.steps):
            step_info = {
                "index": i,
                "system": step.system,
                "action": step.action,
                "description": f"{step.system}: {step.action}",
            }
            plan["steps"].append(step_info)

        return plan
