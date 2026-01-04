# 架构设计：意图驱动的任务流编排系统

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户消息                             │
│              "帮我查看需求 PROJ-123 并开发"                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    IntentRecognizer                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. 分词和关键词提取                                   │   │
│  │  2. 意图模式匹配                                       │   │
│  │  3. 参数提取（URL、ID、文件名等）                       │   │
│  │  4. 置信度计算                                         │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    Intent { type: "requirement-to-development",
                            parameters: { url: "...", project: "PROJ-123" } }
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   TaskOrchestrator                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. 意图到模板匹配                                     │   │
│  │  2. 模板参数绑定                                       │   │
│  │  3. 步骤编排                                           │   │
│  │  4. 执行监控                                           │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    TaskFlowTemplate {
                      steps: [
                        { system: "browser", action: "open", params: {...} },
                        { system: "browser", action: "extract", params: {...} },
                        { system: "ide", action: "switch", params: {...} },
                        { system: "ide", action: "develop", params: {...} }
                      ]
                    }
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   ExecutionContext                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  - shared_data: { requirement: {...} }               │   │
│  │  - execution_history: [...]                          │   │
│  │  - current_step: 2                                   │   │
│  │  - status: "running"                                 │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Browser  │    │   IDE    │    │ Terminal │
    │  System  │    │  System  │    │  System  │
    └──────────┘    └──────────┘    └──────────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                    Step Results
```

## 核心组件设计

### 1. IntentRecognizer（意图识别器）

#### 职责
- 解析用户消息
- 识别任务意图
- 提取关键参数

#### 接口设计
```python
class IntentRecognizer:
    def recognize(self, message: str) -> IntentMatchResult:
        """识别消息意图"""
        pass

    def register_pattern(self, pattern: IntentPattern):
        """注册意图模式"""
        pass
```

#### 意图定义文件格式

**YAML 格式示例**（`config/intent_definitions.yaml`）：
```yaml
intents:
  develop-feature:
    type: "single-system"  # 单系统意图
    description: "需求开发（仅 IDE）"
    system: "ide"
    parameters:
      requirement_text:
        type: "string"
        description: "需求文本内容"\
          
        required: true
        examples:
          - "用户登录需要支持微信扫码"
          - "实现购物车结算功能"

  view-requirement:
    type: "single-system"  # 单系统意图
    description: "需求查看（仅浏览器）"
    system: "browser"
    parameters:
      url:
        type: "string"
        description: "需求链接"
        required: true
        pattern: "https?://\\S+"
      requirement_id:
        type: "string"
        description: "需求编号"
        required: false
        pattern: "[A-Z]+-\\d+"

  requirement-to-development:
    type: "composite"  # 组合意图（跨系统）
    description: "需求查看并开发"
    systems: ["browser", "ide"]
    parameters:
      url:
        type: "string"
        description: "需求链接"
        required: true
      requirement_id:
        type: "string"
        description: "需求编号"
        required: false
```

**LLM 使用此定义文件**：
1. 系统启动时加载意图定义
2. 构建提示词时包含所有意图类型及其说明
3. LLM 根据定义识别意图并提取参数
4. 新增意图时只需更新 YAML 文件

### 2. TaskOrchestrator（任务编排器）

#### 职责
- 匹配意图到模板
- 编排任务执行顺序
- 管理执行上下文
- 处理异常和回滚

#### 执行流程
```python
def orchestrate(self, intent: Intent, context: ExecutionContext):
    # 1. 匹配模板
    template = self.template_matcher.match(intent)

    # 2. 绑定参数
    bound_template = self.bind_parameters(template, intent.parameters)

    # 3. 执行步骤
    for step in bound_template.steps:
        if not self.should_execute(step, context):
            continue

        result = self.execute_step(step, context)
        context.save_result(step, result)

        if not result.success and not step.continue_on_error:
            return self.handle_failure(context, step)

    return context.get_final_result()
```

### 3. SystemBridge（系统桥接）

#### 设计目标
- 统一不同系统的操作接口
- 处理数据格式转换
- 管理系统状态

#### 接口设计
```python
class SystemAdapter(Protocol):
    def execute(self, action: str, params: dict) -> StepResult:
        """执行系统动作"""
        pass

    def extract_data(self, query: str) -> dict:
        """从系统提取数据"""
        pass

    def inject_data(self, data: dict) -> bool:
        """向系统注入数据"""
        pass
```

#### 适配器实现
```python
class BrowserSystemAdapter:
    def execute(self, action: str, params: dict):
        if action == "open":
            return self.browser_automation.get_page(params["url"])
        elif action == "extract":
            return self.extract_content(params["selector"])

    def extract_data(self, query: str):
        # 从当前页面提取数据
        pass

class IDESystemAdapter:
    def execute(self, action: str, params: dict):
        if action == "switch":
            return self.ide_controller.activate_window(params["window"])
        elif action == "develop":
            return self.invoke_development_plugin(params["requirements"])

    def inject_data(self, data: dict):
        # 向 IDE 注入数据
        pass
```

### 4. 数据流设计

#### 上下文数据传递
```python
class ExecutionContext:
    def __init__(self):
        self.shared_data: dict = {}
        self.step_results: list = []

    def get_data(self, key: str, default=None):
        """获取共享数据"""
        return self.shared_data.get(key, default)

    def set_data(self, key: str, value: any):
        """设置共享数据"""
        self.shared_data[key] = value

    def save_step_result(self, step: TemplateStep, result: StepResult):
        """保存步骤结果"""
        self.step_results.append({
            "step": step,
            "result": result,
            "timestamp": datetime.now()
        })
```

#### 步骤间数据依赖
```yaml
# 示例模板
steps:
  - system: browser
    action: extract_requirements
    output_to: requirements  # 将结果保存到 context.shared_data["requirements"]

  - system: ide
    action: develop_from_requirements
    input_from: requirements  # 从 context.shared_data["requirements"] 读取
```

## 关键设计决策

### 1. 为什么不用现有的 WorkflowExecutor？

**现有 WorkflowExecutor**：
- 预定义的 Markdown 文档
- 用户手动编写步骤
- 适合固定流程

**新的 TaskOrchestrator**：
- 意图驱动的动态编排
- 自动选择最佳模板
- 支持参数提取和绑定
- 跨系统数据传递

**关系**：TaskOrchestrator 可以生成 WorkflowConfig，复用 WorkflowExecutor

### 2. 意图识别策略

**方案对比**：

| 策略 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 基于规则 | 简单、可控、可解释 | 覆盖率有限、维护成本高 | ❌ |
| LLM 分类 | 灵活、泛化能力强、语义理解准确 | 成本较低、延迟可接受 | ✅ 采用 |
| 混合模式 | 平衡准确性和成本 | 复杂度高 | ⏰ 备选 |

**采用 LLM 进行意图识别**：
- 分析用户消息的语义，而非简单关键词匹配
- 自动匹配到预定义的意图类型
- 提取意图所需的参数
- 支持自然语言的各种表达方式

**LLM 意图识别流程**：
```python
def recognize_with_llm(self, message: str) -> IntentMatchResult:
    # 1. 构建提示词，包含所有预定义意图类型
    prompt = self._build_intent_prompt(message, self.intents)

    # 2. 调用 LLM 分析
    response = self.llm_client.chat([
        {
            "role": "system",
            "content": "你是一个意图识别助手，负责分析用户消息并匹配到预定义的意图类型。"
        },
        {
            "role": "user",
            "content": prompt
        }
    ])

    # 3. 解析 LLM 返回的意图和参数
    return self._parse_intent_response(response)
```

**提示词示例**：
```
请分析以下用户消息，匹配到最合适的意图类型并提取参数。

用户消息："{message}"

可用的意图类型：
1. develop-feature - 需求开发（单系统）
   说明：用户想开发某个功能，消息中包含需求描述
   参数：requirement_text（需求文本内容）

2. view-requirement - 需求查看（单系统）
   说明：用户想查看某个需求详情
   参数：url（需求链接）、requirement_id（需求编号）

3. requirement-to-development - 需求查看并开发（跨系统）
   说明：用户想先查看需求，然后基于需求进行开发
   参数：url（需求链接）、requirement_id（需求编号）

请以 JSON 格式返回：
{
  "intent_type": "意图类型",
  "confidence": 0.95,
  "parameters": {
    "参数名": "参数值"
  },
  "reasoning": "识别理由"
}
```

### 3. 单场景 vs 组合场景

**设计原则**：
- **优先单场景**：每个意图类型对应一个最小可执行单元
- **支持组合**：多个单场景可以组合成复杂流程
- **统一接口**：单场景和组合场景使用相同的模板系统

**单场景模板示例**：
```yaml
# 单场景：需求开发（仅 IDE）
name: "develop-feature"
intent_types: ["develop-feature"]
steps:
  - system: ide
    action: switch
    parameters:
      window: "PyCharm"
  - system: ide
    action: develop
    parameters:
      requirement: "{{intent.requirement_text}}"
```

**组合场景模板示例**：
```yaml
# 组合场景：需求查看+开发
name: "requirement-to-development"
intent_types: ["requirement-to-development"]
steps:
  - system: browser
    action: open
    parameters:
      url: "{{intent.url}}"
  - system: browser
    action: extract
    output_to: requirement_data
  - system: ide
    action: switch
    parameters:
      window: "PyCharm"
  - system: ide
    action: develop
    input_from: requirement_data
```

**关系**：
- 组合场景 = 多个单场景的顺序执行
- 单场景可独立使用，也可作为组合场景的子步骤
- 系统自动识别单场景或组合场景意图

### 4. 系统切换机制

**挑战**：
- 不同系统有不同的操作接口
- 数据格式不一致
- 状态同步问题

**解决方案**：
- 统一的 SystemAdapter 协议
- 数据格式转换层
- 中央化的 ExecutionContext

### 5. 错误处理策略

```python
class ExecutionStrategy(Enum):
    FAIL_FAST = "fail_fast"        # 失败立即停止
    CONTINUE_ON_ERROR = "continue"  # 继续执行
    ROLLBACK = "rollback"          # 回滚已执行步骤
    RETRY = "retry"                # 重试当前步骤
```

## 扩展性设计

### 添加新意图类型
```python
# 1. 定义意图模式
pattern = IntentPattern(
    type="deploy-to-production",
    keywords=["部署", "生产环境"],
    regex=r"部署.*到.*生产"
)

# 2. 注册识别器
recognizer.register_pattern(pattern)

# 3. 创建任务流模板
template = TaskFlowTemplate(
    name="deploy-to-prod",
    intent_types=["deploy-to-production"],
    steps=[...]
)

# 4. 注册模板
template_engine.register(template)
```

### 添加新系统支持
```python
# 实现系统适配器
class CustomSystemAdapter:
    def execute(self, action, params):
        # 实现具体逻辑
        pass

    def extract_data(self, query):
        pass

    def inject_data(self, data):
        pass

# 注册适配器
orchestrator.register_system("custom", CustomSystemAdapter())
```

## 性能考虑

### 意图识别缓存
```python
@lru_cache(maxsize=1000)
def recognize(self, message: str):
    # 缓存常见消息的识别结果
    pass
```

### 并行执行
```python
# 某些步骤可以并行执行
parallel_steps = [
    {system: "browser", action: "open", url: "..."},
    {system: "ide", action: "open_project"}
]
# 等待所有步骤完成
await asyncio.gather(*[execute(s) for s in parallel_steps])
```

## 安全考虑

1. **权限验证**：某些操作需要用户确认
2. **沙箱执行**：限制系统操作的范围
3. **审计日志**：记录所有跨系统操作
4. **敏感数据处理**：不记录敏感信息（密码、token等）

## 技术债务和未来改进

1. **增强意图识别**：引入 LLM 提高准确率
2. **可视化编辑器**：图形化模板编辑器
3. **性能优化**：并行执行、预测性加载
4. **智能推荐**：基于历史推荐任务流
