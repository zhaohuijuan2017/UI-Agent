# 规范：视觉 UI 定位器

## 能力标识
`visual-ui-locator`

## 依赖
- 屏幕捕获功能

## 新增需求

### 需求：屏幕区域捕获

系统**必须**能够捕获整个屏幕或指定区域的屏幕截图。全屏捕获响应时间**应**小于 100ms。系统**应**支持窗口级捕获并自动排除窗口边框。

#### 场景：全屏捕获

**前提条件**：系统已初始化

**输入**：无特殊参数

**预期行为**：
- 调用系统 API 获取整个主显示器截图
- 返回 PIL Image 对象
- 记录截图元数据（时间戳、分辨率）

**输出**：`Image` 对象，分辨率与显示器一致

#### 场景：指定区域捕获

**前提条件**：已确定目标区域坐标

**输入**：`{"x": 100, "y": 200, "width": 800, "height": 600}`

**预期行为**：
- 只捕获指定坐标区域的屏幕内容
- 返回裁剪后的图像

**输出**：`Image` 对象，尺寸为 800x600

#### 场景：窗口级捕获

**前提条件**：已识别 PyCharm 窗口句柄

**输入**：`{"window_title": "PyCharm - main.py"}`

**预期行为**：
- 定位目标窗口
- 捕获窗口客户区内容
- 排除窗口边框和标题栏

**输出**：`Image` 对象，包含窗口内容区

---

### 需求：UI 元素视觉检测

系统**必须**使用视觉理解模型在屏幕截图中检测和定位 UI 元素。系统**应**支持检测按钮、菜单、文本框、编辑区等多种 UI 元素类型。元素定位准确率**必须**达到 85% 以上。

#### 场景：检测按钮元素

**前提条件**：已获取屏幕截图

**输入**：
```python
screenshot: Image
prompt: "在截图中找到'运行'按钮的位置"
```

**预期行为**：
- 将截图和提示词发送给 GLM-4V-Flash
- 模型分析图像，识别按钮
- 返回按钮的边界框坐标

**输出**：
```python
UIElement(
    element_type="button",
    description="绿色运行按钮",
    bbox=(x1, y1, x2, y2),
    confidence=0.95
)
```

#### 场景：检测菜单项

**前提条件**：已获取包含菜单的截图

**输入**：
```python
screenshot: Image
prompt: "找到文件菜单中的'打开'选项"
```

**预期行为**：
- 分析截图中的菜单结构
- 定位目标菜单项
- 处理可能的子菜单展开

**输出**：`UIElement` 列表，包含主菜单和子菜单项

#### 场景：检测文本编辑区

**前提条件**：已获取 PyCharm 窗口截图

**输入**：
```python
screenshot: Image
prompt: "定位代码编辑区域"
```

**预期行为**：
- 识别编辑器的主体区域
- 排除侧边栏、工具栏
- 返回编辑器的精确边界

**输出**：
```python
UIElement(
    element_type="editor",
    description="代码编辑区",
    bbox=(x1, y1, x2, y2),
    confidence=0.92
)
```

---

### 需求：多模态元素定位

系统**必须**支持多种定位策略，在主策略失败时自动切换到备用方案。系统**应**至少支持三种定位策略：视觉检测、OCR 文本识别和固定坐标映射。

#### 场景：视觉定位成功

**前提条件**：目标元素在截图中清晰可见

**输入**：定位请求

**预期行为**：
1. 尝试策略 1：GLM-4V-Flash 视觉检测
2. 成功检测到元素
3. 返回结果

**输出**：定位成功，置信度 > 0.8

#### 场景：视觉定位失败切换到 OCR

**前提条件**：视觉模型未找到元素或置信度过低

**输入**：定位请求

**预期行为**：
1. 尝试策略 1：视觉检测，置信度 0.3
2. 切换到策略 2：OCR 文本识别
3. 在截图中搜索目标文本
4. 返回文本位置的坐标

**输出**：通过 OCR 定位到的元素坐标

#### 场景：OCR 失败使用固定坐标

**前提条件**：OCR 也未能定位元素

**输入**：定位请求

**预期行为**：
1. 尝试策略 1：视觉检测，失败
2. 尝试策略 2：OCR，失败
3. 切换到策略 3：配置文件中的固定坐标
4. 返回预定义坐标

**输出**：使用配置文件中的备用坐标

---

### 需求：坐标计算和验证

系统**必须**计算 UI 元素的可交互区域（如按钮中心点）并验证坐标有效性。系统**应**拒绝超出屏幕范围的坐标，并**必须**处理部分可见元素的情况。

#### 场景：计算按钮点击位置

**前提条件**：已获取元素边界框

**输入**：`bbox=(100, 200, 300, 250)`

**预期行为**：
- 计算边界框中心点：`(200, 225)`
- 验证坐标在屏幕范围内
- 返回可用于点击的坐标

**输出**：`{"x": 200, "y": 225}`

#### 场景：验证坐标超出屏幕范围

**前提条件**：计算的坐标异常

**输入**：`bbox=(-50, 200, 300, 250)`

**预期行为**：
- 检测到 x1 为负数
- 标记为无效坐标
- 返回错误信息

**输出**：`{"valid": false, "error": "坐标超出屏幕范围"}`

#### 场景：处理部分可见元素

**前提条件**：元素只有一部分在屏幕内

**输入**：部分可见的边界框

**预期行为**：
- 计算可见区域
- 确定是否包含足够的可交互区域
- 决定是否可以安全操作

**输出**：`{"can_interact": true, "safe_region": bbox}`

---

### 需求：定位结果置信度评估

系统**必须**为每个定位结果提供置信度评分，指示定位的可靠性。系统**应**在置信度低于阈值时请求用户确认或返回多个候选结果。

#### 场景：高置信度定位

**前提条件**：元素特征明显，位置正确

**输入**：清晰的截图和明确的元素描述

**预期行为**：
- 视觉模型返回高置信度
- 元素位置符合预期
- 边界框完整

**输出**：`UIElement(confidence=0.95, reliable=true)`

#### 场景：低置信度需要重试

**前提条件**：元素模糊或有多个相似元素

**输入**：可能包含多个相似元素的截图

**预期行为**：
- 视觉模型返回低置信度
- 检测到多个候选位置
- 请求用户确认或重试

**输出**：`UIElement(confidence=0.45, reliable=false, candidates=[...])`

---

### 需求：定位缓存机制

系统**必须**缓存定位结果，避免重复定位相同元素。缓存有效期**应**不超过 30 秒，系统**应**提供清除缓存的方法。

#### 场景：使用缓存的定位结果

**前提条件**：之前已定位过相同元素

**输入**：定位请求，元素名称 `"run_button"`

**预期行为**：
- 检查缓存中是否存在该元素
- 验证缓存是否过期（时间 < 30s）
- 返回缓存的坐标

**输出**：从缓存返回的坐标，无 API 调用

#### 场景：缓存失效重新定位

**前提条件**：缓存时间超过有效期

**输入**：定位请求，缓存已过期

**预期行为**：
- 检测到缓存过期
- 重新执行视觉定位
- 更新缓存

**输出**：新定位的结果，缓存已更新

---

## 数据模型

```python
@dataclass
class UIElement:
    """UI 元素信息"""
    element_type: str              # 元素类型
    description: str               # 元素描述
    bbox: Tuple[int, int, int, int]  # 边界框 (x1, y1, x2, y2)
    center: Tuple[int, int]        # 中心点坐标
    confidence: float              # 置信度 (0-1)
    visible_region: Optional[Tuple[int, int, int, int]]  # 可见区域
    metadata: Dict[str, Any]       # 额外元数据

@dataclass
class ScreenshotMetadata:
    """截图元数据"""
    timestamp: datetime
    resolution: Tuple[int, int]
    window_info: Optional[Dict[str, Any]]
    file_path: Optional[str]

@dataclass
class LocateResult:
    """定位结果"""
    success: bool
    element: Optional[UIElement]
    method_used: str               # 使用的定位方法
    candidates: List[UIElement]    # 候选元素（低置信度时）
    error: Optional[str]
```

## API 接口

```python
class VisualLocator:
    """视觉 UI 定位器接口"""

    def capture_screen(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        window: Optional[str] = None
    ) -> Tuple[Image, ScreenshotMetadata]:
        """捕获屏幕截图

        Args:
            region: 指定区域 (x, y, width, height)
            window: 窗口标题

        Returns:
            截图和元数据
        """
        pass

    def locate(
        self,
        prompt: str,
        screenshot: Optional[Image] = None,
        element_type: Optional[str] = None
    ) -> LocateResult:
        """定位 UI 元素

        Args:
            prompt: 元素描述提示词
            screenshot: 截图（如为 None 则自动捕获）
            element_type: 元素类型（可选，辅助检测）

        Returns:
            定位结果
        """
        pass

    def locate_with_fallback(
        self,
        prompt: str,
        strategies: List[str],
        screenshot: Optional[Image] = None
    ) -> LocateResult:
        """使用多种策略定位元素（带回退）

        Args:
            prompt: 元素描述
            strategies: 策略列表 ["visual", "ocr", "fixed"]
            screenshot: 截图

        Returns:
            定位结果
        """
        pass

    def verify_location(
        self,
        element: UIElement,
        screenshot: Image
    ) -> bool:
        """验证元素位置

        Args:
            element: 要验证的元素
            screenshot: 用于验证的截图

        Returns:
            是否有效
        """
        pass

    def clear_cache(self) -> None:
        """清除定位缓存"""
        pass
```

## 验收标准

1. 全屏捕获响应时间 < 100ms
2. UI 元素定位准确率 >= 85%
3. 高置信度定位（> 0.8）占比 >= 70%
4. 多模态回退成功率 >= 95%
5. 缓存命中率 >= 60%（对于重复元素）
6. 支持 OCR 备用定位
