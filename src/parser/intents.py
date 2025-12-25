"""意图类型定义。"""

from enum import Enum


class IntentType(Enum):
    """命令意图类型枚举。"""

    # 文件操作
    FILE_OPERATION = "file_operation"

    # 编辑操作
    EDIT = "edit"

    # 导航操作
    NAVIGATION = "navigation"

    # 重构操作
    REFACTOR = "refactor"

    # 运行操作
    RUN = "run"

    # 搜索操作
    SEARCH = "search"

    # 未知意图
    UNKNOWN = "unknown"


# 意图关键词映射
INTENT_KEYWORDS = {
    IntentType.FILE_OPERATION: [
        "打开",
        "关闭",
        "保存",
        "新建",
        "删除",
        "open",
        "close",
        "save",
        "new",
        "file",
    ],
    IntentType.EDIT: [
        "复制",
        "粘贴",
        "剪切",
        "删除",
        "撤销",
        "重做",
        "copy",
        "paste",
        "cut",
        "undo",
        "redo",
    ],
    IntentType.NAVIGATION: [
        "跳转",
        "转到",
        "查找",
        "定位",
        "goto",
        "jump",
        "navigate",
    ],
    IntentType.REFACTOR: [
        "重命名",
        "提取",
        "格式化",
        "优化",
        "rename",
        "extract",
        "format",
        "optimize",
        "refactor",
    ],
    IntentType.RUN: [
        "运行",
        "执行",
        "调试",
        "测试",
        "run",
        "execute",
        "debug",
        "test",
    ],
    IntentType.SEARCH: [
        "搜索",
        "查找",
        "替换",
        "search",
        "find",
        "replace",
    ],
}
