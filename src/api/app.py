"""UI-Agent HTTP API 服务器。"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import ConfigManager
from src.config.schema import MainConfig
from src.controller.ide_controller import IDEController


# 全局控制器实例
controller: IDEController | None = None
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    global controller
    # 启动时初始化
    try:
        controller = init_controller()
        logger.info("UI-Agent API 服务器启动成功")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise
    yield
    # 关闭时清理
    logger.info("UI-Agent API 服务器关闭")


class IntentRequest(BaseModel):
    """意图识别请求。"""

    message: str
    execute: bool = True  # 是否执行任务，False 仅返回识别结果


class IntentResponse(BaseModel):
    """意图识别响应。"""

    success: bool
    message: str
    intent_type: str | None = None
    confidence: float | None = None
    parameters: dict[str, Any] | None = None
    execution_plan: dict[str, Any] | None = None
    execution_result: dict[str, Any] | None = None
    error: str | None = None


# 创建 FastAPI 应用
app = FastAPI(
    title="UI-Agent API",
    description="基于意图识别的任务编排 API",
    version="1.0.0",
    lifespan=lifespan,
)


def get_api_key() -> str:
    """获取 API Key。"""
    api_key = os.environ.get("ZHIPUAI_API_KEY", "")
    if api_key:
        return api_key

    # 从配置文件读取
    config_path = os.environ.get("UI_AGENT_CONFIG", "config/main.yaml")
    config_manager = ConfigManager(config_path)
    config: MainConfig = config_manager.load_config()
    return config.api.zhipuai_api_key


def init_controller() -> IDEController:
    """初始化 IDE 控制器。"""
    config_path = os.environ.get("UI_AGENT_CONFIG", "config/main.yaml")
    api_key = get_api_key()

    if not api_key:
        raise ValueError("请设置 ZHIPUAI_API_KEY 环境变量或在配置文件中配置")

    controller = IDEController(config_path, api_key)

    # 打印配置信息
    if controller.config.api.base_url:
        logger.info(f"使用自定义 LLM API: {controller.config.api.base_url}")
    else:
        logger.info("使用官方 LLM API")

    return controller


@app.get("/")
async def root():
    """根路径。"""
    return {
        "name": "UI-Agent API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "POST /api/intent": "意图识别和任务执行",
            "GET /api/health": "健康检查",
            "GET /api/intents": "列出所有可用意图",
        },
    }


@app.get("/api/health")
async def health_check():
    """健康检查。"""
    return {"status": "healthy", "controller_initialized": controller is not None}


@app.get("/api/intents")
async def list_intents():
    """列出所有可用的意图类型。"""
    if not controller or not controller._intent_recognizer:
        raise HTTPException(status_code=503, detail="意图识别器未初始化")

    intents = controller._intent_recognizer.get_available_intents()
    intent_details = []

    for intent_name in intents:
        definition = controller._intent_recognizer.get_intent_definition(intent_name)
        if definition:
            intent_details.append(
                {
                    "name": intent_name,
                    "description": definition.description,
                    "type": definition.type,
                    "system": definition.system,
                    "systems": definition.systems,
                    "parameters": {
                        name: {
                            "type": param.type,
                            "description": param.description,
                            "required": param.required,
                        }
                        for name, param in definition.parameters.items()
                    },
                }
            )

    return {"intents": intent_details}


@app.post("/api/intent", response_model=IntentResponse)
async def recognize_intent(request: IntentRequest) -> IntentResponse:
    """识别意图并执行任务。

    Args:
        request: 意图识别请求

    Returns:
        意图识别响应
    """
    if not controller:
        raise HTTPException(status_code=503, detail="控制器未初始化")

    if not controller._intent_recognizer:
        raise HTTPException(status_code=503, detail="意图识别器未初始化")

    try:
        # 识别意图
        intent_result = controller._intent_recognizer.recognize(request.message)

        if not intent_result.has_match:
            return IntentResponse(
                success=False,
                message="未识别到匹配的意图",
                error="No matching intent found",
            )

        # 准备响应
        response = IntentResponse(
            success=True,
            message=f"识别到意图: {intent_result.intent.type}",
            intent_type=intent_result.intent.type,
            confidence=intent_result.confidence,
            parameters=intent_result.intent.parameters,
        )

        # 如果不执行，仅返回识别结果
        if not request.execute:
            return response

        # 获取执行计划
        if controller._task_orchestrator:
            response.execution_plan = controller._task_orchestrator.show_execution_plan(
                intent_result.intent
            )

            # 执行任务
            context = controller._task_orchestrator.orchestrate(intent_result.intent)

            response.execution_result = {
                "status": context.status,
                "summary": context.get_execution_summary(),
                "steps": [
                    {
                        "index": r.step_index,
                        "success": r.success,
                        "output": r.output,
                        "error": r.error,
                    }
                    for r in context.step_results
                ],
            }

            if context.status == "completed":
                response.message = f"任务执行成功: {intent_result.intent.type}"
            else:
                response.success = False
                response.message = f"任务执行失败: {intent_result.intent.type}"
                response.error = context.get_execution_summary()

        return response

    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        return IntentResponse(
            success=False,
            message="处理请求失败",
            error=str(e),
        )


def main():
    """启动 API 服务器。"""
    import argparse

    parser = argparse.ArgumentParser(description="UI-Agent HTTP API 服务器")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="自动重载（开发模式）")
    parser.add_argument("--log-level", default="info", help="日志级别")
    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 检查 API Key
    if not get_api_key():
        print("错误: 请设置 ZHIPUAI_API_KEY 环境变量")
        print("示例: export ZHIPUAI_API_KEY='your-api-key'")
        sys.exit(1)

    print("=" * 60)
    print("UI-Agent HTTP API 服务器")
    print("=" * 60)
    print(f"监听地址: http://{args.host}:{args.port}")
    print(f"API 文档: http://{args.host}:{args.port}/docs")
    print(f"健康检查: http://{args.host}:{args.port}/api/health")
    print("=" * 60)

    # 启动服务器
    uvicorn.run(
        "src.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
