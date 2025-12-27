# workflow-execution Specification

## Purpose
TBD - created by archiving change add-workflow-execution. Update Purpose after archive.
## 需求
### 需求：Markdown 工作流文档解析

系统**必须**能够解析 Markdown 格式的工作流文档。

#### 场景：解析基础工作流文档

**Given** 存在一个包含步骤列表的 Markdown 文件
**When** 系统解析该文件
**Then** 应成功提取所有步骤
**And** 每个步骤应包含描述信息
**And** 返回有效的 `WorkflowConfig` 对象

#### 场景：解析带元数据的工作流文档

**Given** Markdown 文件包含 YAML front matter
**When** 系统解析该文件
**Then** 应提取 name、description、variables 等元数据
**And** 元数据应正确关联到 `WorkflowConfig`

#### 场景：解析带结构化配置的步骤

**Given** 步骤包含嵌套的 YAML 代码块
**When** 系统解析该步骤
**Then** 应提取 operation、parameters 等配置
**And** 配置应正确关联到对应的 `WorkflowStep`

#### 场景：解析带条件标记的步骤

**Given** 步骤描述以 `[if_success]` 开头
**When** 系统解析该步骤
**Then** 应识别条件标记
**And** condition 字段应设置为 `"if_success"`

#### 场景：处理无效的 Markdown 格式

**Given** Markdown 文件格式无效（如列表格式错误）
**When** 系统尝试解析该文件
**Then** 应返回 `WorkflowParseError`
**And** 错误信息应指出格式问题位置

#### 场景：处理不存在的文件

**Given** 指定的工作流文件不存在
**When** 系统尝试解析该文件
**Then** 应返回 `WorkflowParseError`
**And** 错误信息应说明文件未找到

---

### 需求：工作流顺序执行

系统**必须**按照文档中定义的顺序依次执行步骤。

#### 场景：执行简单的两步骤工作流

**Given** 工作流包含两个步骤："激活窗口" 和 "打开文件"
**When** 系统执行该工作流
**Then** 应先执行"激活窗口"
**And** 完成后再执行"打开文件"
**And** 返回成功状态

#### 场景：执行五步骤工作流

**Given** 工作流包含五个步骤
**When** 系统执行该工作流
**Then** 应按顺序执行所有步骤
**And** `completed_steps` 应等于 5
**And** 所有步骤结果应被记录

#### 场景：中间步骤失败时的行为

**Given** 工作流包含三个步骤，第二步会失败
**And** 第二步的 `continue_on_error` 为 false
**When** 系统执行该工作流
**Then** 应在第二步失败后停止
**And** `failed_step` 应等于 1（第二步）
**And** 第三步不应被执行

#### 场景：步骤失败但继续执行

**Given** 工作流包含三个步骤，第二步会失败
**And** 第二步的 `continue_on_error` 为 true
**When** 系统执行该工作流
**Then** 第二步失败后应继续执行第三步
**And** 所有三个步骤都应被执行
**And** 最终结果应标记为失败（因为有步骤失败）

---

### 需求：条件分支执行

系统**必须**支持基于前一步执行结果的条件分支。

#### 场景：if_success 条件满足时执行

**Given** 上一步执行成功
**And** 当前步骤标记为 `[if_success]`
**When** 系统评估是否执行当前步骤
**Then** 应执行当前步骤

#### 场景：if_success 条件不满足时跳过

**Given** 上一步执行失败
**And** 当前步骤标记为 `[if_success]`
**When** 系统评估是否执行当前步骤
**Then** 应跳过当前步骤
**And** 步骤结果应标记为"跳过"

#### 场景：if_failure 条件满足时执行

**Given** 上一步执行失败
**And** 当前步骤标记为 `[if_failure]`
**When** 系统评估是否执行当前步骤
**Then** 应执行当前步骤

#### 场景：无条件的步骤始终执行

**Given** 当前步骤没有条件标记
**When** 系统评估是否执行当前步骤
**Then** 应始终执行当前步骤

#### 场景：第一个步骤之前的条件被忽略

**Given** 第一个步骤标记了 `[if_success]`
**When** 系统执行工作流
**Then** 应忽略该条件标记
**And** 应执行第一个步骤

---

### 需求：步骤重试机制

系统**必须**支持为步骤配置重试策略。

#### 场景：步骤执行成功无需重试

**Given** 步骤配置 `retry_count: 3`
**And** 步骤第一次执行就成功
**When** 系统执行该步骤
**Then** 不应进行重试
**And** `retry_count` 结果应为 0

#### 场景：步骤失败后在重试次数内成功

**Given** 步骤配置 `retry_count: 3`
**And** 步骤前两次失败，第三次成功
**When** 系统执行该步骤
**Then** 应进行 2 次重试
**And** 最终应返回成功状态
**And** 实际重试次数应为 2

#### 场景：步骤超过重试次数仍失败

**Given** 步骤配置 `retry_count: 3`
**And** 所有尝试（包括重试）都失败
**When** 系统执行该步骤
**Then** 应进行 3 次重试
**And** 最终应返回失败状态
**And** 错误信息应说明重试次数已用尽

#### 场景：重试之间的延迟

**Given** 步骤配置 `retry_count: 2` 和 `retry_interval: 2.0`
**And** 步骤需要重试
**When** 系统执行重试
**Then** 每次重试之间应延迟 2 秒
**And** 延迟时间应被计入总执行时长

#### 场景：默认不重试

**Given** 步骤未配置 `retry_count`
**When** 步骤执行失败
**Then** 不应进行重试
**And** 应立即返回失败状态

---

### 需求：自然语言操作映射

系统**必须**能够将自然语言描述映射到具体的操作。

#### 场景：映射"激活窗口"到 activate_window

**Given** 步骤描述为"激活 PyCharm 窗口"
**And** 没有显式指定 operation
**When** 系统解析该步骤
**Then** 应自动识别为 `activate_window` 操作
**And** 应提取"PyCharm"作为 window_name 参数

#### 场景：映射"打开文件"到 double_click_file

**Given** 步骤描述为"双击 main.py 文件"
**And** 没有显式指定 operation
**When** 系统解析该步骤
**Then** 应自动识别为 `double_click_file` 操作
**And** 应提取"main.py"作为 filename 参数

#### 场景：显式指定 operation 优先

**Given** 步骤描述为"打开文件"
**And** YAML 配置中指定 `operation: open_browser`
**When** 系统解析该步骤
**Then** 应使用显式指定的 `open_browser` 操作
**And** 不应使用自然语言推断的操作

#### 场景：无法识别的操作描述

**Given** 步骤描述为"执行某个未知操作"
**And** 没有显式指定 operation
**When** 系统解析该步骤
**Then** 验证时应返回警告
**And** 可能的操作列表应包含在错误信息中

---

### 需求：工作流验证

系统**必须**在执行前验证工作流配置的有效性。

#### 场景：验证有效的工作流

**Given** 工作流配置完整且有效
**When** 系统验证该工作流
**Then** 应返回验证通过
**And** 不应有错误信息

#### 场景：检测无效的操作名称

**Given** 步骤指定了不存在的操作名称
**When** 系统验证该工作流
**Then** 应返回验证失败
**And** 错误信息应说明哪个步骤的操作名称无效
**And** 应列出可用的操作名称

#### 场景：检测缺失的必需参数

**Given** 步骤指定了需要特定参数的操作
**And** 缺少必需参数
**When** 系统验证该工作流
**Then** 应返回验证失败
**And** 错误信息应说明缺少哪些参数

#### 场景：检测无效的重试配置

**Given** 步骤配置 `retry_count: -1`
**When** 系统验证该工作流
**Then** 应返回验证失败
**And** 错误信息应说明重试次数必须 >= 0

#### 场景：检测无效的条件表达式

**Given** 步骤配置无效的条件表达式
**When** 系统验证该工作流
**Then** 应返回验证失败
**And** 错误信息应说明条件表达式格式错误

---

### 需求：执行结果记录

系统**必须**详细记录工作流和每步的执行结果。

#### 场景：记录成功的步骤执行

**Given** 步骤执行成功
**When** 系统记录步骤结果
**Then** `StepResult.success` 应为 true
**And** 应包含执行时长
**And** `error_message` 应为 None

#### 场景：记录失败的步骤执行

**Given** 步骤执行失败
**When** 系统记录步骤结果
**Then** `StepResult.success` 应为 false
**And** `error_message` 应包含失败原因
**And** 应记录实际重试次数

#### 场景：记录跳过的步骤

**Given** 步骤因条件不满足被跳过
**When** 系统记录步骤结果
**Then** `StepResult.success` 应为 true（跳过不算失败）
**And** 应添加特殊标记说明该步骤被跳过

#### 场景：汇总工作流执行结果

**Given** 工作流包含 5 个步骤，3 个成功，2 个失败
**When** 系统汇总执行结果
**Then** `WorkflowResult.completed_steps` 应为 5
**And** `WorkflowResult.success` 应为 false
**And** `WorkflowResult.step_results` 应包含所有 5 个步骤的结果
**And** 应记录总执行时长

---

### 需求：自然语言命令集成

系统**必须**支持通过自然语言命令执行工作流。

#### 场景：通过"执行工作流 xxx.md"命令

**Given** 用户输入命令"执行工作流 deploy.md"
**When** 系统解析并执行该命令
**Then** 应加载 deploy.md 文件
**And** 应解析并执行工作流
**And** 应返回执行结果

#### 场景：通过"运行步骤 xxx"命令

**Given** 用户输入命令"运行步骤 打开浏览器"
**When** 系统解析并执行该命令
**Then** 应将"打开浏览器"作为单步工作流执行
**And** 应返回执行结果

#### 场景：工作流文件未找到

**Given** 用户输入命令"执行工作流 not_exist.md"
**And** 文件不存在
**When** 系统尝试执行该命令
**Then** 应返回失败状态
**And** 错误信息应说明文件未找到

#### 场景：工作流文件格式错误

**Given** 用户输入命令"执行工作流 invalid.md"
**And** 文件存在但格式无效
**When** 系统尝试执行该命令
**Then** 应返回失败状态
**And** 错误信息应说明格式问题

---

### 需求：错误处理与日志

系统**必须**提供完善的错误处理和日志记录。

#### 场景：记录工作流开始执行

**Given** 用户请求执行工作流
**When** 工作流开始执行
**Then** 应记录开始日志（包含工作流名称）
**And** 日志级别应为 INFO

#### 场景：记录每步执行状态

**Given** 工作流正在执行
**When** 每个步骤执行
**Then** 应记录步骤开始日志
**And** 应记录步骤完成日志（成功或失败）
**And** 日志应包含步骤索引和描述

#### 场景：记录工作流完成状态

**Given** 工作流执行完成
**When** 生成最终结果
**Then** 应记录完成日志
**And** 日志应包含总步骤数、成功数、失败数
**And** 日志应包含总执行时长

#### 场景：解析错误的友好提示

**Given** 工作流文档解析失败
**When** 返回错误信息
**Then** 错误信息应说明问题位置
**And** 应提供修复建议

#### 场景：执行错误的友好提示

**Given** 工作流执行失败
**When** 返回错误信息
**Then** 错误信息应说明失败步骤
**And** 应包含原始错误消息
**And** 应提供可能的解决方案

---

### 需求：Dry-Run 模式

系统**必须**支持仅验证不执行的 dry-run 模式。

#### 场景：Dry-run 验证有效工作流

**Given** 工作流配置有效
**And** 用户指定 `--dry-run` 选项
**When** 系统执行工作流
**Then** 应验证工作流配置
**And** 不应执行任何实际操作
**And** 应返回"验证通过"的结果

#### 场景：Dry-run 检测配置问题

**Given** 工作流配置有问题（如操作名无效）
**And** 用户指定 `--dry-run` 选项
**When** 系统执行工作流
**Then** 应返回配置错误
**And** 不应执行任何实际操作

#### 场景：Dry-run 输出执行计划

**Given** 工作流包含 3 个步骤
**And** 用户指定 `--dry-run` 选项
**When** 系统执行工作流
**Then** 应输出执行计划（将要执行的步骤列表）
**And** 不应执行任何实际操作

