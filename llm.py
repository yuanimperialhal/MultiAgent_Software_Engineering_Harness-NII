import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import ChatTongyi

def create_llm() -> ChatTongyi:
    """创建所有 Agent 共用的 qwen-plus 模型。"""
    stage_dir = Path(__file__).resolve().parent
    load_dotenv(stage_dir / ".env")

    if not os.getenv("DASHSCOPE_API_KEY"):
        raise ValueError("请在 .env 文件中设置 DASHSCOPE_API_KEY 环境变量。")

    return ChatTongyi(
        model="qwen-plus",
        temperature=0,)