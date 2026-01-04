# 意图识别指南

本文档介绍 UI-Agent 的意图识别系统，包括如何使用意图识别和如何定义新的意图类型。

## 概述

意图识别系统基于大语言模型（LLM），能够自动理解用户的自然语言输入，识别用户的意图并提取相关参数。

### 工作流程

```
用户输入 → 意图识别 → 模板匹配 → 任务编排 → 执行 → 报告
```

1. **意图识别**：分析用户消息，识别意图类型和参数
2. **模板匹配**：根据意图类型查找对应的任务流模板
3. **任务编排**：绑定参数，编排执行步骤
4. **执行**：按步骤执行跨系统操作
5. **报告**：生成详细的执行报告

## 支持的意图类型

### 单系统意图

仅涉及一个系统的操作。

#### `develop-feature` - 需求开发

在 IDE 中直接开发功能。

**系统**：IDE

**参数**：
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `requirement_text` | string | 是 | 需求文本内容 |

**示例**：
- "帮我开发一个购物车功能"
- "实现用户登录功能"

#### `view-requirement` - 需求查看

在浏览器中查看需求详情。

**系统**：Browser

**参数**：
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 需求链接 |
| `requirement_id` | string | 否 | 需求编号（如 ISSUE-1） |

**示例**：
- "帮我查看 https://github.com/user/repo/issues/1 的需求详情"
- "打开这个需求页面 https://example.com/issue/123"

#### `deploy_application` - 部署应用

部署应用到指定环境。

**系统**：Terminal

**参数**：
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `environment` | string | 是 | 目标环境（test/staging/production） |
| `branch` | string | 否 | 部署分支 |

**示例**：
- "部署到测试环境"
- "部署 main 分支到生产环境"

#### `test_code` - 测试代码

运行测试并生成报告。

**系统**：Terminal

**参数**：
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `test_type` | string | 否 | 测试类型（unit/integration/e2e） |
| `generate_report` | boolean | 否 | 是否生成覆盖率报告 |

**示例**：
- "运行单元测试"
- "运行所有测试并生成覆盖率报告"

#### `review_code` - 代码审查

执行代码审查。

**系统**：IDE

**参数**：
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `scope` | string | 否 | 审查范围（current_file/staged_changes/all） |

**示例**：
- "审查当前文件的代码"
- "审查所有暂存的更改"

### 跨系统组合意图

涉及多个系统协同的操作。

#### `requirement-to-development` - 需求查看并开发

先在浏览器中查看需求，然后在 IDE 中进行开发。

**系统**：Browser → IDE

**参数**：
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 需求链接 |
| `requirement_id` | string | 否 | 需求编号 |

**示例**：
- "查看这个需求 https://github.com/user/repo/issues/4 并实现它"
- "帮我查看需求然后开发功能"

#### `analyze_requirements` - 分析需求

从链接或文件中分析需求。

**系统**：Browser、IDE

**参数**：
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `source` | string | 是 | 需求来源（URL 或文件路径） |

**示例**：
- "分析这个需求文档 https://example.com/doc.md"

#### `design_solution` - 设计方案

基于需求进行方案设计。

**系统**：IDE

**参数**：
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `requirement_text` | string | 是 | 需求描述 |

**示例**：
- "为用户认证功能设计方案"

#### `implement_feature` - 实现功能

基于设计或需求实现功能。

**系统**：IDE

**参数**：
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `specification` | string | 是 | 设计文档或需求描述 |

**示例**：
- "按照设计文档实现购物车功能"

## 意图定义文件

意图定义在 `config/intent_definitions.yaml` 中配置。

### 定义格式

```yaml
intents:
  intent-name:
    type: single-system  # 或 composite
    description: 意图描述
    system: ide  # 单系统意图的目标系统
    systems:     # 组合意图涉及的系统
      - browser
      - ide
    parameters:
      parameter_name:
        type: string
        description: 参数说明
        required: true
        examples:
          - 示例1
          - 示例2
        pattern: "regex_pattern"  # 可选的验证模式
```

### 添加新意图

1. 在 `config/intent_definitions.yaml` 中添加新意图定义
2. 在 `workflows/templates/` 中创建对应的任务流模板
3. 在 `src/orchestration/adapters.py` 中注册系统适配器（如果需要）

### 示例：添加新意图

```yaml
intents:
  debug-application:
    type: single-system
    description: 启动调试会话
    system: ide
    parameters:
      target:
        type: string
        description: 调试目标（当前文件/特定文件）
        required: true
        examples:
          - "当前文件"
          - "main.py"
      breakpoints:
        type: string
        description: 断点位置
        required: false
```

## 程序化使用

### 基本用法

```python
from zhipuai import ZhipuAI
from src.intent.recognizer import IntentRecognizer
from src.templates.loader import TemplateLoader
from src.orchestration.executor import TaskExecutor
from src.orchestration.orchestrator import TaskOrchestrator
from src.orchestration.adapters import BrowserSystemAdapter, IDESystemAdapter

# 初始化 LLM 客户端
llm_client = ZhipuAI(api_key="your-api-key")

# 创建意图识别器
recognizer = IntentRecognizer(
    intent_definitions_path="config/intent_definitions.yaml",
    llm_client=llm_client,
)

# 识别意图
result = recognizer.recognize("帮我开发一个购物车功能")
print(f"意图类型: {result.intent.type}")
print(f"置信度: {result.confidence}")
print(f"参数: {result.intent.parameters}")

# 创建任务执行器
executor = TaskExecutor()
executor.register_adapter("browser", BrowserSystemAdapter())
executor.register_adapter("ide", IDESystemAdapter())

# 创建模板加载器
template_loader = TemplateLoader()
template_loader.load_from_directory("workflows/templates")

# 创建编排器
orchestrator = TaskOrchestrator(executor, template_loader)

# 执行任务
context = orchestrator.orchestrate(result.intent)
print(context.format_report())
```

### 获取执行计划

```python
# 显示执行计划（不实际执行）
plan = orchestrator.show_execution_plan(result.intent)
print(f"模板: {plan['template']}")
print(f"步骤数: {len(plan['steps'])}")
for step in plan['steps']:
    print(f"  {step['system']}: {step['action']}")
```

## 置信度阈值

系统默认置信度阈值为 0.85。当识别置信度低于阈值时，系统会记录警告日志。

```python
recognizer = IntentRecognizer(
    intent_definitions_path="config/intent_definitions.yaml",
    llm_client=llm_client,
    confidence_threshold=0.90,  # 自定义阈值
)
```

## 执行报告

每次任务执行后，可以获取详细的执行报告：

```python
context = orchestrator.orchestrate(intent)

# 获取摘要
summary = context.get_execution_summary()
print(f"状态: {summary['status']}")
print(f"总步骤: {summary['total_steps']}")
print(f"成功: {summary['successful_steps']}")
print(f"失败: {summary['failed_steps']}")
print(f"耗时: {summary['total_duration']:.2f}秒")

# 获取详细报告
detailed = context.get_detailed_report()

# 格式化报告
report_text = context.format_report()
print(report_text)
```

## 日志

意图识别和任务执行过程会记录详细日志：

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)

# 日志会记录：
# - 意图识别过程
# - LLM 调用和响应
# - 参数提取结果
# - 模板匹配情况
# - 任务执行步骤
# - 跨系统切换
# - 执行结果和错误
```

## 常见问题

### Q: 如何提高意图识别准确率？

A:
1. 提供清晰的意图描述和示例
2. 使用明确的参数类型和验证模式
3. 调整置信度阈值
4. 优化提示词模板

### Q: 如何处理未识别的意图？

A: 系统会返回 `intent_type="unknown"`，可以：
1. 检查日志了解失败原因
2. 添加新的意图定义
3. 改进现有意图的描述

### Q: 如何调试意图识别？

A:
1. 启用 DEBUG 级别日志查看详细信息
2. 检查 LLM 响应内容
3. 验证意图定义格式

### Q: 支持哪些 LLM？

A: 目前支持智谱 AI 的 GLM 系列（glm-4-flash、glm-4v-flash 等）。可以通过配置自定义模型和 API 端点。
