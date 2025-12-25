# 规范：IDE 操作配置

## 能力标识
`ide-operation-config`

## 依赖
无

## 新增需求

### 需求：操作配置定义

系统**必须**支持通过配置文件定义 IDE 操作，包括操作的视觉定位规则和执行步骤。系统**应**为 PyCharm 支持至少 20 种常用操作。

#### 场景：定义文件打开操作

**前提条件**：创建配置文件

**输入**：
```yaml
operations:
  - name: open_file
    aliases: [打开文件, open file, 打开]
    intent: file_operation
    description: 在 IDE 中打开指定文件

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

      - type: key
        key: enter
        timeout: 1.0

    post_check:
      type: verify_file_opened
      filename: "{filename}"
```

**预期行为**：
- 配置文件被成功加载
- 操作可通过名称 `open_file` 访问
- 支持的别名都被识别

**输出**：配置在内存中可用，操作列表包含 `open_file`

#### 场景：定义重构操作

**前提条件**：配置系统已初始化

**输入**：
```yaml
operations:
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
        timeout: 2.0

      - type: type
        text: "{new_name}"
        delay: 0.1

      - type: key
        key: enter
        timeout: 1.0

    requires_confirmation: true
```

**预期行为**：
- 配置被解析为 `OperationConfig` 对象
- `requires_confirmation` 标志被正确识别

**输出**：`OperationConfig(name="rename_symbol", requires_confirmation=True, ...)`

---

### 需求：参数化操作配置

系统**必须**支持操作配置中的参数替换，使同一配置可处理不同的输入值。参数替换准确率**必须**达到 100%。

#### 场景：替换文件名参数

**前提条件**：配置文件中定义了参数占位符

**输入**：
```python
config = OperationConfig(
    actions=[
        Action(type="type", text="{filename}"),
        Action(type="key", key="enter")
    ]
)
parameters = {"filename": "main.py"}
```

**预期行为**：
- 扫描操作中的参数占位符
- 用实际值替换 `{filename}`
- 生成可执行的操作序列

**输出**：
```python
[
    Action(type="type", text="main.py"),
    Action(type="key", key="enter")
]
```

#### 场景：替换多个参数

**前提条件**：配置包含多个不同参数

**输入**：
```python
config = OperationConfig(
    visual_prompt="找到类 {class_name} 中的方法 {method_name}",
    actions=[
        Action(type="shortcut", keys=["ctrl", "{shortcut_key}"]),
        Action(type="type", text="{new_name}")
    ]
)
parameters = {
    "class_name": "UserService",
    "method_name": "login",
    "shortcut_key": "f6",
    "new_name": "authenticate"
}
```

**预期行为**：
- 替换视觉提示词中的参数
- 替换操作序列中的参数
- 所有占位符都被正确处理

**输出**：所有参数都已替换的配置

---

### 需求：操作别名管理

系统**必须**支持为操作定义多个别名，使用户可以使用不同的表达方式。系统**应**在配置验证时检测并报告别名冲突。

#### 场景：通过别名访问操作

**前提条件**：操作配置了多个别名

**输入**：
```yaml
operation:
  name: save_file
  aliases: [保存, save, 保存文件, save file]
```

**查询**：`get_operation("保存")`

**预期行为**：
- 搜索别名映射
- 找到对应的操作 `save_file`
- 返回操作配置

**输出**：`OperationConfig(name="save_file", ...)`

#### 场景：别名冲突处理

**前提条件**：两个操作使用了相同的别名

**输入**：
```yaml
operations:
  - name: open_file
    aliases: [打开, open]

  - name: open_folder
    aliases: [打开, open folder]
```

**预期行为**：
- 配置验证时检测到冲突
- 返回验证错误
- 指出冲突的别名

**输出**：`ValidationError("别名冲突: '打开' 被多个操作使用")`

---

### 需求：条件操作配置

系统**必须**支持基于条件执行不同的操作序列。系统**应**支持默认条件分支（当所有条件都不满足时使用）。

#### 场景：基于文件类型的不同操作

**前提条件**：配置了条件分支

**输入**：
```yaml
operation:
  name: open_file
  conditional_actions:
    - condition: "{file_extension} == '.py'"
      actions:
        - type: shortcut
          keys: ["ctrl", "shift", "a"]

    - condition: "{file_extension} == '.md'"
      actions:
        - type: shortcut
          keys: ["ctrl", "shift", "m"]
```

**参数**：`{"file_extension": ".py"}`

**预期行为**：
- 评估条件表达式
- 匹配第一个满足条件的分支
- 执行对应的操作序列

**输出**：执行 Python 文件专用的打开操作

#### 场景：默认条件分支

**前提条件**：配置了默认处理

**输入**：
```yaml
operation:
  conditional_actions:
    - condition: "{has_error}"
      actions: [...]
    - condition: null  # 默认分支
      actions: [...]
```

**预期行为**：
- 尝试匹配所有条件
- 没有条件满足时使用默认分支
- 执行默认操作

**输出**：执行默认操作序列

---

### 需求：操作风险分级

系统**必须**支持为操作分配风险等级，用于安全控制。系统**应**对中风险以上的操作自动触发确认流程，并**必须**记录所有高风险操作到审计日志。

#### 场景：定义高风险操作

**前提条件**：配置了操作风险等级

**输入**：
```yaml
operation:
  name: delete_file
  risk_level: high
  aliases: [删除文件, delete file]

  actions:
    - type: shortcut
      keys: ["ctrl", "alt", "delete"]

    - type: wait_for_dialog
      timeout: 1.0

    - type: key
      key: enter
```

**预期行为**：
- 操作被标记为高风险
- 执行前自动触发确认流程
- 记录到操作审计日志

**输出**：用户确认后执行，操作被记录

#### 场景：安全操作无需确认

**前提条件**：操作风险等级为 safe

**输入**：
```yaml
operation:
  name: goto_line
  risk_level: safe
  actions: [...]
```

**预期行为**：
- 直接执行操作
- 无需用户确认
- 不记录到高风险日志

**输出**：操作直接执行

---

### 需求：配置验证

系统**必须**在加载配置时验证其完整性和正确性。系统**应**检测至少 90% 的常见配置错误，包括缺少字段、类型错误和无效值。

#### 场景：验证必需字段

**前提条件**：加载配置文件

**输入**：
```yaml
operation:
  name: save_file
  # 缺少 'actions' 字段
```

**预期行为**：
- 检测到缺少必需字段 `actions`
- 返回详细的验证错误
- 指出缺失的字段名称

**输出**：`ValidationError("缺少必需字段: actions")`

#### 场景：验证操作类型

**前提条件**：配置中定义了操作

**输入**：
```yaml
actions:
  - type: invalid_action_type
    parameters: {...}
```

**预期行为**：
- 检查操作类型是否在支持列表中
- 发现 `invalid_action_type` 不存在
- 返回验证错误

**输出**：`ValidationError("不支持的操作类型: invalid_action_type")`

#### 场景：验证参数格式

**前提条件**：操作定义了参数

**输入**：
```yaml
actions:
  - type: click
    parameters:
      x: "not_a_number"  # 应该是数字
      y: 100
```

**预期行为**：
- 验证参数类型
- 发现 `x` 应为数字但提供了字符串
- 返回格式错误

**输出**：`ValidationError("参数格式错误: x 应为整数")`

---

### 需求：配置热更新

系统**必须**支持在运行时重新加载配置，无需重启程序。配置重载失败时**应**保持旧配置继续使用。

#### 场景：修改配置后重新加载

**前提条件**：系统正在运行

**输入**：
- 用户修改了 `operations/pycharm.yaml`
- 触发配置重载

**预期行为**：
- 检测配置文件变化
- 解析新配置
- 验证新配置
- 替换内存中的配置
- 不影响正在执行的操作

**输出**：`{"success": true, "operations_updated": 25}`

#### 场景：配置重载失败保持旧配置

**前提条件**：新配置有错误

**输入**：
- 修改配置文件时引入语法错误
- 尝试重载

**预期行为**：
- 解析新配置失败
- 捕获错误信息
- 保持旧配置继续使用
- 返回错误详情

**输出**：`{"success": false, "error": "...", "using_previous_config": true}`

---

### 需求：多 IDE 配置支持

系统**必须**支持为不同 IDE 维护独立的操作配置。系统**应**支持至少 3 种 IDE（PyCharm、VS Code、IntelliJ IDEA）的独立配置。

#### 场景：切换 IDE 配置

**前提条件**：配置目录包含多个 IDE 的配置

**输入**：
```
config/
  operations/
    pycharm.yaml
    vscode.yaml
    idea.yaml
```

**切换命令**：`switch_ide("vscode")`

**预期行为**：
- 卸载当前 IDE 配置
- 加载 `vscode.yaml`
- 更新可用操作列表
- 适配 IDE 特定的视觉提示

**输出**：`{"success": true, "current_ide": "vscode", "operations_count": 20}`

#### 场景：IDE 特定参数

**前提条件**：不同 IDE 有不同的快捷键

**输入**：
```yaml
# pycharm.yaml
actions:
  - type: shortcut
    keys: ["ctrl", "shift", "f10"]

# vscode.yaml
actions:
  - type: shortcut
    keys: ["ctrl", "f5"]
```

**预期行为**：
- 根据当前 IDE 加载对应配置
- 使用正确的快捷键

**输出**：针对当前 IDE 的正确操作

---

## 数据模型

```python
@dataclass
class OperationConfig:
    """操作配置"""
    name: str                              # 操作名称
    aliases: List[str]                     # 别名列表
    intent: str                            # 所属意图类别
    description: str                       # 操作描述
    visual_prompt: str                     # 视觉定位提示词
    actions: List[Action]                  # 操作序列
    conditional_actions: Optional[List[ConditionalAction]]  # 条件操作
    preconditions: List[str]               # 前置条件
    post_check: Optional[Dict]             # 后置检查
    risk_level: str = "low"                # 风险等级
    requires_confirmation: bool = False    # 是否需要确认
    timeout: float = 5.0                   # 默认超时

@dataclass
class ConditionalAction:
    """条件操作"""
    condition: Optional[str]               # 条件表达式（None 表示默认）
    actions: List[Action]                  # 操作序列

@dataclass
class IDEConfig:
    """IDE 配置"""
    ide_name: str                          # IDE 名称
    version_requirement: Optional[str]     # 版本要求
    operations: List[OperationConfig]      # 操作列表
    global_shortcuts: Dict[str, List[str]]  # 全局快捷键映射
    visual_context: Dict[str, str]         # 视觉上下文提示
```

## API 接口

```python
class ConfigManager:
    """配置管理器接口"""

    def load_config(self, path: str) -> IDEConfig:
        """加载 IDE 配置

        Args:
            path: 配置文件路径

        Returns:
            IDE 配置对象
        """
        pass

    def get_operation(self, name: str) -> Optional[OperationConfig]:
        """根据名称或别名获取操作

        Args:
            name: 操作名称或别名

        Returns:
            操作配置，如果不存在则返回 None
        """
        pass

    def get_operations_by_intent(self, intent: str) -> List[OperationConfig]:
        """获取指定意图的所有操作

        Args:
            intent: 意图类别

        Returns:
            操作列表
        """
        pass

    def validate_config(self, config: IDEConfig) -> ValidationResult:
        """验证配置

        Args:
            config: 要验证的配置

        Returns:
            验证结果
        """
        pass

    def reload_config(self) -> bool:
        """重新加载当前配置

        Returns:
            是否成功
        """
        pass

    def switch_ide(self, ide_name: str) -> bool:
        """切换到指定 IDE 的配置

        Args:
            ide_name: IDE 名称

        Returns:
            是否成功
        """
        pass

    def resolve_parameters(
        self,
        config: OperationConfig,
        parameters: Dict[str, Any]
    ) -> OperationConfig:
        """解析配置中的参数

        Args:
            config: 包含占位符的配置
            parameters: 参数值

        Returns:
            参数已解析的配置
        """
        pass
```

## 配置文件结构

```
config/
├── main.yaml                    # 主配置文件
└── operations/
    ├── pycharm.yaml             # PyCharm 操作配置
    ├── vscode.yaml              # VS Code 操作配置
    └── idea.yaml                # IntelliJ IDEA 配置
```

## 验收标准

1. 支持至少 20 种 PyCharm 常用操作
2. 配置加载响应时间 < 100ms
3. 配置验证能检测 90% 的常见错误
4. 支持配置热更新
5. 参数替换准确率 100%
6. 支持 3+ IDE 的独立配置
