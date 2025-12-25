# 规范：GUI 自动化执行器

## 能力标识
`gui-automation-executor`

## 依赖
- `visual-ui-locator`（用于获取目标元素坐标）

## 新增需求

### 需求：鼠标操作执行

系统**必须**能够执行各种鼠标操作，包括点击、双击、右键点击和拖拽。鼠标操作成功率**必须**达到 98% 以上。

#### 场景：执行单击操作

**前提条件**：已获取目标元素坐标

**输入**：
```python
Action(
    type="click",
    parameters={"x": 500, "y": 300, "button": "left"}
)
```

**预期行为**：
- 将鼠标移动到目标坐标
- 执行左键单击
- 添加短暂延迟确保操作完成

**输出**：`{"success": true, "executed_at": "timestamp"}`

#### 场景：执行双击操作

**前提条件**：需要双击触发的元素

**输入**：
```python
Action(
    type="double_click",
    parameters={"x": 500, "y": 300}
)
```

**预期行为**：
- 移动鼠标到目标位置
- 执行快速双击（间隔 < 200ms）
- 等待双击效果生效

**输出**：`{"success": true}`

#### 场景：执行右键菜单操作

**前提条件**：需要打开上下文菜单

**输入**：
```python
Action(
    type="click",
    parameters={"x": 500, "y": 300, "button": "right"}
)
```

**预期行为**：
- 移动鼠标到目标位置
- 执行右键单击
- 等待菜单展开

**输出**：`{"success": true, "menu_opened": true}`

#### 场景：执行拖拽操作

**前提条件**：需要拖拽的元素和目标位置

**输入**：
```python
Action(
    type="drag",
    parameters={
        "start": (400, 300),
        "end": (600, 300),
        "duration": 0.5
    }
)
```

**预期行为**：
- 移动鼠标到起始位置
- 按下鼠标左键
- 平滑移动到目标位置（模拟人类拖拽速度）
- 释放鼠标

**输出**：`{"success": true, "dragged": true}`

---

### 需求：键盘操作执行

系统**必须**能够执行各种键盘操作，包括文本输入和快捷键。键盘操作成功率**必须**达到 99% 以上。系统**应**正确处理特殊字符和组合键。

#### 场景：输入文本

**前提条件**：已定位到文本输入框

**输入**：
```python
Action(
    type="type",
    parameters={"text": "Hello, World!", "delay": 0.05}
)
```

**预期行为**：
- 逐字符输入文本
- 每个字符之间添加指定延迟
- 正确处理特殊字符（空格、标点）

**输出**：`{"success": true, "characters_typed": 13}`

#### 场景：执行快捷键

**前提条件**：需要触发 IDE 快捷键

**输入**：
```python
Action(
    type="shortcut",
    parameters={"keys": ["ctrl", "s"]}
)
```

**预期行为**：
- 同时按下 Ctrl 和 S 键
- 等待短暂延迟
- 释放所有键

**输出**：`{"success": true, "shortcut_triggered": "ctrl+s"}`

#### 场景：执行组合快捷键

**前提条件**：需要多键组合

**输入**：
```python
Action(
    type="shortcut",
    parameters={"keys": ["shift", "ctrl", "f6"]}
)
```

**预期行为**：
- 同时按下 Shift、Ctrl 和 F6
- 保持按键状态
- 按相反顺序释放

**输出**：`{"success": true}`

#### 场景：模拟特殊按键

**前提条件**：需要使用特殊功能键

**输入**：
```python
Action(
    type="key",
    parameters={"key": "enter"}
)
```

**预期行为**：
- 按下 Enter 键
- 立即释放

**输出**：`{"success": true}`

---

### 需求：操作序列编排

系统**必须**能够按照顺序执行多个操作，并处理操作之间的依赖关系。操作序列成功率**应**达到 95% 以上。系统**应**在某个步骤失败时停止执行并返回详细错误信息。

#### 场景：执行打开文件操作序列

**前提条件**：已解析打开文件命令

**输入**：
```python
actions = [
    Action(type="click", parameters={"target": "project_tree"}),
    Action(type="type", parameters={"text": "main.py"}),
    Action(type="key", parameters={"key": "enter"}),
]
```

**预期行为**：
1. 点击项目树区域
2. 等待焦点转移
3. 输入文件名进行搜索
4. 按回车打开文件

**输出**：
```python
{
    "success": true,
    "results": [
        {"action": 0, "success": true},
        {"action": 1, "success": true},
        {"action": 2, "success": true}
    ],
    "total_time": 2.5
}
```

#### 场景：操作序列中某个步骤失败

**前提条件**：执行过程中某个元素未找到

**输入**：包含 5 个步骤的操作序列

**预期行为**：
- 执行步骤 1、2 成功
- 步骤 3 失败（元素未找到）
- 停止执行后续步骤
- 返回部分执行结果和错误信息

**输出**：
```python
{
    "success": false,
    "completed_steps": 2,
    "failed_at": 2,
    "error": "元素未找到: save_button"
}
```

---

### 需求：操作前验证

系统**必须**在执行操作前验证前置条件，避免无效操作。系统**应**验证元素存在性、可视范围和可交互状态。

#### 场景：验证元素存在性

**前提条件**：准备执行点击操作

**输入**：目标元素 "run_button"

**预期行为**：
- 调用视觉定位器验证元素存在
- 检查元素在可视范围内
- 验证元素可交互（非禁用状态）

**输出**：`{"can_execute": true, "element_found": true}`

#### 场景：验证失败取消操作

**前提条件**：目标元素不存在或不可见

**输入**：目标元素 "cancel_button"

**预期行为**：
- 尝试定位元素
- 发现元素不存在
- 取消操作执行
- 返回详细的失败原因

**输出**：`{"can_execute": false, "reason": "元素未找到: cancel_button"}`

---

### 需求：操作后验证

系统**必须**在操作执行后验证预期结果，确保操作成功。系统**应**在验证失败时自动重试操作。

#### 场景：验证文件已打开

**前提条件**：执行了打开文件操作

**输入**：
```python
Action(
    type="click",
    parameters={"target": "file_main_py"},
    post_check={
        "type": "verify_file_opened",
        "filename": "main.py"
    }
)
```

**预期行为**：
- 执行点击操作
- 等待 1 秒让界面响应
- 截图验证文件名在标题栏或标签页中
- 返回验证结果

**输出**：`{"success": true, "verified": true, "file_opened": "main.py"}`

#### 场景：操作后验证失败触发重试

**前提条件**：操作执行但结果验证失败

**输入**：重命名操作

**预期行为**：
- 执行重命名快捷键
- 验证新名称未出现
- 计入重试次数
- 重新执行操作

**输出**：`{"success": true, "retry_count": 1, "verified": true}`

---

### 需求：超时和重试机制

系统**必须**处理操作超时和自动重试失败的操作。系统**应**支持配置最大重试次数（默认 3 次）和重试延迟。重试机制**必须**使整体成功率提升至少 15%。

#### 场景：操作超时

**前提条件**：操作执行时间超过预期

**输入**：
```python
Action(
    type="click",
    parameters={"target": "slow_button"},
    timeout=2.0
)
```

**预期行为**：
- 开始执行操作
- 监控执行时间
- 超过 2 秒后判定超时
- 终止操作并返回超时错误

**输出**：`{"success": false, "error": "操作超时: timeout=2.0s"}`

#### 场景：自动重试失败操作

**前提条件**：配置了重试策略

**输入**：
```python
Action(
    type="click",
    parameters={"target": "unstable_button"},
    max_retries=3,
    retry_delay=1.0
)
```

**预期行为**：
1. 第一次执行：失败
2. 等待 1 秒
3. 第二次执行：失败
4. 等待 1 秒
5. 第三次执行：成功

**输出**：`{"success": true, "attempts": 3}`

#### 场景：重试次数耗尽

**前提条件**：所有重试都失败

**输入**：最大重试次数为 3 的操作

**预期行为**：
- 尝试 3 次操作
- 全部失败
- 返回最终失败结果

**输出**：`{"success": false, "attempts": 3, "error": "重试次数耗尽"}`

---

### 需求：鼠标平滑移动

系统**应**模拟自然的鼠标移动轨迹，避免机械化的瞬间跳跃。系统**必须**支持可配置的移动持续时间和路径曲线类型。

#### 场景：平滑移动到目标

**前提条件**：从 (100, 100) 移动到 (500, 400)

**输入**：
```python
Action(
    type="click",
    parameters={
        "start": (100, 100),
        "end": (500, 400),
        "smooth": true,
        "duration": 0.3
    }
)
```

**预期行为**：
- 计算移动路径（贝塞尔曲线或线性插值）
- 在 300ms 内分多次小步移动
- 模拟人类移动曲线（轻微加速和减速）

**输出**：`{"success": true, "movement_duration": 0.3}`

---

## 数据模型

```python
@dataclass
class Action:
    """单个操作"""
    type: str                      # 操作类型
    parameters: Dict[str, Any]     # 操作参数
    timeout: float = 5.0           # 超时时间
    max_retries: int = 3           # 最大重试次数
    retry_delay: float = 1.0       # 重试延迟
    pre_check: Optional[Dict] = None      # 前置检查
    post_check: Optional[Dict] = None     # 后置验证
    smooth_move: bool = True       # 是否平滑移动鼠标

@dataclass
class ActionResult:
    """操作执行结果"""
    success: bool
    action: Action
    error: Optional[str] = None
    retry_count: int = 0
    duration: float = 0.0
    verified: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class SequenceResult:
    """操作序列执行结果"""
    success: bool
    results: List[ActionResult]
    completed_steps: int
    total_steps: int
    total_duration: float
    failed_at: Optional[int] = None
```

## API 接口

```python
class AutomationExecutor:
    """GUI 自动化执行器接口"""

    def execute(self, action: Action) -> ActionResult:
        """执行单个操作

        Args:
            action: 要执行的操作

        Returns:
            执行结果
        """
        pass

    def execute_sequence(
        self,
        actions: List[Action],
        stop_on_error: bool = True
    ) -> SequenceResult:
        """执行操作序列

        Args:
            actions: 操作列表
            stop_on_error: 遇到错误是否停止

        Returns:
            序列执行结果
        """
        pass

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1
    ) -> bool:
        """执行点击操作

        Args:
            x: 目标 X 坐标
            y: 目标 Y 坐标
            button: 鼠标键 (left/right/middle)
            clicks: 点击次数

        Returns:
            是否成功
        """
        pass

    def type_text(
        self,
        text: str,
        delay: float = 0.0
    ) -> bool:
        """输入文本

        Args:
            text: 要输入的文本
            delay: 每个字符之间的延迟

        Returns:
            是否成功
        """
        pass

    def press_keys(
        self,
        keys: List[str],
        duration: float = 0.1
    ) -> bool:
        """按下组合键

        Args:
            keys: 键列表，如 ["ctrl", "s"]
            duration: 按键持续时间

        Returns:
            是否成功
        """
        pass

    def verify_action(
        self,
        action: Action,
        result: ActionResult
    ) -> bool:
        """验证操作结果

        Args:
            action: 执行的操作
            result: 操作结果

        Returns:
            验证是否通过
        """
        pass

    def emergency_stop(self) -> None:
        """紧急停止所有正在执行的操作"""
        pass
```

## 安全机制

```python
class SafetyConfig:
    """安全配置"""
    dangerous_operations: List[str] = [
        "delete_file",
        "delete_folder",
        "git_reset_hard",
        "format_disk"
    ]
    require_confirmation: bool = True
    enable_undo: bool = True
    max_execution_time: float = 30.0
```

## 验收标准

1. 鼠标操作成功率 >= 98%
2. 键盘操作成功率 >= 99%
3. 操作序列成功率 >= 95%
4. 单个操作响应时间 < 1s
5. 重试机制使整体成功率提升 >= 15%
6. 支持紧急停止功能
