# 模板编写指南

本文档介绍如何编写和使用任务流模板，实现自动化的跨系统操作流程。

## 概述

任务流模板定义了一系列操作步骤，系统会按照模板自动执行这些步骤。模板支持参数绑定、条件分支、数据传递等功能。

## 模板结构

### 模板定义（YAML 格式）

```yaml
name: template-name              # 模板名称
description: 模板描述            # 模板说明
intent_types:                    # 适用的意图类型
  - intent-type-1
  - intent-type-2
steps:                           # 执行步骤
  - system: ide                  # 目标系统
    action: action_name          # 执行动作
    parameters:                  # 动作参数
      param1: value1
      param2: "{{intent.param}}"  # 占位符
    condition: if_success        # 执行条件（可选）
    input_from: data_key         # 输入数据来源（可选）
    output_to: data_key          # 输出数据目标（可选）
    continue_on_error: false     # 失败时是否继续（可选）
```

### 模板属性

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 模板名称，通常与意图类型相同 |
| `description` | string | 是 | 模板描述 |
| `intent_types` | list | 是 | 适用的意图类型列表 |
| `steps` | list | 是 | 执行步骤列表 |
| `parameters` | dict | 否 | 模板级参数定义 |

### 步骤属性

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `system` | string | 是 | 目标系统（ide/browser/terminal） |
| `action` | string | 是 | 执行的动作名称 |
| `parameters` | dict | 否 | 动作参数 |
| `condition` | string | 否 | 执行条件（if_success/if_failure） |
| `input_from` | string | 否 | 从上下文读取数据的键名 |
| `output_to` | string | 否 | 输出数据到上下文的键名 |
| `continue_on_error` | bool | 否 | 失败时是否继续执行 |

## 占位符和参数绑定

### 意图参数

使用 `{{intent.param_name}}` 引用意图中的参数：

```yaml
steps:
  - system: ide
    action: generate_code
    parameters:
      requirement: "{{intent.requirement_text}}"
      language: "{{intent.language}}"
```

### 上下文数据

使用 `input_from` 从上下文读取前一步的输出：

```yaml
steps:
  - system: browser
    action: extract_data
    output_to: extracted_data

  - system: ide
    action: use_data
    input_from: extracted_data
```

## 条件执行

### if_success

仅在上一步成功时执行：

```yaml
steps:
  - system: browser
    action: open_url
    parameters:
      url: "https://example.com"

  - system: browser
    action: extract_content
    condition: if_success
```

### if_failure

仅在上一步失败时执行：

```yaml
steps:
  - system: ide
    action: risky_operation

  - system: ide
    action: handle_error
    condition: if_failure
```

## 数据传递

### 输出数据

使用 `output_to` 将步骤输出保存到上下文：

```yaml
steps:
  - system: browser
    action: extract_requirement
    parameters:
      url: "{{intent.url}}"
    output_to: requirement_data
```

### 输入数据

使用 `input_from` 从上下文读取数据：

```yaml
steps:
  - system: ide
    action: generate_code
    input_from: requirement_data
    parameters:
      template: "default"
```

## 错误处理

### continue_on_error

设置 `continue_on_error: true` 使步骤失败时不中断执行：

```yaml
steps:
  - system: ide
    action: optional_step
    continue_on_error: true

  - system: ide
    action: next_step  # 即使上一步失败也会执行
```

## 完整示例

### 单系统模板：需求开发

```yaml
name: develop-feature
description: 需求开发模板
intent_types:
  - develop-feature
steps:
  - system: ide
    action: switch_ide
    parameters:
      ide_name: "PyCharm"

  - system: ide
    action: activate_plugin
    parameters:
      plugin_name: "ai-assistant"

  - system: ide
    action: generate_code
    parameters:
      requirement: "{{intent.requirement_text}}"
```

### 跨系统模板：需求查看并开发

```yaml
name: requirement-to-development
description: 需求查看并开发
intent_types:
  - requirement-to-development
steps:
  - system: browser
    action: open_url
    parameters:
      url: "{{intent.url}}"
    output_to: page_content

  - system: browser
    action: extract_requirement
    input_from: page_content
    output_to: requirement_data

  - system: ide
    action: switch_ide
    parameters:
      ide_name: "PyCharm"

  - system: ide
    action: generate_code
    parameters:
      requirement: "{{intent.requirement_text}}"
    input_from: requirement_data
```

### 带条件分支的模板

```yaml
name: deploy-with-validation
description: 部署前验证
intent_types:
  - deploy_application
steps:
  - system: terminal
    action: run_tests
    parameters:
      test_type: "unit"

  - system: terminal
    action: deploy
    parameters:
      environment: "{{intent.environment}}"
    condition: if_success

  - system: terminal
    action: notify_failure
    condition: if_failure
```

## 创建新模板

1. 在 `workflows/templates/` 目录创建新的 YAML 文件
2. 定义模板结构和步骤
3. 如果需要，实现对应的系统适配器
4. 重新加载模板（或重启应用）

### 示例模板文件

`workflows/templates/custom-task.yaml`：

```yaml
name: custom-task
description: 自定义任务模板
intent_types:
  - custom-intent
steps:
  - system: ide
    action: custom_action
    parameters:
      param1: "value1"
```

### 加载自定义模板

```python
from src.templates.loader import TemplateLoader

loader = TemplateLoader()
loader.load_from_file("workflows/templates/custom-task.yaml")
```

## 系统适配器

每个系统需要实现 `SystemAdapter` 接口：

```python
from src.orchestration.adapters import SystemAdapter
from src.orchestration.context import StepExecutionResult

class CustomSystemAdapter(SystemAdapter):
    def execute(self, action: str, parameters: dict) -> StepExecutionResult:
        """执行动作"""
        try:
            # 实现具体逻辑
            result = self._do_action(action, parameters)

            return StepExecutionResult(
                step_index=0,
                success=True,
                output=result,
                duration=0.5,
            )
        except Exception as e:
            return StepExecutionResult(
                step_index=0,
                success=False,
                error=str(e),
                duration=0.5,
            )
```

### 注册适配器

```python
from src.orchestration.executor import TaskExecutor

executor = TaskExecutor()
executor.register_adapter("custom", CustomSystemAdapter())
```

## 内置系统和动作

### IDE 系统 (`ide`)

| 动作 | 参数 | 说明 |
|------|------|------|
| `switch_ide` | `ide_name` | 切换到指定 IDE |
| `activate_plugin` | `plugin_name` | 激活插件 |
| `generate_code` | `requirement` | 生成代码 |

### 浏览器系统 (`browser`)

| 动作 | 参数 | 说明 |
|------|------|------|
| `open_url` | `url` | 打开 URL |
| `extract_data` | - | 提取页面数据 |
| `click` | `selector` | 点击元素 |

### 终端系统 (`terminal`)

| 动作 | 参数 | 说明 |
|------|------|------|
| `run_tests` | `test_type` | 运行测试 |
| `deploy` | `environment` | 部署应用 |

## 最佳实践

1. **命名规范**：使用清晰的模板和步骤名称
2. **错误处理**：合理使用 `continue_on_error`
3. **数据传递**：使用 `input_from` 和 `output_to` 实现步骤间数据流转
4. **参数验证**：在意图定义中添加参数验证规则
5. **文档化**：为模板添加详细描述
6. **测试**：先使用 `--dry-run` 验证模板

## 调试

### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 查看执行计划

```python
plan = orchestrator.show_execution_plan(intent)
print(plan)
```

### 使用 Dry Run 模式

```bash
python -m src.main --workflow workflows/template.md --dry-run
```

## 常见问题

### Q: 如何实现循环执行？

A: 当前版本不支持循环，建议通过多个步骤实现。

### Q: 如何共享多个步骤的数据？

A: 使用 `output_to` 将数据保存到上下文，后续步骤可通过 `input_from` 或直接访问。

### Q: 参数替换失败怎么办？

A: 检查占位符格式，确保参数名正确且存在于意图参数中。

### Q: 如何调试模板执行？

A: 启用 DEBUG 日志，查看详细的执行过程和数据流转。
