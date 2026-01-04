# task-orchestration Specification

## Purpose
TBD - created by archiving change intent-based-task-orchestration. Update Purpose after archive.
## 需求
### 需求：意图识别

系统**必须**能够通过 LLM 分析用户的自然语言消息，识别任务意图并提取相关参数。

#### 场景：LLM 识别单场景意图-需求开发

**Given** 用户输入消息："帮我开发一个用户登录功能，需要支持微信扫码"
**And** 系统已配置预定义的意图类型列表
**When** 系统调用 LLM 分析该消息
**Then** LLM 应返回意图类型为 `develop-feature`
**And** 应提取参数：
  - `requirement_text`: `用户登录功能，需要支持微信扫码`
**And** 置信度应 >= 0.85
**And** LLM 应提供识别理由

#### 场景：LLM 识别单场景意图-需求查看

**Given** 用户输入消息："帮我查看 https://jira.example.com/PROJ-123 的需求详情"
**When** 系统调用 LLM 分析该消息
**Then** LLM 应返回意图类型为 `view-requirement`
**And** 应提取参数：
  - `url`: `https://jira.example.com/PROJ-123`
  - `requirement_id`: `PROJ-123`

#### 场景：LLM 识别组合场景意图-需求查看并开发

**Given** 用户输入消息："帮我看看 PROJ-123 这个需求，然后帮我实现它"
**And** 系统已配置预定义的意图类型列表
**When** 系统调用 LLM 分析该消息
**Then** LLM 应返回意图类型为 `requirement-to-development`
**And** 应提取参数：
  - `requirement_id`: `PROJ-123`
**And** 应推断 `url` 参数：`https://jira.example.com/PROJ-123`

#### 场景：LLM 处理模糊输入

**Given** 用户输入消息："开发登录"
**And** 消息信息不完整
**When** 系统调用 LLM 分析该消息
**Then** LLM 应返回最可能的意图类型 `develop-feature`
**And** 置信度应 < 0.85
**And** 系统**应该**向用户询问缺失的参数："请问您想开发什么样的登录功能？"

#### 场景：LLM 识别失败回退

**Given** 用户输入消息无法匹配任何预定义意图
**When** 系统调用 LLM 分析该消息
**Then** LLM 应返回 `unknown` 意图类型
**And** 系统**应该**提示用户："抱歉，我不理解您的请求，请提供更详细的描述"
**And** 系统**应该**提供可用意图类型列表供用户参考

#### 场景：动态更新意图定义

**Given** 开发者添加了新的意图类型 `deploy-to-production`
**And** 重新加载了意图定义
**When** 用户发送与部署相关的消息
**Then** LLM 应能识别新添加的意图类型
**And** 不需要重新训练模型

### 需求：任务流模板

系统**必须**支持预定义的任务流模板，模板描述跨系统的操作序列。

#### 场景：加载预定义模板

**Given** 存在预定义的"需求-开发"模板文件
**When** 系统加载该模板
**Then** 模板应包含以下步骤序列：
  1. 浏览器系统：打开需求页面
  2. 浏览器系统：提取需求信息
  3. 系统：切换到 PyCharm
  4. IDE 系统：调用开发插件
  5. IDE 系统：输入需求信息
**And** 每个步骤应定义目标系统、动作和参数

#### 场景：模板参数绑定

**Given** 意图参数为 `{url: "https://jira.example.com/PROJ-123", requirement_id: "PROJ-123"}`
**And** 模板步骤包含参数占位符 `{{intent.url}}`
**When** 系统执行模板绑定
**Then** 应自动替换占位符为实际值：`https://jira.example.com/PROJ-123`

### 需求：任务编排执行

系统**必须**能够自动编排和执行单系统任务或跨系统的任务序列。

#### 场景：单系统任务执行-IDE开发

**Given** 用户请求执行"需求开发"单场景任务
**When** 系统执行该任务
**Then** 系统应：
  1. 打开 PyCharm IDE
  2. 激活开发插件
  3. 将需求信息传入开发插件
  4. 开始代码生成

#### 场景：单系统任务执行-浏览器查看

**Given** 用户请求执行"需求查看"单场景任务
**When** 系统执行该任务
**Then** 系统应：
  1. 打开浏览器访问需求页面
  2. 提取并展示需求内容

#### 场景：跨系统任务执行

**Given** 用户请求执行"需求-开发"任务流
**When** 系统执行该任务流
**Then** 系统应：
  1. 在浏览器系统中打开需求页面
  2. 从页面提取需求信息（标题、描述、验收标准）
  3. 自动切换到 IDE 系统（PyCharm）
  4. 在 IDE 中激活开发插件
  5. 将需求信息注入到开发插件

#### 场景：系统间数据传递

**Given** 任务流包含步骤 1（浏览器提取数据）和步骤 2（IDE 使用数据）
**When** 系统执行步骤 1
**Then** 应将输出数据保存到 `context.shared_data["requirement"]`
**When** 系统执行步骤 2
**Then** 应从 `context.shared_data["requirement"]` 读取数据
**And** 应自动转换数据格式（如 HTML → 结构化 JSON）

#### 场景：执行异常处理

**Given** 任务流某步骤执行失败
**When** 系统检测到失败
**Then** 系统**应该**：
  - 记录失败步骤和原因
  - 执行回滚操作（撤销已执行的步骤）
  - 向用户报告错误详情
  - 提供重试选项

### 需求：执行上下文管理

系统**必须**维护任务执行的状态和数据上下文。

#### 场景：保存步骤结果

**Given** 任务流正在执行
**When** 每个步骤执行完成
**Then** 系统**必须**记录：
  - 步骤序号
  - 执行状态（成功/失败/跳过）
  - 输出数据
  - 执行时长

#### 场景：历史数据查询

**Given** 步骤 3 需要使用步骤 1 的输出数据
**When** 步骤 3 执行
**Then** 应能通过 `context.get_data("requirement")` 获取数据
**And** 返回值应包含步骤 1 提取的所有信息

### 需求：进度可视化

系统**必须**向用户展示任务执行的实时进度。

#### 场景：显示执行计划

**Given** 系统识别到用户意图并匹配到任务流模板
**When** 在开始执行前
**Then** 系统**应该**向用户展示执行计划：
  ```
  识别到意图：需求-开发
  执行计划：
    [1] 浏览器：打开需求页面
    [2] 浏览器：提取需求信息
    [3] 系统：切换到 PyCharm
    [4] IDE：启动开发插件
    [5] IDE：输入需求信息
    [6] IDE：开始开发
  ```
**And** 应提示用户确认执行

#### 场景：实时进度更新

**Given** 任务流正在执行
**When** 每个步骤完成
**Then** 应实时显示进度：
  ```
  执行中：
    [✓] 浏览器：打开需求页面 (0.5s)
    [✓] 浏览器：提取需求信息 (1.2s)
    [→] 系统：切换到 PyCharm... (执行中)
  ```

### 需求：系统适配器

系统**必须**提供统一的接口适配不同系统（浏览器、IDE、终端等）。

#### 场景：浏览器系统适配

**Given** 系统需要调用浏览器功能
**When** 调用 `BrowserSystemAdapter.execute(action="open", params={url: "..."})`
**Then** 应执行对应的浏览器自动化操作
**And** 应返回 `StepResult` 包含执行状态和输出数据

#### 场景：IDE 系统适配

**Given** 系统需要调用 IDE 功能
**When** 调用 `IDESystemAdapter.execute(action="input", params={text: "..."})`
**Then** 应执行对应的 IDE 操作
**And** 应支持数据注入（如输入框、剪贴板）

### 需求：可扩展性

系统**必须**支持用户通过配置文件自定义意图和任务流模板。

#### 场景：通过 YAML 注册自定义意图

**Given** 开发者需要在 `config/intent_definitions.yaml` 中添加新意图类型
**When** 添加以下配置：
```yaml
intents:
  custom-deploy:
    type: "composite"
    description: "自定义部署流程"
    systems: ["terminal", "browser"]
    parameters:
      target_url:
        type: "string"
        required: true
```
**And** 重新加载意图定义
**Then** 新意图应能被识别器识别
**And** LLM 应能匹配到该意图类型

#### 场景：创建自定义模板

**Given** 开发者需要定义新的任务流
**When** 创建 YAML 文件 `custom-deploy.yaml`
**Then** 系统应能加载和使用该模板

**Example**：
```yaml
name: "自定义部署"
intent_types: ["custom-deployment"]
steps:
  - system: terminal
    action: run
    parameters:
      command: "npm run build"
  - system: browser
    action: upload
    parameters:
      url: "{{deployment.target_url}}"
```

