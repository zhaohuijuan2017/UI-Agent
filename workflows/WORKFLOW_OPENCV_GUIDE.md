# 工作流中使用 OpenCV 模板匹配

## 概述

系统支持两种 UI 元素识别方式：

| 方式 | 技术基础 | 优点 | 缺点 |
|------|----------|------|------|
| **OpenCV 模板匹配** | 计算机视觉算法 | 快速、准确、不需要 AI | 需要预先准备模板图片 |
| **GLM-4V-Flash 视觉识别** | AI 模型 | 无需模板，理解能力强 | 较慢，需要网络 |

## OpenCV 模板匹配使用方法

### 1. 准备模板图片

将 UI 元素的截图保存到 `templates/` 目录：

```bash
templates/
├── run_button.png          # 运行按钮
├── database-button.png     # 数据库按钮
└── project-view.png        # 项目视图图标
```

### 2. 在工作流中使用模板

创建工作流文件，使用 `template` 参数指定模板：

```markdown
---
name: "使用模板匹配的工作流"
---

## 步骤

1. 激活 PyCharm 窗口

2. 点击运行按钮

   ```yaml
   operation: click_run_button
   parameters:
     template: run_button.png
     confidence: 0.8
   ```

3. 点击数据库按钮

   ```yaml
   operation: click_database_button
   parameters:
     template: database-button.png
   ```
```

### 3. 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `template` | 模板图片文件名 | `run_button.png` |
| `confidence` | 匹配置信度 (0.0-1.0) | `0.8` (默认 0.8) |

### 4. 已定义的模板匹配操作

系统已预定义以下支持模板匹配的操作：

| 操作名称 | 说明 | 模板图片 |
|----------|------|----------|
| `click_run_button` | 点击运行按钮 | `run_button.png` |
| `click_database_button` | 点击数据库按钮 | `database-button.png` |
| `click_button` | 通用点击按钮 | 通过 `--template` 参数指定 |

## 执行工作流

```bash
# 验证工作流
python -m src.main --workflow workflows/opencv-example.md --dry-run

# 执行工作流
python -m src.main --workflow workflows/opencv-example.md
```

## 模板匹配配置

在 `config/main.yaml` 中配置模板匹配：

```yaml
template_matching:
  enabled: true
  template_dir: "templates/"
  default_confidence: 0.8
  method: "TM_CCOEFF_NORMED"  # OpenCV 匹配方法
  enable_multiscale: true      # 多尺度匹配
  scales: [0.8, 0.9, 1.0, 1.1, 1.2]
```

## OpenCV 匹配方法

| 方法 | 说明 |
|------|------|
| `TM_SQDIFF` | 平方差匹配 |
| `TM_SQDIFF_NORMED` | 归一化平方差匹配 |
| `TM_CCORR` | 相关匹配 |
| `TM_CCORR_NORMED` | 归一化相关匹配 |
| `TM_CCOEFF` | 系数匹配 |
| `TM_CCOEFF_NORMED` | 归一化系数匹配（推荐） |

## 混合使用示例

可以混合使用模板匹配和自然语言命令：

```markdown
## 步骤

1. 激活 PyCharm 窗口

2. 点击运行按钮（使用模板）
   ```yaml
   operation: click_run_button
   parameters:
     template: run_button.png
   ```

3. 双击 main.py 文件（使用 AI 识别）

4. 跳转到第 10 行（快捷键）
```

## 注意事项

1. **模板图片**：应与实际 UI 元素尺寸一致
2. **置信度设置**：太低可能误匹配，太高可能匹配失败
3. **多尺度匹配**：启用后可匹配不同大小的元素
4. **优先级**：模板匹配优先于视觉识别

## 故障排除

### 模板匹配失败

1. 检查模板图片路径是否正确
2. 降低 `confidence` 阈值
3. 启用多尺度匹配
4. 确保模板图片与当前 UI 一致

### 调试模式

```bash
# 启用调试日志
python -m src.main --workflow workflows/opencv-example.md --debug
```
