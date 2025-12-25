# 架构设计文档：自然语言控制 PyCharm IDE 系统

## 1. 系统概述

本系统通过自然语言、计算机视觉和 GUI 自动化技术的结合，创建一个能够理解用户意图并自动操作 PyCharm IDE 的智能助手。

### 1.1 设计原则

1. **模块化**：各组件职责单一，接口清晰
2. **可扩展**：易于添加新的 IDE 支持和操作类型
3. **容错性**：多层级错误处理和恢复机制
4. **可观测**：完整的日志和调试信息
5. **安全性**：防止危险操作的误执行

---

## 2. 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                     用户接口层                           │
│  (CLI / 交互式界面 / API)                                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    编排层 (Orchestrator)                 │
│  - 命令处理流程编排                                      │
│  - 错误处理和恢复                                        │
│  - 状态管理                                              │
└─────────────────────────────────────────────────────────┘
        │               │               │               │
        ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  NLP 引擎    │ │  视觉引擎    │ │  自动化引擎  │ │  配置管理    │
│              │ │              │ │              │ │              │
│ - 意图识别   │ │ - 屏幕捕获   │ │ - 鼠标操作   │ │ - 操作配置   │
│ - 参数提取   │ │ - 元素检测   │ │ - 键盘操作   │ │ - 环境配置   │
│ - 上下文理解 │ │ - 坐标计算   │ │ - 序列编排   │ │ - 验证规则   │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
        │               │               │               │
        └───────────────┴───────────────┴───────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │      基础设施层       │
                    │  - 日志系统          │
                    │  - 缓存系统          │
                    │  - 工具函数          │
                    └──────────────────────┘
```

---

## 3. 核心组件设计

### 3.1 命令解析器 (CommandParser)

**职责**：将自然语言转换为结构化的操作指令

```python
class ParsedCommand:
    """解析后的命令结构"""
    intent: str           # 意图类型：open_file, rename, refactor
    action: str           # 具体操作
    parameters: dict      # 提取的参数
    confidence: float     # 置信度
    context: dict         # 上下文信息

class CommandParser:
    """自然语言命令解析器"""

    def parse(self, text: str, context: dict) -> ParsedCommand:
        """解析自然语言命令"""
        pass

    def validate(self, command: ParsedCommand) -> bool:
        """验证命令有效性"""
        pass
```

**意图分类**：
- **文件操作**：打开、关闭、保存、新建
- **编辑操作**：复制、粘贴、删除、重命名
- **导航操作**：跳转、查找、返回
- **重构操作**：重命名符号、提取方法、移动
- **运行操作**：运行、调试、测试

### 3.2 视觉定位器 (VisualLocator)

**职责**：通过视觉理解定位 UI 元素

```python
class UIElement:
    """UI 元素信息"""
    element_type: str      # 元素类型：button, menu, text_field
    description: str       # 描述
    bbox: Tuple[int, int, int, int]  # 边界框 (x1, y1, x2, y2)
    confidence: float      # 定位置信度

class VisualLocator:
    """视觉 UI 定位器"""

    def locate(self, prompt: str, screenshot: Image) -> List[UIElement]:
        """在截图中定位 UI 元素"""
        pass

    def verify(self, element: UIElement, screenshot: Image) -> bool:
        """验证元素位置"""
        pass
```

**定位策略**：
1. **主策略**：GLM-4V-Flash 视觉理解
2. **备用策略**：OCR 文本识别匹配
3. **回退策略**：配置文件中的固定坐标

### 3.3 自动化执行器 (AutomationExecutor)

**职责**：执行 GUI 操作

```python
class Action:
    """单个操作"""
    type: str             # click, drag, type, shortcut
    parameters: dict      # 操作参数
    timeout: float        # 超时时间
    retry: int            # 重试次数

class AutomationExecutor:
    """GUI 自动化执行器"""

    def execute(self, action: Action) -> bool:
        """执行单个操作"""
        pass

    def execute_sequence(self, actions: List[Action]) -> bool:
        """执行操作序列"""
        pass

    def verify_action(self, action: Action) -> bool:
        """验证操作结果"""
        pass
```

### 3.4 配置管理器 (ConfigManager)

**职责**：管理 IDE 操作配置

```python
class OperationConfig:
    """操作配置"""
    name: str
    aliases: List[str]           # 别名
    intent: str                  # 所属意图
    visual_prompt: str           # 视觉定位提示
    actions: List[Action]        # 操作序列
    preconditions: List[str]     # 前置条件
    post_check: str              # 后置检查

class ConfigManager:
    """配置管理器"""

    def load_config(self, path: str) -> dict:
        """加载配置文件"""
        pass

    def get_operation(self, name: str) -> OperationConfig:
        """获取操作配置"""
        pass

    def validate_config(self, config: dict) -> bool:
        """验证配置"""
        pass
```

---

## 4. 数据流设计

### 4.1 命令执行流程

```
用户输入
    │
    ▼
┌─────────────┐
│ 命令接收    │
└─────────────┘
    │
    ▼
┌─────────────┐     ┌─────────────┐
│ NLP 解析    │────→│ 参数验证    │
└─────────────┘     └─────────────┘
    │                     │ (失败)
    │ (成功)              ▼
    ▼              ┌─────────────┐
┌─────────────┐    │ 错误处理    │
│ 获取操作配置│    └─────────────┘
└─────────────┘
    │
    ▼
┌─────────────┐     ┌─────────────┐
│ 屏幕截图    │────→│ UI 元素定位 │
└─────────────┘     └─────────────┘
    │                     │
    │                     ▼
    │              ┌─────────────┐
    │              │ 坐标计算    │
    │              └─────────────┘
    │                     │
    ▼                     ▼
┌─────────────────────────────┐
│      操作执行（自动化）      │
│  - 鼠标移动到目标位置        │
│  - 执行点击/输入等操作       │
└─────────────────────────────┘
    │
    ▼
┌─────────────┐
│ 结果验证    │
└─────────────┘
    │
    ├─ 成功 ─→ 返回结果
    │
    └─ 失败 ─→ 重试/报错
```

### 4.2 错误处理流程

```
操作执行
    │
    ▼
┌─────────────┐
│ 操作是否成功│
└─────────────┘
    │
    ├─ 成功 ─→ 返回结果
    │
    └─ 失败
        │
        ▼
┌─────────────┐
│ 重试次数 < N │
└─────────────┘
    │
    ├─ 是 ─→ 重新定位元素 → 重新执行
    │
    └─ 否
        │
        ▼
┌─────────────┐
│ 尝试备用策略│
└─────────────┘
    │
    ├─ 成功 ─→ 返回结果
    │
    └─ 失败 ─→ 返回错误信息
```

---

## 5. 模块接口设计

### 5.1 主控制器接口

```python
class IDEController:
    """IDE 控制主控制器"""

    def __init__(self, config_path: str):
        """初始化控制器"""
        self.parser = CommandParser()
        self.locator = VisualLocator()
        self.executor = AutomationExecutor()
        self.config = ConfigManager().load_config(config_path)

    def execute_command(self, command: str) -> ExecutionResult:
        """执行自然语言命令"""
        # 1. 解析命令
        parsed = self.parser.parse(command, self.get_context())

        # 2. 获取操作配置
        op_config = self.config.get_operation(parsed.action)

        # 3. 定位 UI 元素
        screenshot = self.capture_screen()
        elements = self.locator.locate(op_config.visual_prompt, screenshot)

        # 4. 执行操作序列
        result = self.executor.execute_sequence(op_config.actions)

        # 5. 验证结果
        if result.success:
            return ExecutionResult(success=True, message="操作成功")
        else:
            return ExecutionResult(success=False, error=result.error)
```

### 5.2 插件接口设计

为支持扩展，设计插件接口：

```python
class IDEPlugin(Protocol):
    """IDE 插件接口"""

    def supports_ide(self, ide_name: str) -> bool:
        """是否支持该 IDE"""
        ...

    def get_operations(self) -> List[OperationConfig]:
        """获取支持的操作列表"""
        ...

    def customize_locator(self, locator: VisualLocator) -> VisualLocator:
        """自定义定位器"""
        ...
```

---

## 6. 配置文件结构

### 6.1 操作配置示例

```yaml
# operations/pycharm.yaml
ide: pycharm
version: ">=2023.2"

operations:
  - name: open_file
    aliases: [打开文件, open file, 打开]
    intent: file_operation
    description: 在 PyCharm 中打开指定文件

    visual_prompt: |
      在截图中找到以下元素：
      1. 项目工具窗口中的文件树
      2. 目标文件：{filename}

    actions:
      - type: click
        target: project_tree
        timeout: 2.0

      - type: type
        text: "{filename}"
        delay: 0.1

      - type: shortcut
        keys: ["enter"]
        timeout: 1.0

    post_check:
      type: verify_file_opened
      filename: "{filename}"

  - name: rename_symbol
    aliases: [重命名, rename, refactor_rename]
    intent: refactor
    description: 重命名当前光标位置的符号

    visual_prompt: |
      在截图中找到：
      1. 当前编辑器中光标位置
      2. 确认光标在符号上

    actions:
      - type: shortcut
        keys: ["shift", "f6"]
        timeout: 1.0

      - type: wait_for_dialog
        dialog_title: "Rename"

      - type: type
        text: "{new_name}"
        delay: 0.1

      - type: shortcut
        keys: ["enter"]
        timeout: 1.0

    requires_confirmation: true
```

### 6.2 主配置文件

```yaml
# config/main.yaml
system:
  log_level: INFO
  log_file: logs/ide_controller.log
  screenshot_dir: screenshots/

ide:
  name: pycharm
  config_path: operations/pycharm.yaml

api:
  zhipuai:
    api_key: ${ZHIPUAI_API_KEY}
    model: glm-4v-flash
    timeout: 30

automation:
  default_timeout: 5.0
  max_retries: 3
  retry_delay: 1.0
  action_delay: 0.2

safety:
  dangerous_operations:
    - delete_file
    - delete_folder
    - git_reset
  require_confirmation: true
  enable_undo: true
```

---

## 7. 技术选型理由

### 7.1 为什么选择视觉定位而非 IDE API

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| IDE API | 精确、快速 | IDE 特定、不通用 | ❌ |
| 辅助功能 API | 跨应用 | 复杂、权限问题 | ❌ |
| 视觉定位 | 通用、扩展性强 | 依赖 UI 稳定性 | ✅ |

**结论**：选择视觉定位作为主要方案，保留其他方案作为备用。

### 7.2 为什么选择云端 API

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 本地模型 | 无网络延迟 | 资源消耗大、精度较低 | ❌ |
| 云端 API | 高精度、省资源 | 网络依赖 | ✅ |

**结论**：使用云端 API，添加本地缓存优化性能。

---

## 8. 性能考虑

### 8.1 优化策略

1. **截图缓存**：避免重复截图
2. **定位结果缓存**：相同元素复用定位结果
3. **并行处理**：NLP 解析与截图并行
4. **增量捕获**：只捕获变化区域

### 8.2 性能目标

| 指标 | 目标值 |
|------|--------|
| 命令解析 | < 500ms |
| UI 定位 | < 2s |
| 操作执行 | < 1s |
| 端到端延迟 | < 5s |

---

## 9. 安全设计

### 9.1 操作分级

```python
class OperationRisk(Enum):
    """操作风险等级"""
    SAFE = "safe"              # 安全：查看、导航
    LOW = "low"                # 低风险：编辑
    MEDIUM = "medium"          # 中风险：重构
    HIGH = "high"              # 高风险：删除、覆盖
    CRITICAL = "critical"      # 严重：不可逆操作
```

### 9.2 安全机制

1. **操作确认**：中风险以上操作需确认
2. **操作审计**：记录所有操作日志
3. **紧急停止**：Ctrl+C 中断执行
4. **沙箱模式**：测试环境先行验证

---

## 10. 扩展性设计

### 10.1 添加新 IDE

1. 创建 IDE 配置文件
2. 实现 IDEPlugin 接口
3. 定义操作配置

### 10.2 添加新操作

1. 在配置文件中添加操作定义
2. 定义视觉提示词
3. 定义操作序列
4. 添加测试用例

---

## 11. 目录结构设计

```
ui-agent/
├── src/
│   ├── __init__.py
│   ├── main.py                 # 程序入口
│   │
│   ├── controller/             # 控制层
│   │   ├── __init__.py
│   │   └── ide_controller.py
│   │
│   ├── parser/                 # 命令解析
│   │   ├── __init__.py
│   │   ├── command_parser.py
│   │   └── intents.py
│   │
│   ├── locator/                # 视觉定位
│   │   ├── __init__.py
│   │   ├── visual_locator.py
│   │   ├── screenshot.py
│   │   └── element.py
│   │
│   ├── automation/             # 自动化执行
│   │   ├── __init__.py
│   │   ├── executor.py
│   │   └── actions.py
│   │
│   ├── config/                 # 配置管理
│   │   ├── __init__.py
│   │   ├── config_manager.py
│   │   └── schema.py
│   │
│   ├── infrastructure/         # 基础设施
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── cache.py
│   │   └── utils.py
│   │
│   └── models/                 # 数据模型
│       ├── __init__.py
│       ├── command.py
│       ├── element.py
│       └── result.py
│
├── config/
│   ├── main.yaml               # 主配置
│   └── operations/
│       └── pycharm.yaml        # PyCharm 操作配置
│
├── tests/
│   ├── test_parser.py
│   ├── test_locator.py
│   ├── test_executor.py
│   └── test_integration.py
│
├── logs/
├── screenshots/
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## 12. 未来改进方向

1. **多 IDE 支持**：扩展到 VS Code、IntelliJ IDEA
2. **学习机制**：从用户操作中学习优化
3. **语音输入**：支持语音命令
5. **云端同步**：配置和操作历史云端存储
