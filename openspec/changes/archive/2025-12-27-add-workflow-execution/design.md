# 工作流执行架构设计

## 设计目标

设计一个可扩展、易用的工作流执行系统，支持：
1. 通过 Markdown 文档定义多步骤操作
2. 串行执行步骤，按文档顺序
3. 条件分支能力（基于前一步结果）
4. 可配置的重试机制
5. 混合格式（自然语言 + 结构化配置）

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         工作流系统                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Markdown 文档 │───>│   解析器     │───>│  工作流配置   │       │
│  │  (用户编写)   │    │  (Parser)    │    │  (Config)    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                   │              │
│                                                   v              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   执行结果    │<───│   执行器     │<───│   验证器     │       │
│  │  (Result)    │    │ (Executor)   │    │ (Validator)  │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                            │                                     │
│                            v                                     │
│                   ┌──────────────────┐                          │
│                   │  IDE 控制器       │                          │
│                   │ (IDEController)  │                          │
│                   └──────────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 数据模型 (models.py)

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

@dataclass
class WorkflowStep:
    """工作流步骤模型"""

    description: str  # 步骤描述（自然语言）
    operation: Optional[str] = None  # 操作名称（从描述解析或显式指定）
    parameters: Dict[str, Any] = field(default_factory=dict)  # 操作参数
    retry_count: int = 0  # 重试次数
    retry_interval: float = 1.0  # 重试间隔（秒）
    condition: Optional[str] = None  # 执行条件
    continue_on_error: bool = False  # 失败时是否继续

@dataclass
class WorkflowConfig:
    """工作流配置模型"""

    name: str  # 工作流名称
    description: str = ""  # 工作流描述
    steps: List[WorkflowStep] = field(default_factory=list)  # 步骤列表
    variables: Dict[str, Any] = field(default_factory=dict)  # 变量字典
    metadata: Dict[str, Any] = field(default_factory=dict)  # 其他元数据

@dataclass
class StepResult:
    """步骤执行结果"""

    step_index: int  # 步骤索引
    description: str  # 步骤描述
    success: bool  # 是否成功
    error_message: Optional[str] = None  # 错误信息
    retry_count: int = 0  # 实际重试次数
    duration: float = 0.0  # 执行时长

@dataclass
class WorkflowResult:
    """工作流执行结果"""

    workflow_name: str  # 工作流名称
    success: bool  # 整体是否成功
    completed_steps: int  # 完成的步骤数
    total_steps: int  # 总步骤数
    failed_step: Optional[int] = None  # 失败的步骤索引
    error_message: Optional[str] = None  # 错误信息
    step_results: List[StepResult] = field(default_factory=list)  # 每步结果
    duration: float = 0.0  # 总执行时长
```

### 2. 解析器 (parser.py)

```python
class WorkflowParser:
    """工作流解析器"""

    def parse_file(self, path: str) -> WorkflowConfig:
        """解析工作流文件"""

    def parse_content(self, content: str) -> WorkflowConfig:
        """解析工作流内容"""

    def _extract_front_matter(self, content: str) -> Dict[str, Any]:
        """提取 YAML front matter"""

    def _extract_steps(self, content: str) -> List[WorkflowStep]:
        """提取步骤列表"""

    def _parse_step(self, step_text: str, index: int) -> WorkflowStep:
        """解析单个步骤"""

    def _extract_yaml_block(self, step_text: str) -> Optional[Dict[str, Any]]:
        """提取 YAML 代码块"""
```

**解析策略**：

1. **YAML Front Matter**：提取工作流元数据
2. **步骤识别**：识别有序列表作为步骤
3. **混合格式处理**：
   - 纯文本：使用自然语言解析器映射到操作
   - 带 YAML 块：从 YAML 提取结构化参数
4. **条件解析**：识别 `[if_*]` 语法

### 3. 执行器 (executor.py)

```python
class WorkflowExecutor:
    """工作流执行器"""

    def __init__(self, ide_controller: IDEController):
        self._ide = ide_controller

    def execute(self, config: WorkflowConfig) -> WorkflowResult:
        """执行工作流"""

    def _execute_step(
        self,
        step: WorkflowStep,
        index: int,
        context: Dict[str, Any]
    ) -> StepResult:
        """执行单个步骤"""

    def _should_execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> bool:
        """判断是否应该执行步骤"""

    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> bool:
        """评估条件表达式"""

    def _execute_with_retry(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> StepResult:
        """带重试的执行"""
```

**执行流程**：

```
开始
  │
  v
初始化上下文
  │
  v
┌─────────────────┐
│ 遍历每个步骤    │<─────────┐
└─────────────────┘          │
  │                          │
  v                          │
检查条件是否满足 ────否────> 跳过步骤
  │是
  v
执行操作
  │
  v
检查是否需要重试 ────是────> 延迟后重试
  │否                      │
  v                         │
记录结果                    │
  │                         │
  v                         │
更新上下文 ──────────────────┘
  │
  v
检查是否继续 ────否────> 返回结果
  │是（且未出错）
  v
下一个步骤
```

### 4. 验证器 (validator.py)

```python
class WorkflowValidator:
    """工作流验证器"""

    def validate(self, config: WorkflowConfig) -> List[str]:
        """验证工作流配置，返回错误列表"""

    def _validate_step(self, step: WorkflowStep, index: int) -> List[str]:
        """验证单个步骤"""

    def _validate_operation(self, operation: str) -> bool:
        """验证操作名称是否有效"""
```

## 关键设计决策

### 1. 为什么选择 Markdown？

- **可读性**：用户友好的格式
- **易编辑**：任何文本编辑器都可以编辑
- **版本控制友好**：Diff 清晰
- **支持代码块**：可嵌入结构化配置

### 2. 条件分支设计

采用简化的条件语法：
- `[if_success]`：上一步成功时执行
- `[if_failure]`：上一步失败时执行
- `[if <expression>]`：自定义条件

条件评估基于执行上下文：
```python
context = {
    "previous_result": StepResult,
    "all_results": List[StepResult],
    "variables": Dict[str, Any]
}
```

### 3. 重试机制

重试是步骤级别的配置：
- 在步骤级别设置重试策略
- 重试之间有可配置的延迟
- 记录每次重试的尝试
- 所有重试失败后决定是否继续

### 4. 错误处理策略

提供灵活的错误处理：
- `continue_on_error`：失败时继续执行后续步骤
- 条件分支：根据失败执行不同的步骤
- 详细错误信息：记录失败步骤和原因

### 5. 与现有系统集成

通过 `IDEController` 集成：
- 工作流执行器调用 `IDEController` 的现有方法
- 复用现有的操作配置（`config/operations/*.yaml`）
- 保持单步操作和工作流操作的一致性

## Markdown 格式规范

### 基础格式

```markdown
---
name: "工作流名称"
description: "工作流描述"
variables:
  key: value
---

# 标题（可选）

## 步骤

1. 第一步描述（自然语言）

2. 第二步描述（带配置）

   ```yaml
   operation: 具体操作名
   parameters:
     key: value
   retry_count: 3
   condition: if_success
   continue_on_error: true
   ```

3. [if_success] 条件步骤
```

### 格式规则

1. **元数据**：YAML front matter（可选）
2. **步骤**：有序列表项
3. **配置块**：步骤下方的 YAML 代码块（可选）
4. **条件标记**：`[条件]` 前缀（可选）
5. **注释**：使用 HTML 注释 `<!-- -->`

## 示例工作流

```markdown
---
name: "晨间检查流程"
description: "每天早晨的检查清单"
variables:
  repo_url: "https://github.com/user/repo"
---

# 晨间检查工作流

## 步骤

1. 激活 PyCharm 窗口

2. 打开浏览器访问仓库

   ```yaml
   operation: open_browser
   parameters:
     url: "{{repo_url}}"
   ```

3. [if_success] 搜索 "python" 关键词

   ```yaml
   operation: input_text
   parameters:
     context_text: "搜索框"
     input_text: "python"
     submit_action: enter
   retry_count: 2
   ```

4. 打开文件 main.py

   ```yaml
   operation: double_click_file
   parameters:
     filename: "main.py"
   ```

5. 跳转到第 42 行

   ```yaml
   operation: go_to_line
   parameters:
     line_number: 42
   ```
```

## 扩展性考虑

### 未来可能的扩展

1. **变量替换**：`{{variable_name}}` 语法
2. **循环支持**：`for` 循环步骤
3. **并行执行**：标记可并行的步骤组
4. **工作流嵌套**：调用子工作流
5. **异步执行**：支持异步操作
6. **钩子函数**：前置/后置钩子

### 设计预留

- `WorkflowConfig.variables`：预留变量支持
- `WorkflowStep.condition`：支持复杂条件表达式
- 上下文传递：步骤间可通过上下文传递数据
