# 任务列表

## 阶段 1：意图识别模块

### 1.1 创建意图模块结构
- [x] 创建 `src/intent/` 目录
- [x] 创建 `src/intent/__init__.py`
- [x] 创建 `src/intent/recognizer.py`：意图识别器
- [x] 创建 `src/intent/models.py`：意图数据模型
- [ ] 创建 `src/intent/classifier.py`：意图分类器

### 1.2 实现意图数据模型
- [x] 定义 `Intent` 数据类
  - `type`：意图类型（需求分析、开发、部署等）
  - `parameters`：提取的参数字典
  - `confidence`：识别置信度
  - `raw_message`：原始消息
- [x] 定义 `IntentPattern` 数据类
  - 模式匹配规则
  - 参数提取规则
- [x] 定义 `IntentMatchResult` 数据类
  - 匹配结果
  - 提取的参数

### 1.3 实现意图识别器（基于 LLM）
- [x] 实现 `IntentRecognizer.recognize(message: str)` 方法
- [x] 集成 LLM 客户端（支持不同的OPENAPI模型，通过配置定义）
- [x] 实现意图识别提示词模板
- [x] 实现 LLM 响应解析（提取意图类型、参数、置信度）
- [x] 实现置信度阈值判定（< 0.85 时请求用户确认）
- [x] 支持多意图匹配（返回所有可能的意图及置信度）
- [x] 实现意图定义加载机制（从配置文件/代码加载）

### 1.4 预定义意图类型

**单系统意图**：
- [x] `develop-feature`：需求开发（仅 IDE，直接使用消息中的需求内容）
- [x] `view-requirement`：需求查看（仅浏览器，从 URL 提取需求信息）

**跨系统组合意图**：
- [x] `requirement-to-development`：需求查看并开发（浏览器 → IDE）
- [x] `analyze_requirements`：分析需求（从链接/文件）
- [x] `design_solution`：设计方案（基于需求）
- [x] `implement_feature`：实现功能（基于设计/需求）
- [x] `deploy_application`：部署应用
- [x] `test_code`：测试代码
- [x] `review_code`：代码审查

### 1.5 创建意图定义文件
- [x] 创建 `config/intent_definitions.yaml`：意图类型定义
  - 每个意图的类型、描述、所需参数
  - 参数说明和示例值
- [x] 实现意图定义加载器
- [ ] 支持热重载（修改定义后无需重启）

## 阶段 2：任务流模板系统

### 2.1 创建模板模块
- [x] 创建 `src/templates/` 目录
- [x] 创建 `src/templates/__init__.py`
- [x] 创建 `src/templates/models.py`：模板数据模型
- [x] 创建 `src/templates/loader.py`：模板加载器
- [x] 创建 `src/templates/engine.py`：模板引擎

### 2.2 实现模板数据模型
- [x] 定义 `TaskFlowTemplate` 数据类
  - `name`：模板名称
  - `description`：模板描述
  - `intent_types`：适用的意图类型
  - `steps`：任务步骤列表
  - `parameters`：模板参数定义
- [x] 定义 `TemplateStep` 数据类
  - `system`：目标系统（browser、ide、terminal等）
  - `action`：执行动作
  - `parameters`：参数配置
  - `condition`：执行条件
  - `input_from`：输入数据来源
  - `output_to`：输出数据目标

### 2.3 实现模板加载器
- [x] 支持从文件加载模板（YAML/JSON）
- [x] 支持从代码定义模板
- [x] 实现模板注册机制
- [ ] 支持模板继承和组合

### 2.4 预定义任务流模板

**单场景模板**：
- [x] `develop-feature`：需求开发（单系统）
  - IDE：切换到 PyCharm
  - IDE：激活开发插件
  - IDE：传入需求内容
  - IDE：开始代码生成
- [x] `view-requirement`：需求查看（单系统）
  - 浏览器：打开需求页面
  - 浏览器：提取并展示需求内容

**跨系统组合模板**：
- [x] `requirement-to-development`：需求查看→开发流程
  - 浏览器：打开需求页面
  - 浏览器：提取需求信息
  - IDE：切换到 PyCharm
  - IDE：调用开发插件，传入需求信息
- [ ] `design-to-implementation`：设计→实现流程
- [ ] `code-to-deploy`：代码→部署流程

### 2.5 实现模板引擎
- [x] 支持参数替换（使用前一步的输出）
- [x] 支持条件分支
- [ ] 支持循环执行
- [x] 支持错误处理

## 阶段 3：任务编排器

### 3.1 创建编排模块
- [x] 创建 `src/orchestration/` 目录
- [x] 创建 `src/orchestration/__init__.py`
- [x] 创建 `src/orchestration/orchestrator.py`：任务编排器
- [x] 创建 `src/orchestration/executor.py`：任务执行器
- [x] 创建 `src/orchestration/context.py`：执行上下文

### 3.2 实现执行上下文
- [x] 定义 `ExecutionContext` 数据类
  - 存储任务执行状态
  - 保存步骤间传递的数据
  - 记录执行历史
- [x] 实现数据传递机制
  - 输入数据绑定
  - 输出数据捕获
  - 数据格式转换

### 3.3 实现任务编排器
- [x] 实现 `TaskOrchestrator.orchestrate(intent, context)`
- [x] 意图到模板的匹配
- [x] 步骤顺序编排
- [x] 跨系统切换管理
- [x] 异常处理和回滚

### 3.4 实现任务执行器
- [x] 实现单个任务步骤的执行
- [x] 集成现有的 IDEController、BrowserAutomation
- [x] 系统间切换逻辑
- [x] 数据提取和注入
- [x] 执行结果收集

### 3.5 实现系统桥接
- [x] 定义统一系统操作接口
- [x] 实现 `SystemAdapter` 协议
- [x] 浏览器系统适配器
- [x] IDE 系统适配器
- [ ] 终端系统适配器

## 阶段 4：CLI 集成

### 4.1 命令行接口
- [x] 修改 `main.py` 添加意图识别入口
- [ ] 支持 `--orchestrate` 模式
- [x] 显示任务执行进度
- [ ] 支持交互式确认

### 4.2 配置文件
- [x] 在 `config/` 中添加意图配置
- [x] 定义意图到模板的映射规则
- [ ] 配置系统切换参数

### 4.3 日志和监控
- [ ] 记录意图识别日志
- [ ] 记录任务执行日志
- 
- [ ] 记录跨系统切换日志
- [ ] 提供执行报告

## 阶段 5：测试

### 5.1 单元测试
- [ ] `tests/unit/test_intent_recognizer.py`
  - 测试意图识别准确性
  - 测试参数提取
- [ ] `tests/unit/test_template_engine.py`
  - 测试模板加载
  - 测试参数替换
  - 测试条件分支
- [ ] `tests/unit/test_orchestrator.py`
  - 测试任务编排
  - 测试上下文传递
  - 测试异常处理

### 5.2 集成测试/
- [ ] `tests/integration/test_task_flow_execution.py`
  - 测试完整任务流执行
  - 测试跨系统操作
- [ ] 创建测试场景模板
  - 需求查看场景
  - 需求开发场景

### 5.3 端到端测试
- [ ] 手动测试：真实场景验证
- [ ] 性能测试：响应时间、成功率

## 阶段 6：文档与优化

### 6.1 文档
- [ ] 更新 README.md 添加意图识别说明
- [ ] 创建 INTENT.md 意图识别指南
- [ ] 创建 TEMPLATE.md 模板编写指南
- [ ] 添加使用示例

### 6.2 代码质量
- [ ] Black 格式化
- [ ] Ruff 检查
- [ ] Mypy 类型检查

### 6.3 优化
- [ ] 性能优化（缓存、并行执行）
- [ ] 意图识别准确率提升
- [ ] 用户体验优化

## 任务依赖关系

```
1.1 ───> 1.2 ───> 1.3 ───> 1.4
                │
2.1 ───> 2.2 ───> 2.3 ───> 2.4 ───> 2.5
                │
                └──> 3.1 ───> 3.2 ───> 3.3 ───> 3.4 ───> 3.5
                                    │
                                    └──> 4.1 ───> 4.2 ───> 4.3
                                                       │
                                                       └──> 5.1 ───> 5.2 ───> 5.3
                                                                          │
                                                                          └──> 6.1 ───> 6.2 ───> 6.3
```

## 可并行任务

- 1.4（预定义意图）可与 2.4（预定义模板）并行设计
- 5.1（单元测试）可与 4.x（CLI 集成）并行开发
- 6.1（文档）可与 5.3（端到端测试）并行进行

## 验收检查点

1. **阶段 1**：能识别"查看需求并开发"意图，置信度 > 80%
2. **阶段 2**：模板系统能加载和执行预定义流程
3. **阶段 3**：能编排跨系统任务并传递数据
4. **阶段 4**：用户可通过 CLI 触发意图识别
5. **阶段 5**：核心测试覆盖率达到 80% 以上
6. **阶段 6**：文档完整，代码质量达标
