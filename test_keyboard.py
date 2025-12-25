"""测试 keyboard 库是否正常工作。"""

import sys
import time

try:
    import keyboard

    print("keyboard 库已安装")
    print(f"版本: {keyboard.__version__ if hasattr(keyboard, '__version__') else 'unknown'}")

    print("\n请确保 PyCharm 正在运行并处于焦点状态")
    print("3 秒后将测试快捷键 Ctrl+Shift+A...")

    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)

    print("执行快捷键: Ctrl+Shift+A")
    keyboard.press_and_release('ctrl+shift+a')

    print("\n如果 PyCharm 的 'Find Action' 对话框打开了，说明 keyboard 库正常工作")
    print("如果没有打开，可能需要以管理员权限运行此脚本")

except ImportError:
    print("错误: keyboard 库未安装")
    print("请运行: pip install keyboard")
    sys.exit(1)
except Exception as e:
    print(f"错误: {e}")
    print("\n在 Windows 上，keyboard 库可能需要管理员权限")
    print("请尝试以管理员身份运行命令提示符，然后执行此脚本")
    sys.exit(1)
