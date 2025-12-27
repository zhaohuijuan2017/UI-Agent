---
name: "条件分支示例"
description: "演示条件分支和重试机制"
---

# 条件分支示例工作流

## 步骤

1. 激活 PyCharm 窗口

2. 打开文件 main.py

   ```yaml
   operation: double_click_file
   parameters:
     filename: "main.py"
   retry_count: 2
   retry_interval: 1.0
   ```

3. [if_success] 跳转到第 42 行

   ```yaml
   operation: go_to_line
   parameters:
     line_number: 42
   ```

4. [if_failure] 显示错误提示

   ```yaml
   operation: input_text
   parameters:
     context_text: "搜索"
     input_text: "文件打开失败"
   continue_on_error: true
   ```
