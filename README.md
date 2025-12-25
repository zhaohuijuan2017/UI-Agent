# UI-Agent - 自然语言控制 PyCharm IDE 系统

一个通过自然语言指令控制 PyCharm IDE 的智能助手系统，结合了自然语言处理（NLP）、计算机视觉和 GUI 自动化技术。

## 功能特性

- 自然语言命令解析和意图识别
- 基于 GLM-4V-Flash 的视觉 UI 元素定位
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
python -m src.main "打开 main.py"
```

## 支持的命令

系统支持以下类型的自然语言命令：

- **文件操作**：打开文件、关闭文件、保存文件、新建文件
- **编辑操作**：重命名符号、提取方法、格式化代码
- **导航操作**：跳转到行、查找文件、查找符号
- **运行操作**：运行当前文件、调试程序、运行测试

示例：
```
打开 main.py
跳转到第 50 行
重命名当前函数为 foo
运行当前文件
格式化代码
```

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
│   └── models/           # 数据模型
├── config/               # 配置文件
├── tests/                # 测试
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
