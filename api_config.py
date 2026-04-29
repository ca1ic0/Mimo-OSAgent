"""API 配置 - 所有外部服务的连接参数

本文件集中管理:
- MiMo LLM API（对话、转录、ack）
- MiMo TTS API（语音合成）
- 模型名称、语音参数
- 认证凭据

优先从环境变量 / .env 文件读取。
"""

import os
from dotenv import load_dotenv

load_dotenv()

# === MiMo API 基础配置 ===

API_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
API_TOKEN = os.environ.get("OPENAI_API_KEY", "")
if not API_TOKEN:
    raise RuntimeError(
        "缺少 OPENAI_API_KEY，请在 .env 文件或环境变量中设置。"
        "参考 .env.example"
    )

# === LLM 模型 ===

AUDIO_MODEL = os.environ.get("OPENAI_MODEL", "mimo-v2.5")

# === TTS 配置 ===

TTS_API_URL = os.environ.get("TTS_API_URL", API_BASE_URL)
TTS_MODEL = os.environ.get("TTS_MODEL", "mimo-v2.5-tts")
TTS_VOICE = os.environ.get("TTS_VOICE", "Chloe")
TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "mimo")

# === 派生端点（由上面的配置自动拼接）===

CHAT_ENDPOINT = f"{API_BASE_URL}/chat/completions"
TTS_ENDPOINT = f"{TTS_API_URL}/chat/completions"


# === 通用工具函数 ===

def get_headers():
    """获取 API 请求头"""
    return {"api-key": API_TOKEN, "Content-Type": "application/json"}
