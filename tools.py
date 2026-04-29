"""LangChain Tools - Agent 可调用的工具"""

import json
import time
import platform
from typing import Optional

from langchain_core.tools import tool

OS_INFO = f"{platform.system()} {platform.release()}"


@tool
def ask_clarification(reason: str) -> str:
    """当用户的需求不清晰、模糊或信息不足时，调用此工具要求用户重复或补充说明。
    例如：没听清具体软件名称、不确定操作目标、需求有歧义等。

    Args:
        reason: 需要澄清的原因，例如"没听清具体软件名称"
    """
    return json.dumps({
        "action": "clarify",
        "reason": reason,
        "tts_text": f"抱歉，{reason}，能麻烦您再说一遍吗？",
    })


@tool
def generate_command_report(
    description: str,
    overall_risk: str,
    commands_json: str,
    tts_text: str,
) -> str:
    """当用户的需求明确且需要执行系统命令时，调用此工具生成命令执行报告。
    报告包含命令列表、每条命令的风险评级和功能说明。

    Args:
        description: 用户需求的整体描述
        overall_risk: 总体风险等级，可选值: low, medium, high, critical
        commands_json: 命令列表的 JSON 字符串，格式为 [{"step":1,"command":"...","description":"...","risk":"low","risk_reason":"..."}]
        tts_text: 语音说明文本，用亲切自然的语气简述操作原理
    """
    try:
        commands = json.loads(commands_json)
    except json.JSONDecodeError:
        commands = []

    report_id = f"RPT-{time.strftime('%Y%m%d')}-{int(time.time()) % 10000:04d}"

    return json.dumps({
        "action": "report",
        "report_id": report_id,
        "description": description,
        "overall_risk": overall_risk,
        "commands": commands,
        "tts_text": tts_text,
        "ready_tts_text": f"分析完成啦，{report_id} 号报告已经推送到您的工作台，请过目",
    })


@tool
def chat_reply(message: str) -> str:
    """当用户只是闲聊、问问题或不需要执行系统命令时，调用此工具进行自然对话回复。
    例如：打招呼、问天气、闲聊、问知识性问题等。

    Args:
        message: 回复用户的文本，语气自然亲切，适合语音播放
    """
    return json.dumps({
        "action": "chat",
        "message": message,
    })


# 工具列表
TOOLS = [ask_clarification, generate_command_report, chat_reply]
