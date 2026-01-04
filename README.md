# UI-Agent - 自然语言控制 PyCharm IDE 系统

一个通过自然语言指令控制 PyCharm IDE 的智能助手系统，结合了自然语言处理（NLP）、计算机视觉和 GUI 自动化技术。

## 功能特性

- 自然语言命令解析和意图识别
- 基于 GLM-4V-Flash 的视觉 UI 元素定位
- **窗口管理功能**：激活、切换窗口，支持多种 IDE
- **浏览器启动功能**：打开浏览器并访问指定网址
- **浏览器自动化功能**：点击、滚动、输入文本、按键操作
- **工作流执行功能**：通过 Markdown 文档定义多步骤操作流程
  - 支持串行执行步骤
  - 支持条件分支（if_success、if_failure）
  - 支持可配置重试机制
  - 支持混合格式（自然语言 + YAML 配置）
- 跨平台 GUI 自动化操作执行
- 可扩展的 IDE 操作配置系统
- 完善的安全机制和错误恢复

## 快速开始

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd ui-agent

# 安装依赖
pip install -e ".[dev]"
```

### 配置

1. 复制配置模板：
```bash
cp config/main.yaml.example config/main.yaml
```

2. 设置智谱 AI API Key：
```bash
export ZHIPUAI_API_KEY="your-api-key-here"
```

3. 编辑 `config/main.yaml` 配置文件

### 使用

```bash

# 启动交互式 CLI
python -m src.main

# 执行单条命令
python -m src.main "在 终端 下方的输入框中输入 python --version 并回车"
python -m src.main "双击 implement-nl-ide-control"

# 执行工作流文件
python -m src.main --workflow workflows/simple-example.md

# 验证工作流（不执行）
python -m src.main --workflow workflows/simple-example.md --dry-run
```

## 支持的命令

系统支持以下类型的自然语言命令：

- **窗口管理**：激活窗口、切换到 PyCharm、切换窗口
- **浏览器启动**：打开浏览器、访问网址、在浏览器中打开
- **浏览器自动化**：点击元素、滚动页面、在输入框中输入、等待元素
- **文件操作**：打开文件、关闭文件、保存文件、新建文件
- **编辑操作**：重命名符号、提取方法、格式化代码
- **导航操作**：跳转到行、查找文件、查找符号
- **运行操作**：运行当前文件、调试程序、运行测试

## 工作流功能

工作流允许你通过 Markdown 文档定义多步骤操作流程，自动按顺序执行。

### 工作流文档格式

```markdown
---
name: "工作流名称"
description: "工作流描述"
variables:
  url: "https://example.com"
---

# 工作流标题

## 步骤

1. 激活 PyCharm 窗口

2. 打开文件 main.py

   ```yaml
   operation: double_click_file
   parameters:
     filename: "main.py"
   retry_count: 2
   ```

3. [if_success] 跳转到第 42 行

4. [if_failure] 显示错误提示
   ```yaml
   continue_on_error: true
   ```
```

### 工作流特性

- **条件分支**：使用 `[if_success]` 或 `[if_failure]` 标记条件步骤
- **重试机制**：在 YAML 配置中设置 `retry_count` 和 `retry_interval`
- **错误处理**：使用 `continue_on_error` 控制失败时的行为
- **混合格式**：纯自然语言或 YAML 配置，灵活选择

### 执行工作流

```bash
# 执行工作流
python -m src.main --workflow workflows/simple-example.md

# 验证工作流（不实际执行）
python -m src.main --workflow workflows/simple-example.md --dry-run
```

示例：
```
# 窗口管理
激活窗口
切换到 Chrome

# 浏览器启动
打开浏览器访问 https://www.baidu.com
在 Chrome 中打开 https://github.com

# 浏览器自动化（需要使用明确的前缀）
网页点击 百度一下按钮
页面滚动
网页输入 搜索框 Python
等待页面加载完成

# 文件操作
打开 main.py
跳转到第 50 行
重命名当前函数为 foo

# 运行操作
运行当前文件
格式化代码
```

**注意**：浏览器自动化命令需要使用明确的前缀（"网页"、"页面"、"浏览器"），以区分于普通的 UI 操作。

例如：
- `网页点击 百度一下按钮` ✓ 正确
- `点击 百度一下按钮` ✗ 会被识别为普通 UI 操作（使用 OCR 视觉定位）

## 浏览器自动化 API

### 程序化使用

```python
import asyncio
from src.browser.automation import BrowserAutomation

async def browser_automation_example():
    # 创建自动化实例
    automation = BrowserAutomation()

    try:
        # 连接到浏览器
        await automation.connect_to_browser()

        # 导航到页面
        await automation.get_page("https://www.example.com")

        # 点击元素（使用 CSS 选择器）
        await automation.click(".submit-button")

        # 点击元素（使用文本）
        await automation.click("text=提交")

        # 滚动页面
        await automation.scroll(direction="down")
        await automation.scroll_to_element(".footer")

        # 输入文本
        await automation.type_text("#search", "Playwright")

        # 按键操作
        await automation.press_key("#search", "Enter")

        # 等待元素
        await automation.wait_for_element(".results")

        # 检查元素状态
        is_visible = await automation.is_element_visible(".button")
        text = await automation.get_element_text("h1")
        href = await automation.get_element_attribute(".link", "href")

    finally:
        # 关闭浏览器
        await automation.close()

# 运行示例
asyncio.run(browser_automation_example())
```

### 支持的操作

| 操作 | 方法 | 说明 |
|------|------|------|
| 点击 | `click(locator, timeout)` | 点击指定元素 |
| 滚动 | `scroll(direction, distance)` | 向上/向下/左/右滚动 |
| 滚动到元素 | `scroll_to_element(locator, timeout)` | 滚动到指定元素 |
| 输入文本 | `type_text(locator, text, clear, timeout)` | 在输入框中输入 |
| 按键 | `press_key(locator, key, timeout)` | 模拟键盘按键 |
| 等待元素 | `wait_for_element(locator, visible, timeout)` | 等待元素出现/消失 |
| 检查可见性 | `is_element_visible(locator, timeout)` | 检查元素是否可见 |
| 检查启用状态 | `is_element_enabled(locator, timeout)` | 检查元素是否启用 |
| 获取文本 | `get_element_text(locator, timeout)` | 获取元素文本内容 |
| 获取属性 | `get_element_attribute(locator, attribute, timeout)` | 获取元素属性值 |

### 元素定位器

支持多种元素定位方式：

| 定位器类型 | 语法示例 | 说明 |
|-----------|---------|------|
| CSS 选择器 | `.button`, `#search`, `input[name="q"]` | CSS 选择器语法 |
| 文本内容 | `text=提交` | 精确匹配文本 |
| XPath | `xpath=//button[@type='submit']` | XPath 表达式 |
| 坐标定位 | `coords=100,200` | 页面坐标位置 |

## 多屏显示器支持

系统支持在多显示器环境下指定使用特定显示器进行截图和 UI 定位。

### 快速使用

```python
from src.locator.visual_locator import VisualLocator

# 创建定位器时指定默认显示器（monitor_index=2 表示第二个显示器）
locator = VisualLocator(
    api_key="your_api_key",
    screenshot_capture=capture,
    monitor_index=2
)

# 动态切换显示器
locator.set_monitor_index(1)

# 定位时临时指定显示器
elements = locator.locate("查找按钮", monitor_index=3)
```

### 显示器索引

- **0**: 整个虚拟屏幕（所有显示器合并）- 默认
- **1**: 第一个显示器
- **2**: 第二个显示器
- 以此类推...

详细使用说明和配置选项请参考：[多屏显示器支持规范](openspec/specs/vision-config/spec.md#需求多屏显示器支持)

## 项目结构

```
ui-agent/
├── src/
│   ├── controller/        # 控制层
│   ├── parser/           # 命令解析
│   ├── locator/          # 视觉定位
│   ├── automation/       # 自动化执行
│   ├── config/           # 配置管理
│   ├── infrastructure/   # 基础设施
│   ├── window/           # 窗口管理
│   ├── browser/          # 浏览器启动与自动化
│   ├── workflow/         # 工作流执行
│   │   ├── models.py         # 数据模型
│   │   ├── parser.py         # Markdown 解析器
│   │   ├── executor.py       # 执行器
│   │   ├── validator.py      # 验证器
│   │   └── exceptions.py     # 异常类
│   └── models/           # 数据模型
├── config/               # 配置文件
├── workflows/            # 工作流示例
├── tests/                # 测试
│   ├── unit/             # 单元测试
│   └── integration/      # 集成测试
├── logs/                 # 日志
└── screenshots/          # 截图
```

## 开发

```bash
# 运行测试
pytest

# 代码格式化
black src/
ruff check src/

# 类型检查
mypy src/
```

## 安全注意事项

- 系统会记录所有操作日志
- 危险操作（如删除文件）需要确认
- 支持紧急停止（Ctrl+C）
- 建议在测试环境先验证

## 许可证

MIT License
