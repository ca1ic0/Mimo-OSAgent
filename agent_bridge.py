"""桥接层：将 Agent 的 OSAgentSession 封装为可被 Flask 调用的接口"""

import threading
from typing import Any, Callable

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, ToolMessage

from os_agent.audit import AuditLogger
from os_agent.config import Settings
from os_agent.message_utils import parse_json_content, stringify_content
from os_agent.runtime import LocalCommandRunner
from os_agent.session import OSAgentSession, SessionTurnResult

# 加载 .env
load_dotenv()


def _messages_to_events(result: SessionTurnResult) -> list[dict[str, Any]]:
    """将 SessionTurnResult 中的消息转换为 SSE 事件列表"""
    events = []
    for msg in result.new_messages:
        if isinstance(msg, AIMessage):
            text = stringify_content(msg.content)
            if text.strip():
                events.append({"type": "agent_text", "text": text})
            # AIMessage 也可能包含 tool_calls（由 graph 内部处理，这里一般不出现）
        elif isinstance(msg, ToolMessage):
            payload = parse_json_content(msg.content)
            if payload:
                status = payload.get("status", "safe")
                if status == "warning":
                    events.append({
                        "type": "warning",
                        "command": payload.get("command", ""),
                        "reason": payload.get("reason", ""),
                        "approval_id": payload.get("approval_id", ""),
                    })
                elif status == "dangerous":
                    events.append({
                        "type": "tool_result",
                        "status": "dangerous",
                        "command": payload.get("command", ""),
                        "reason": payload.get("reason", ""),
                        "stdout": payload.get("stdout", ""),
                        "stderr": payload.get("stderr", ""),
                        "returncode": payload.get("returncode"),
                    })
                else:
                    events.append({
                        "type": "tool_result",
                        "status": status,
                        "command": payload.get("command", ""),
                        "reason": payload.get("reason", ""),
                        "stdout": payload.get("stdout", ""),
                        "stderr": payload.get("stderr", ""),
                        "returncode": payload.get("returncode"),
                    })
            else:
                text = stringify_content(msg.content)
                if text.strip():
                    events.append({"type": "tool_result", "status": "safe", "command": "", "reason": "", "stdout": text, "stderr": "", "returncode": 0})
    return events


class AgentSession:
    """封装一个 OSAgentSession 实例，线程安全"""

    def __init__(self):
        self._lock = threading.Lock()
        settings = Settings()
        runner = LocalCommandRunner(
            output_limit=settings.command_output_limit,
        )
        audit = AuditLogger()
        self.session = OSAgentSession(
            settings=settings,
            runner=runner,
            audit_logger=audit,
        )

    def handle_user_turn(self, text: str, event_callback: Callable[[dict], None]):
        """执行用户输入，通过 event_callback 推送 SSE 事件"""
        with self._lock:
            result = self.session.handle_user_turn(text)

        if result.error:
            event_callback({"type": "error", "message": str(result.error)})
            return

        events = _messages_to_events(result)
        for ev in events:
            event_callback(ev)

        if result.warning:
            # warning 事件已在 _messages_to_events 中推送
            pass

    def resolve_warning(self, approved: bool, mode: str = "once", event_callback: Callable[[dict], None] | None = None):
        """处理审批决策"""
        with self._lock:
            result = self.session.resolve_warning(approved, mode=mode)

        if result.error and event_callback:
            event_callback({"type": "error", "message": str(result.error)})
            return

        if event_callback:
            events = _messages_to_events(result)
            for ev in events:
                event_callback(ev)

    def reset(self):
        """重置会话"""
        with self._lock:
            self.session.reset_conversation()

    @property
    def has_pending_warning(self) -> bool:
        return self.session.pending_warning is not None


class BridgeSessionManager:
    """管理 session_id → AgentSession 映射"""

    def __init__(self):
        self._sessions: dict[str, AgentSession] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> AgentSession:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = AgentSession()
            return self._sessions[session_id]

    def clear(self, session_id: str):
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            session.reset()


# 全局实例
bridge_session_manager = BridgeSessionManager()
