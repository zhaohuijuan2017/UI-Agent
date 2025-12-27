"""UI-Agent 主程序入口。"""

import os
import sys
from pathlib import Path

import yaml

from src.controller.ide_controller import IDEController
from src.infrastructure.logger import Logger


def get_api_key(config_path: str) -> str | None:
    """获取 API Key，优先从环境变量，然后从配置文件。

    Args:
        config_path: 配置文件路径

    Returns:
        API Key，如果未找到则返回 None
    """
    # 优先从环境变量获取
    api_key = os.environ.get("ZHIPUAI_API_KEY", "")
    if api_key:
        return api_key

    # 从配置文件读取
    config_file = Path(config_path)
    if config_file.exists():
        try:
            with open(config_file, encoding="utf-8") as f:
                content = f.read()
                content = os.path.expandvars(content)
                data = yaml.safe_load(content)

            # 从 api.zhipuai.api_key 获取
            api_key = data.get("api", {}).get("zhipuai", {}).get("api_key", "")
            if api_key:
                return api_key
        except Exception:
            pass

    return None


def print_banner() -> None:
    """打印程序横幅。"""
    print("\n" + "=" * 50)
    print("  UI-Agent - 自然语言控制 PyCharm IDE 系统")
    print("=" * 50 + "\n")


def print_help() -> None:
    """打印帮助信息。"""
    print("\n可用命令:")
    print("  help     - 显示此帮助信息")
    print("  exit     - 退出程序")
    print("  quit     - 退出程序")
    print("  debug    - 启用调试日志")
    print("  nodebug  - 关闭调试日志")
    print("\n示例命令:")
    print("  打开 main.py")
    print("  保存文件")
    print("  跳转到第 50 行")
    print("  运行当前文件")
    print("  格式化代码")
    print("\n命令行选项:")
    print("  --debug, --verbose, -v  - 启用调试日志")
    print("  --template <文件名>      - 指定模板图片")
    print("  --workflow <文件名>      - 执行工作流文件")
    print("  --dry-run                - 验证工作流但不执行")
    print()


def main() -> int:
    """主函数。

    Returns:
        退出代码
    """
    # 解析命令行参数（在初始化日志之前）
    enable_debug = "--debug" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    # 初始化日志
    logger = Logger.get_logger()

    # 如果启用 debug，设置日志级别
    if enable_debug or verbose:
        Logger.set_level("DEBUG")
        print("[调试] Debug 日志已启用")

    # 配置文件路径
    config_path = os.environ.get("UI_AGENT_CONFIG", "config/main.yaml")

    # 获取 API Key（优先环境变量，其次配置文件）
    api_key = get_api_key(config_path)
    if not api_key:
        print("错误: 请设置 ZHIPUAI_API_KEY")
        print("方式1: 设置环境变量 export ZHIPUAI_API_KEY='your-api-key'")
        print("方式2: 在 config/main.yaml 中配置 api.zhipuai.api_key")
        return 1

    try:
        # 初始化控制器
        controller = IDEController(config_path, api_key)
        logger.info("UI-Agent 初始化成功")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        print(f"错误: 初始化失败 - {e}")
        return 1

    # 检查是否是单命令模式
    if len(sys.argv) > 1:
        # 解析命令和参数
        args = sys.argv[1:]
        command_parts = []
        template_name = None
        workflow_file = None
        dry_run = False

        i = 0
        while i < len(args):
            # 跳过选项参数
            if args[i] in ("--debug", "--verbose", "-v"):
                i += 1
            elif args[i] == "--template" and i + 1 < len(args):
                template_name = args[i + 1]
                i += 2
            elif args[i] == "--workflow" and i + 1 < len(args):
                workflow_file = args[i + 1]
                i += 2
            elif args[i] == "--dry-run":
                dry_run = True
                i += 1
            else:
                command_parts.append(args[i])
                i += 1

        # 如果指定了工作流文件，执行工作流
        if workflow_file:
            result = controller.execute_workflow_file(workflow_file, dry_run=dry_run)
            if result.success:
                print(f"\n{result.message}")
                if result.duration_ms > 0:
                    print(f"耗时: {result.duration_ms}ms")
                return 0
            else:
                print(f"\n错误: {result.message}")
                if result.error:
                    try:
                        print(f"详情: {result.error}")
                    except UnicodeEncodeError:
                        error_clean = ''.join(c for c in str(result.error) if c.isprintable() or c.isspace())
                        print(f"详情: {error_clean}")
                return 1

        command = " ".join(command_parts)
        result = controller.execute_command(command, template_name=template_name)

        if result.success:
            print(f"\n{result.message}")
            if result.duration_ms > 0:
                print(f"耗时: {result.duration_ms}ms")
            return 0
        else:
            print(f"\n错误: {result.message}")
            if result.error:
                # 处理可能包含特殊字符的错误信息
                try:
                    print(f"详情: {result.error}")
                except UnicodeEncodeError:
                    # 如果编码失败，移除不可打印字符后再输出
                    error_clean = ''.join(c for c in str(result.error) if c.isprintable() or c.isspace())
                    print(f"详情: {error_clean}")
            return 1

    # 交互式模式
    print_banner()
    print_help()

    print("输入命令 (输入 'help' 查看帮助，'exit' 退出):\n")

    while controller.is_running:
        try:
            command = input(">>> ").strip()

            if not command:
                continue

            if command.lower() in ("exit", "quit"):
                print("\n再见!")
                break

            if command.lower() == "help":
                print_help()
                continue

            # 处理 debug 命令
            if command.lower() == "debug":
                Logger.set_level("DEBUG")
                print("Debug 日志已启用")
                continue

            if command.lower() == "nodebug":
                Logger.set_level("INFO")
                print("Debug 日志已关闭")
                continue

            # 执行命令
            result = controller.execute_command(command)

            if result.success:
                print(f"\n{result.message}")
                if result.duration_ms > 0:
                    print(f"耗时: {result.duration_ms}ms")
            else:
                print(f"\n错误: {result.message}")
                if result.error:
                    # 处理可能包含特殊字符的错误信息
                    try:
                        print(f"详情: {result.error}")
                    except UnicodeEncodeError:
                        # 如果编码失败，移除不可打印字符后再输出
                        error_clean = ''.join(c for c in str(result.error) if c.isprintable() or c.isspace())
                        print(f"详情: {error_clean}")

            print()

        except KeyboardInterrupt:
            print("\n\n使用 'exit' 命令退出程序")
        except EOFError:
            print("\n\n再见!")
            break

    # 清理
    controller.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
