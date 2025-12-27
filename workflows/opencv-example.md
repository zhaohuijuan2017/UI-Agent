---
name: "使用 OpenCV 模板匹配"
description: "演示如何在工作流中使用 OpenCV 模板匹配进行 UI 元素定位"
---

# 使用 OpenCV 模板匹配的工作流

## 步骤

1. 激活 PyCharm 窗口

2. 点击数据库按钮

   ```yaml
   operation: click_database_button
   parameters:
     template: database-button.png
     confidence: 0.8
   ```

3. [if_success] 在终端中输入命令

   ```yaml
   operation: input_text
   parameters:
     template: pycharm-teminal.png
     context_text: 终端
     input_text: python --version
     submit_action: enter
   ```
