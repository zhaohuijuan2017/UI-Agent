# 规范：自然语言命令解析器

## 能力标识
`nl-command-parser`

## 依赖
无

## 新增需求

### 需求：命令意图识别

系统**必须**能够识别用户自然语言指令的操作意图，将输入分类到预定义的意图类别中。系统**应**支持文件操作、编辑操作、导航操作、重构操作和运行操作等至少五种意图类型。

#### 场景：识别文件操作意图

**前提条件**：用户输入自然语言命令

**输入**：`"打开 main.py 文件"`

**预期行为**：
- 系统分析输入文本
- 识别意图类型为 `file_operation`
- 识别具体操作为 `open`
- 提取参数：`{"filename": "main.py"}`

**输出**：`ParsedCommand(intent="file_operation", action="open", parameters={"filename": "main.py"}, confidence=0.95)`

#### 场景：识别重构操作意图

**前提条件**：用户输入重构相关命令

**输入**：`"把当前函数重命名为 calculate_total"`

**预期行为**：
- 系统识别意图类型为 `refactor`
- 识别具体操作为 `rename_symbol`
- 提取参数：`{"new_name": "calculate_total", "scope": "current_function"}`

**输出**：`ParsedCommand(intent="refactor", action="rename_symbol", parameters={"new_name": "calculate_total"}, confidence=0.92)`

#### 场景：识别导航操作意图

**前提条件**：用户输入导航相关命令

**输入**：`"跳转到第 42 行"`

**预期行为**：
- 系统识别意图类型为 `navigation`
- 识别具体操作为 `goto_line`
- 提取参数：`{"line_number": 42}`

**输出**：`ParsedCommand(intent="navigation", action="goto_line", parameters={"line_number": 42}, confidence=0.98)`

---

### 需求：参数提取

系统**必须**能够从自然语言命令中准确提取操作所需的结构化参数。参数提取**应**支持文件路径、行号范围、符号名称等多种参数类型。

#### 场景：提取文件路径参数

**前提条件**：命令中包含文件路径

**输入**：`"打开 src/models/user.py 文件"`

**预期行为**：
- 识别完整路径：`src/models/user.py`
- 识别文件名：`user.py`
- 识别目录：`src/models/`

**输出**：参数包含 `{"filepath": "src/models/user.py", "filename": "user.py", "directory": "src/models/"}`

#### 场景：提取行号范围参数

**前提条件**：命令中包含行号范围

**输入**：`"选中第 10 到 25 行"`

**预期行为**：
- 识别起始行号：`10`
- 识别结束行号：`25`
- 构建行号范围：`(10, 25)`

**输出**：参数包含 `{"line_start": 10, "line_end": 25}`

#### 场景：提取符号名称参数

**前提条件**：命令中包含类名、函数名等符号

**输入**：`"在 UserService 类中添加 login 方法"`

**预期行为**：
- 识别类名：`UserService`
- 识别方法名：`login`
- 识别操作类型：`add_method`

**输出**：参数包含 `{"class_name": "UserService", "method_name": "login", "operation": "add_method"}`

---

### 需求：命令上下文理解

系统**必须**能够利用当前上下文信息（当前文件、光标位置、IDE 状态）来解析不完整的命令。系统**应**支持相对路径解析和省略主语的命令理解。

#### 场景：基于当前文件解析相对路径

**前提条件**：
- 用户当前在 `src/main.py` 文件中
- 用户输入相对路径命令

**输入**：`"打开 ../config/settings.py"`

**上下文**：`{"current_file": "src/main.py"}`

**预期行为**：
- 解析相对路径
- 计算绝对路径：`config/settings.py`

**输出**：参数包含 `{"filepath": "config/settings.py", "resolved_path": "config/settings.py"}`

#### 场景：理解省略主语的命令

**前提条件**：
- 用户当前选中了一段文本
- 用户输入省略宾语的命令

**输入**：`"重命名为 new_name"`

**上下文**：`{"selection": {"start": 100, "end": 150, "text": "old_name"}}`

**预期行为**：
- 从上下文推断操作对象为当前选中文本
- 识别操作为重命名

**输出**：参数包含 `{"target": "selection", "new_name": "new_name", "old_name": "old_name"}`

---

### 需求：命令别名和模板支持

系统**必须**支持命令别名和预定义模板，使用户能够使用简短或习惯的表达方式。系统**应**为每个操作支持至少三个别名。

#### 场景：使用别名执行命令

**前提条件**：配置文件中定义了命令别名

**配置**：
```yaml
aliases:
  open: [打开, open, o]
  save: [保存, save]
  run: [运行, run, execute]
```

**输入**：`"o main.py"` 或 `"打开 main.py"`

**预期行为**：
- 识别别名 `o` 对应操作 `open`
- 执行与完整命令相同的解析逻辑

**输出**：`ParsedCommand(intent="file_operation", action="open", ...)`

#### 场景：使用命令模板填充参数

**前提条件**：配置文件中定义了命令模板

**配置**：
```yaml
templates:
  test_file:
    pattern: "测试 {filename}"
    intent: run
    action: run_test
```

**输入**：`"测试 user_service"`

**预期行为**：
- 匹配模板 `test_file`
- 提取填充参数 `{"filename": "user_service"}`
- 生成完整命令结构

**输出**：`ParsedCommand(intent="run", action="run_test", parameters={"filename": "user_service"})`

---

### 需求：命令验证

系统**必须**在解析后验证命令的有效性，包括参数完整性和业务规则检查。系统**应**检测必需参数缺失、参数类型错误和参数值超出范围等问题。

#### 场景：验证必需参数缺失

**前提条件**：命令解析完成

**输入**：`ParsedCommand(action="open_file", parameters={})`

**预期行为**：
- 检查 `open_file` 操作的必需参数
- 发现 `filename` 参数缺失
- 返回验证错误

**输出**：`{"valid": false, "errors": ["缺少必需参数: filename"]}`

#### 场景：验证参数值范围

**前提条件**：命令包含数值参数

**输入**：`ParsedCommand(action="goto_line", parameters={"line_number": -5})`

**预期行为**：
- 检查 `line_number` 参数值
- 验证值必须大于 0
- 返回验证错误

**输出**：`{"valid": false, "errors": ["行号必须大于 0"]}`

---

### 需求：置信度评估

系统**必须**为每个解析结果提供置信度评分，指示解析的可靠性。系统**应**在置信度低于阈值时请求用户确认，并提供替代解析建议。

#### 场景：高置信度解析

**前提条件**：命令表达清晰明确

**输入**：`"打开 main.py 文件"`

**预期行为**：
- 分析命令结构和语义
- 计算置信度评分
- 高置信度 (> 0.9)

**输出**：`ParsedCommand(confidence=0.96)`

#### 场景：低置信度解析需要确认

**前提条件**：命令表达模糊或歧义

**输入**：`"运行它"`

**预期行为**：
- 分析命令，发现指代不明
- 计算低置信度 (< 0.7)
- 返回解析结果并请求用户确认

**输出**：`ParsedCommand(confidence=0.45, needs_confirmation=true, suggestions=["运行当前文件", "运行测试"])`

---

## 数据模型

```python
@dataclass
class ParsedCommand:
    """解析后的命令"""
    intent: str                    # 意图类型
    action: str                    # 具体操作
    parameters: Dict[str, Any]     # 提取的参数
    confidence: float              # 置信度 (0-1)
    needs_confirmation: bool       # 是否需要用户确认
    suggestions: List[str]         # 建议的替代解析
    raw_input: str                 # 原始输入
    context: Dict[str, Any]        # 使用的上下文信息

@dataclass
class CommandContext:
    """命令执行上下文"""
    current_file: Optional[str]    # 当前文件路径
    cursor_position: Tuple[int, int]  # 光标位置 (行, 列)
    selection: Optional[Selection] # 当前选区
    ide_state: Dict[str, Any]      # IDE 状态信息
```

## API 接口

```python
class CommandParser:
    """命令解析器接口"""

    def parse(
        self,
        text: str,
        context: Optional[CommandContext] = None
    ) -> ParsedCommand:
        """解析自然语言命令

        Args:
            text: 用户输入的自然语言命令
            context: 当前上下文信息

        Returns:
            解析后的命令对象
        """
        pass

    def validate(
        self,
        command: ParsedCommand
    ) -> ValidationResult:
        """验证命令有效性

        Args:
            command: 解析后的命令

        Returns:
            验证结果
        """
        pass

    def register_template(
        self,
        name: str,
        pattern: str,
        intent: str,
        action: str
    ) -> None:
        """注册命令模板

        Args:
            name: 模板名称
            pattern: 模式字符串
            intent: 意图类型
            action: 具体操作
        """
        pass
```

## 验收标准

1. 能够识别至少 5 种主要意图类型（文件操作、编辑操作、导航操作、重构操作、运行操作）
2. 参数提取准确率 >= 90%
3. 置信度评分与实际准确性相关系数 >= 0.8
4. 支持至少 20 个命令别名
5. 解析响应时间 < 500ms
