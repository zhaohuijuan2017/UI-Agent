"""工作流执行器。"""

import time
from typing import Any

from src.workflow.models import (
    StepResult,
    WorkflowConfig,
    WorkflowResult,
    WorkflowStep,
)


class WorkflowExecutor:
    """工作流执行器。"""

    def __init__(self, ide_controller: Any) -> None:
        """初始化执行器。

        Args:
            ide_controller: IDE 控制器实例
        """
        self._ide = ide_controller

    def execute(self, config: WorkflowConfig, dry_run: bool = False) -> WorkflowResult:
        """执行工作流。

        Args:
            config: 工作流配置
            dry_run: 是否仅验证不执行

        Returns:
            执行结果
        """
        start_time = time.time()

        print(f"\n{'='*50}")
        print(f"开始执行工作流: {config.name}")
        if config.description:
            print(f"描述: {config.description}")
        print(f"总步骤数: {len(config.steps)}")
        print(f"{'='*50}\n")

        if dry_run:
            print("[Dry-Run] 仅验证模式，不执行实际操作\n")

        step_results = []
        context: dict[str, Any] = {
            "variables": config.variables.copy(),
            "previous_result": None,
        }

        for index, step in enumerate(config.steps):
            # 判断是否应该执行该步骤
            if not self._should_execute_step(step, index, context):
                print(f"  [跳过] 步骤 {index + 1}: {step.description}")
                step_results.append(
                    StepResult(
                        step_index=index,
                        description=step.description,
                        success=True,
                        skipped=True,
                    )
                )
                continue

            # 执行步骤
            if dry_run:
                result = self._dry_run_step(step, index)
            else:
                result = self._execute_step(step, index, context)

            step_results.append(result)

            # 更新上下文
            context["previous_result"] = result

            # 打印进度
            status = "[成功]" if result.success else "[失败]"
            retry_info = f" (重试 {result.retry_count} 次)" if result.retry_count > 0 else ""
            print(f"  {status} 步骤 {index + 1}: {step.description}{retry_info}")

            # 如果失败且不继续执行，则停止
            if not result.success and not step.continue_on_error:
                duration = time.time() - start_time
                print(f"\n{'='*50}")
                print(f"工作流执行失败: 步骤 {index + 1}")
                print(f"错误: {result.error_message}")
                print(f"{'='*50}\n")

                return WorkflowResult(
                    workflow_name=config.name,
                    success=False,
                    completed_steps=index + 1,
                    total_steps=len(config.steps),
                    failed_step=index,
                    error_message=result.error_message,
                    step_results=step_results,
                    duration=duration,
                )

        duration = time.time() - start_time

        # 检查是否所有步骤都成功
        all_success = all(r.success or r.skipped for r in step_results)

        print(f"\n{'='*50}")
        if all_success:
            print(f"工作流执行成功: {config.name}")
        else:
            print(f"工作流执行完成（有失败）: {config.name}")
        print(f"完成步骤: {len([r for r in step_results if not r.skipped])}/{len(config.steps)}")
        print(f"总耗时: {duration:.2f} 秒")
        print(f"{'='*50}\n")

        return WorkflowResult(
            workflow_name=config.name,
            success=all_success,
            completed_steps=len(config.steps),
            total_steps=len(config.steps),
            step_results=step_results,
            duration=duration,
        )

    def _should_execute_step(self, step: WorkflowStep, index: int, context: dict[str, Any]) -> bool:
        """判断是否应该执行步骤。

        Args:
            step: 步骤对象
            index: 步骤索引
            context: 执行上下文

        Returns:
            是否应该执行
        """
        # 第一个步骤总是执行
        if index == 0:
            return True

        # 没有条件则执行
        if not step.condition:
            return True

        # 解析条件
        condition = step.condition.strip()

        if condition == "if_success":
            # 上一步成功时执行
            prev_result = context.get("previous_result")
            return prev_result is not None and prev_result.success and not prev_result.skipped
        elif condition == "if_failure":
            # 上一步失败时执行
            prev_result = context.get("previous_result")
            return prev_result is not None and not prev_result.success and not prev_result.skipped

        # 默认执行
        return True

    def _execute_step(self, step: WorkflowStep, index: int, context: dict[str, Any]) -> StepResult:
        """执行单个步骤。

        Args:
            step: 步骤对象
            index: 步骤索引
            context: 执行上下文

        Returns:
            步骤结果
        """
        return self._execute_with_retry(step, index, context)

    def _execute_with_retry(
        self, step: WorkflowStep, index: int, context: dict[str, Any]
    ) -> StepResult:
        """带重试的执行。

        Args:
            step: 步骤对象
            index: 步骤索引
            context: 执行上下文

        Returns:
            步骤结果
        """
        start_time = time.time()
        last_error = None

        for attempt in range(step.retry_count + 1):
            try:
                # 获取 template 参数（如果有）
                template_name = step.parameters.get("template") if step.parameters else None

                # 构建命令
                if step.operation:
                    # 使用显式指定的操作
                    command = self._build_command_from_operation(step)
                else:
                    # 使用自然语言描述
                    command = step.description

                # 执行命令（传递 template 参数，并跳过意图识别）
                # 工作流中的步骤都是低级操作，不需要意图识别
                result = self._ide.execute_command(command, template_name=template_name, skip_intent_recognition=True)

                duration = time.time() - start_time

                # 检查执行结果
                if result.status.value in ("success", "cancelled"):
                    return StepResult(
                        step_index=index,
                        description=step.description,
                        success=result.status.value == "success",
                        error_message=result.error if result.status.value != "success" else None,
                        retry_count=attempt,
                        duration=duration,
                    )
                else:
                    last_error = result.error or result.message

                    # 如果还有重试机会，等待后重试
                    if attempt < step.retry_count:
                        print(f"    [警告] 执行失败，{step.retry_interval} 秒后重试...")
                        time.sleep(step.retry_interval)

            except Exception as e:
                last_error = str(e)
                duration = time.time() - start_time

                # 如果还有重试机会，等待后重试
                if attempt < step.retry_count:
                    print(f"    [警告] 执行异常，{step.retry_interval} 秒后重试...")
                    time.sleep(step.retry_interval)

        # 所有尝试都失败
        duration = time.time() - start_time
        return StepResult(
            step_index=index,
            description=step.description,
            success=False,
            error_message=last_error or "执行失败",
            retry_count=step.retry_count,
            duration=duration,
        )

    def _dry_run_step(self, step: WorkflowStep, index: int) -> StepResult:
        """Dry-run 模式下的步骤执行。

        Args:
            step: 步骤对象
            index: 步骤索引

        Returns:
            步骤结果
        """
        print(f"  [验证] 步骤 {index + 1}: {step.description}")
        if step.operation:
            print(f"       操作: {step.operation}")
            if step.parameters:
                print(f"       参数: {step.parameters}")
        if step.condition:
            print(f"       条件: {step.condition}")
        if step.retry_count > 0:
            print(f"       重试: {step.retry_count} 次，间隔 {step.retry_interval} 秒")
        if step.continue_on_error:
            print("       失败继续: 是")

        return StepResult(
            step_index=index,
            description=step.description,
            success=True,  # Dry-run 假设成功
            skipped=False,
        )

    def _build_command_from_operation(self, step: WorkflowStep) -> str:
        """从操作配置构建命令。

        Args:
            step: 步骤对象

        Returns:
            命令字符串
        """
        # 如果有参数，构建带参数的命令
        if step.parameters:
            # 特殊处理 input_text 操作
            input_text_value = step.parameters.get("input_text")
            submit_action_value = step.parameters.get("submit_action")

            if step.operation == "input_text" and input_text_value:
                # 构建自然语言格式的命令
                context_text = step.parameters.get("context_text", "")
                command = f"在{context_text}中输入 {input_text_value}"
                if submit_action_value == "enter":
                    command += " 并回车"
                return command

            # 其他操作的通用处理
            command = step.description
            for key, value in step.parameters.items():
                if key == "submit_action" and value == "enter":
                    command += " 并回车"
                elif key not in ("template", "input_text", "context_text") and isinstance(
                    value, str
                ):
                    command += f" {value}"
            return command

        return step.description
