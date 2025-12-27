# 工作流功能指南

工作流功能允许你通过 Markdown 文档定义多步骤操作流程，自动按顺序执行。

## 目录

- [快速开始](#快速开始)
- [文档格式](#文档格式)
- [高级特性](#高级特性)
- [执行方式](#执行方式)
- [示例](#示例)
- [最佳实践](#最佳实践)

---

## 快速开始

### 1. 创建工作流文件

在 `workflows/` 目录下创建一个 Markdown 文件：

```markdown
---
name: "我的第一个工作流"
description: "打开并跳转到指定行"
---

# 我的工作流

## 步骤

1. 激活 PyCharm 窗口
2. 双击文件 main.py
3. 跳转到第 42 行
```

### 2. 执行工作流

```bash
python -m src.main --workflow workflows/my-workflow.md
```

### 3. 验证工作流（不执行）

```bash
python -m src.main --workflow workflows/my-workflow.md --dry-run
```

---

## 文档格式

工作流文件使用 Markdown 格式，包含 YAML front matter 和步骤列表。

### 基本结构

```markdown
---
name: "工作流名称"
description: "工作流描述"
variables:
  key: "value"
---

# 工作流标题

## 步骤

1. 第一步描述
2. 第二步描述
3. 第三步描述
```

### Front Matter 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 工作流名称 |
| `description` | string | 否 | 工作流描述 |
| `variables` | object | 否 | 变量字典（预留） |

### 步骤格式

每个步骤以有序列表（`1. `、`2. ` 等）开始，后跟步骤描述。

```markdown
1. 激活 PyCharm 窗口
2. 打开文件 main.py
3. 跳转到第 50 行
```

---

## 高级特性

### 1. YAML 配置块

可以在步骤下方添加 YAML 配置块，提供更详细的参数：

```markdown
1. 打开文件 main.py

   ```yaml
   operation: double_click_file
   parameters:
     filename: "main.py"
   retry_count: 3
   retry_interval: 2.0
   continue_on_error: true
   ```
```

#### 支持的配置字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `operation` | string | - | 操作名称（如 double_click_file） |
| `parameters` | object | `{}` | 操作参数 |
| `retry_count` | int | `0` | 重试次数 |
| `retry_interval` | float | `1.0` | 重试间隔（秒） |
| `condition` | string | - | 执行条件 |
| `continue_on_error` | bool | `false` | 失败时是否继续 |

### 2. 条件分支

使用条件标记控制步骤的执行：

```markdown
1. 激活 PyCharm 窗口
2. [if_success] 打开文件 main.py
3. [if_failure] 显示错误提示
```

#### 支持的条件

| 条件 | 说明 |
|------|------|
| `[if_success]` | 上一步成功时执行 |
| `[if_failure]` | 上一步失败时执行 |

### 3. 重试机制

为容易失败的步骤配置重试：

```markdown
1. 打开文件 large_file.py

   ```yaml
   retry_count: 3
   retry_interval: 2.0
   ```
```

- `retry_count`: 重试次数（不包括首次尝试）
- `retry_interval`: 每次重试之间的间隔（秒）

### 4. 错误处理

使用 `continue_on_error` 控制失败时的行为：

```markdown
1. 尝试打开可选文件

   ```yaml
   continue_on_error: true
   ```

2. 继续执行下一步
```

---

## 执行方式

### 命令行执行

```bash
# 执行工作流
python -m src.main --workflow workflows/simple-example.md

# 验证工作流（不实际执行）
python -m src.main --workflow workflows/simple-example.md --dry-run
```

### 交互式执行

```bash
# 启动交互式 CLI
python -m src.main

# 然后输入
执行工作流 workflows/simple-example.md
```

### 程序化执行

```python
from src.controller.ide_controller import IDEController

controller = IDEController()

# 执行工作流文件
result = controller.execute_workflow_file("workflows/simple-example.md")

# 验证工作流
result = controller.validate_workflow_file("workflows/simple-example.md")
```

---

## 示例

### 示例 1：简单工作流

```markdown
---
name: "打开文件"
description: "激活窗口并打开文件"
---

# 打开文件工作流

## 步骤

1. 激活 PyCharm 窗口
2. 双击文件 main.py
```

### 示例 2：带条件的工作流

```markdown
---
name: "条件执行"
description: "演示条件分支"
---

## 步骤

1. 激活 PyCharm 窗口

2. [if_success] 双击文件 main.py

3. [if_success] 跳转到第 42 行

4. [if_failure] 显示错误消息
```

### 示例 3：带重试的工作流

```markdown
---
name: "重试演示"
description: "演示重试机制"
---

## 步骤

1. 激活 PyCharm 窗口

2. 打开文件 large_file.py

   ```yaml
   operation: double_click_file
   parameters:
     filename: "large_file.py"
   retry_count: 3
   retry_interval: 2.0
   ```

3. 跳转到第 1 行
```

### 示例 4：浏览器工作流

```markdown
---
name: "浏览器操作"
description: "打开浏览器并搜索"
---

## 步骤

1. 打开浏览器访问 https://www.baidu.com

2. 网页点击 搜索框

3. 在网页输入框中输入 Python 并回车

4. 等待页面加载完成

5. 页面滚动
```

### 示例 5：复杂工作流

```markdown
---
name: "部署流程"
description: "完整的部署自动化"
---

# 部署流程

## 步骤

1. 激活 PyCharm 窗口

2. 双击文件 deploy.py

3. [if_success] 跳转到第 1 行

4. [if_success] 运行当前文件

5. [if_success] 打开浏览器访问 http://localhost:8080

6. [if_failure] 显示部署失败消息

   ```yaml
   continue_on_error: true
   ```

7. 等待 5 秒

8. 网页刷新页面
```

---

## 最佳实践

### 1. 工作流命名

使用清晰、描述性的名称：

```markdown
---
name: "部署到测试环境"
description: "自动部署应用到测试服务器"
---
```

### 2. 步骤描述

使用自然语言描述步骤：

```markdown
1. 激活 PyCharm 窗口
2. 双击文件 main.py
3. 跳转到第 42 行
```

### 3. 错误处理

为可能失败的步骤配置重试和错误处理：

```markdown
1. 打开网络资源文件

   ```yaml
   retry_count: 5
   retry_interval: 3.0
   continue_on_error: true
   ```
```

### 4. 使用 YAML 配置

对于复杂操作，使用 YAML 配置块：

```markdown
1. 在搜索框中输入 Python 并回车

   ```yaml
   operation: input_text
   parameters:
     context_text: "搜索框"
     input_text: "Python"
     submit_action: enter
   ```
```

### 5. 模块化设计

将复杂流程拆分为多个小工作流：

```markdown
# 主工作流
---
name: "完整部署"
---

## 步骤

1. 执行工作流 workflows/build.md
2. 执行工作流 workflows/test.md
3. 执行工作流 workflows/deploy.md
```

### 6. 验证先行

使用 `--dry-run` 验证工作流：

```bash
# 先验证
python -m src.main --workflow workflows/deploy.md --dry-run

# 确认无误后再执行
python -m src.main --workflow workflows/deploy.md
```

### 7. 添加注释

使用注释说明复杂步骤：

```markdown
## 步骤

<!-- 首先确保 PyCharm 处于活动状态 -->
1. 激活 PyCharm 窗口

<!-- 打开主程序文件 -->
2. 双击文件 main.py

<!-- 跳转到入口函数 -->
3. 跳转到第 42 行
```

---

## 故障排查

### 工作流执行失败

1. **验证工作流格式**：使用 `--dry-run` 检查格式
2. **检查日志**：查看 `logs/` 目录下的日志文件
3. **单独测试步骤**：将失败的步骤单独执行

### 步骤被跳过

- 检查条件标记是否正确
- 确认前一步的执行状态

### 重试不生效

- 检查 `retry_count` 和 `retry_interval` 是否正确配置
- 确认 YAML 配置块格式正确

---

## 相关文档

- [命令参考](COMMANDS.md) - 所有支持的命令
- [README.md](README.md) - 项目总体说明
- [浏览器自动化](workflows/WORKFLOW_OPENCV_GUIDE.md) - 浏览器自动化指南
