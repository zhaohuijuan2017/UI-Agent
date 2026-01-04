# vision-config Specification

## Purpose
TBD - created by archiving change disable-vision-recognition. Update Purpose after archive.
## 需求
### 需求：视觉识别配置开关

系统**必须**支持通过配置文件控制视觉识别功能的启用状态。

#### 场景：默认启用视觉识别

**给定**：配置文件中未指定 `vision.enabled` 或设置为 `true`

**当**：系统启动并执行 UI 定位操作

**那么**：
- 系统应使用大模型视觉识别作为主要定位方式
- 行为与当前实现保持一致

#### 场景：禁用视觉识别

**给定**：配置文件中设置 `vision.enabled: false`

**当**：系统执行 UI 定位操作

**那么**：
- 系统不应调用大模型视觉 API
- 系统应使用 OCR 定位方式
- 日志应输出"视觉识别已禁用，使用 OCR 定位"

#### 场景：配置热更新

**给定**：系统正在运行且启用了热更新
**并且**：初始配置 `vision.enabled: true`

**当**：配置文件被修改为 `vision.enabled: false`

**那么**：
- 下次定位操作应使用 OCR 而非大模型
- 无需重启系统

---

### 需求：配置数据模型

配置系统**必须**支持视觉识别相关的配置项。

#### 场景：配置解析

**给定**：配置文件包含以下内容：

```yaml
vision:
  enabled: false
```

**当**：配置管理器加载配置

**那么**：
- `MainConfig.vision.enabled` 应为 `false`
- 配置验证应通过

#### 场景：默认值

**给定**：配置文件不包含 `vision` 部分

**当**：配置管理器加载配置

**那么**：
- `MainConfig.vision.enabled` 应默认为 `true`

---

### 需求：定位器行为控制

`VisualLocator` **必须**根据配置决定定位策略。

#### 场景：启用状态下的定位

**给定**：`VisualLocator` 初始化时 `vision_enabled=true`
**并且**：调用 `locate(prompt, screenshot, target_filter="example")`

**当**：执行定位操作

**那么**：
- 首先尝试使用大模型视觉识别（`_locate_with_vision`）
- 如果有 `target_filter` 且支持 OCR，使用混合定位（`_locate_hybrid`）
- 行为与当前实现一致

#### 场景：禁用状态下的定位

**给定**：`VisualLocator` 初始化时 `vision_enabled=false`
**并且**：调用 `locate(prompt, screenshot, target_filter="example")`

**当**：执行定位操作

**那么**：
- 不应调用 `client.chat.completions.create`（大模型 API）
- 应直接使用 OCR 定位（`_locate_with_ocr`）
- 如果 OCR 不可用，返回空列表

---

### 需求：多屏显示器支持

系统**必须**支持在多显示器环境下指定使用特定显示器进行截图和 UI 定位。

#### 场景：显示器索引说明

**给定**：系统运行在多显示器环境下

**那么**：
- `monitor_index = 0`: 整个虚拟屏幕（所有显示器合并）
- `monitor_index = 1`: 第一个显示器
- `monitor_index = 2`: 第二个显示器
- 以此类推...

#### 场景：查看可用显示器

**给定**：已创建 `ScreenshotCapture` 实例

**当**：调用 `get_monitors()` 方法

**那么**：
- 应返回所有可用显示器的信息列表
- 每个显示器信息应包含完整的坐标和尺寸信息

```python
from src.locator.screenshot import ScreenshotCapture

capture = ScreenshotCapture(config)
monitors = capture.get_monitors()
for i, m in enumerate(monitors):
    print(f"显示器 {i}: {m}")
```

#### 场景：创建定位器时指定默认显示器

**给定**：系统有多个显示器

**当**：创建 `VisualLocator` 时指定 `monitor_index=2`

**那么**：
- 所有后续定位操作应默认使用第二个显示器
- 截图应仅包含第二个显示器的内容

```python
locator = VisualLocator(
    api_key="your_api_key",
    screenshot_capture=capture,
    monitor_index=2  # 使用第二个显示器
)
```

#### 场景：动态切换显示器

**给定**：`VisualLocator` 已初始化

**当**：调用 `set_monitor_index(3)`

**那么**：
- 默认显示器应更新为第三个显示器
- 后续定位操作应使用新指定的显示器

```python
locator.set_monitor_index(1)  # 切换到第一个显示器
current = locator.get_monitor_index()  # 应返回 1
```

#### 场景：定位时临时指定显示器

**给定**：`VisualLocator` 默认使用显示器 1

**当**：调用 `locate(prompt, monitor_index=3)`

**那么**：
- 此次定位应临时使用第三个显示器
- 默认显示器设置不应改变
- 后续定位仍使用显示器 1

```python
# 使用默认显示器
elements = locator.locate("查找按钮")

# 临时使用第三个显示器
elements = locator.locate("查找按钮", monitor_index=3)
```

#### 场景：验证时指定显示器

**给定**：需要验证元素位置

**当**：调用 `verify(element, monitor_index=2)`

**那么**：
- 应使用第二个显示器的截图进行验证
- 验证结果应基于指定显示器的坐标系统

#### 场景：错误处理

**给定**：系统只有 3 个显示器（索引 0-2）

**当**：尝试使用 `monitor_index=5`

**那么**：
- 应抛出 `ValueError` 异常
- 异常信息应包含可用范围："显示器索引 5 超出范围，可用范围: 0-2"

#### 场景：配置文件支持（可选）

**给定**：配置文件包含显示器配置

```yaml
vision:
  enabled: true
  monitor_index: 2  # 默认使用第二个显示器
```

**当**：系统初始化 `VisualLocator`

**那么**：
- 应从配置文件读取默认显示器索引
- 如果未配置，默认使用 0（所有显示器合并）

---

