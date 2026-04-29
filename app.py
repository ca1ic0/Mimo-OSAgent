"""语音命令分析助手 - Flask 后端 (异步 Agent 架构)"""

import base64
import json
import os
import queue
import subprocess
import tempfile
import time
import threading
from threading import Lock

import requests
from flask import Flask, Response, jsonify, request, send_from_directory

import api_config
import config
from agent_bridge import bridge_session_manager
from tts import create_tts_provider

app = Flask(__name__, static_folder="static")

# TTS 提供者（可插拔）
tts_provider = create_tts_provider()

# 报告存储
reports = {}
reports_lock = Lock()

# 异步任务
tasks = {}           # task_id → {status, result, ...}
tasks_lock = Lock()
task_queues = {}     # session_id → queue.Queue
task_queues_lock = Lock()

def get_session_queue(session_id):
    """获取或创建 session 的事件队列"""
    with task_queues_lock:
        if session_id not in task_queues:
            task_queues[session_id] = queue.Queue()
        return task_queues[session_id]


def convert_to_wav(audio_bytes):
    """音频转 WAV"""
    if audio_bytes[:4] == b'RIFF':
        return base64.b64encode(audio_bytes).decode()
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        in_path = f.name
    out_path = in_path.replace(".webm", ".wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", in_path, "-ar", "16000", "-ac", "1", "-f", "wav", out_path],
            capture_output=True, timeout=10,
        )
        with open(out_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def transcribe_audio(wav_b64: str) -> dict:
    """音频转文字，同时识别语言"""
    resp = requests.post(api_config.CHAT_ENDPOINT, headers=api_config.get_headers(), json={
        "model": api_config.AUDIO_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "input_audio", "input_audio": {"data": wav_b64}},
            {"type": "text", "text": "请转录这段音频中的发言内容，并识别用户使用的语言。只返回 JSON 格式：{\"transcript\": \"转录文本\", \"language\": \"zh\"}。language 只能是 zh 或 en。"},
        ]}],
        "temperature": 0.3,
        "max_completion_tokens": 1024,
    }, timeout=30)
    if resp.status_code != 200:
        return {"transcript": "", "language": "zh"}

    content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    try:
        result = json.loads(content)
        transcript = result.get("transcript", "")
        language = result.get("language", "zh")
        if language not in ("zh", "en"):
            language = "zh"
        return {"transcript": transcript, "language": language}
    except json.JSONDecodeError:
        return {"transcript": content, "language": "zh"}


def process_chat_async(task_id, user_text, session_id, language):
    """后台处理 — 通过 Agent 实际执行命令"""
    try:
        agent_session = bridge_session_manager.get_or_create(session_id)
        q = get_session_queue(session_id)

        def event_callback(event):
            q.put({"task_id": task_id, "event": event})

        # Agent 执行用户指令（同步，会通过 callback 推送实时事件）
        agent_session.handle_user_turn(user_text, event_callback)

        # 推送完成事件
        event_callback({"type": "agent_done"})

        # 更新任务状态
        with tasks_lock:
            tasks[task_id]["status"] = "complete"

    except Exception as e:
        error_event = {"type": "error", "message": str(e)}
        with tasks_lock:
            tasks[task_id]["status"] = "error"
        q = get_session_queue(session_id)
        q.put({"task_id": task_id, "event": error_event})


# === 页面路由 ===

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/report")
def report_page():
    return send_from_directory("static", "report.html")


# === API 路由 ===

@app.route("/api/ack", methods=["POST"])
def ack():
    """快速确认 + 意图分类"""
    try:
        data = request.get_json()
        user_text = data.get("text", "")
        sid = data.get("session_id", "default")
        language = data.get("language", "zh")

        if language == "en":
            system_prompt = """You are Qinggenniao, an ops engineer. Return a JSON object:
- "text": brief one-sentence reply
- "intent": "ops" for operational requests (install, check status, configure, troubleshoot), "chat" for greetings/casual chat

Only return JSON, nothing else."""
            user_prompt = f"User said: {user_text}"
            fallback = {"text": "Got it, let me look into it", "intent": "ops"}
        else:
            system_prompt = """你是青耕鸟，一名经验丰富的运维工程师。

分析用户输入，返回一个 JSON 对象，包含两个字段：
- "text": 简短的一句话回复
- "intent": 如果用户提出了明确的运维需求（安装软件、查询系统状态、配置服务、排查故障等），设为 "ops"；如果只是打招呼、闲聊或问一般问题，设为 "chat"

示例：
用户："帮我安装btop" → {"text": "好的，我来查一下怎么安装btop软件", "intent": "ops"}
用户："查看磁盘空间" → {"text": "收到，我看看磁盘使用情况", "intent": "ops"}
用户："你好" → {"text": "你好呀！", "intent": "chat"}
用户："今天天气怎么样" → {"text": "我是运维助手，不过聊聊天也挺好", "intent": "chat"}

只返回 JSON 对象，不要加其他内容。"""
            user_prompt = f"用户说：{user_text}"
            fallback = {"text": "好的，我去看看", "intent": "ops"}

        resp = requests.post(api_config.CHAT_ENDPOINT, headers=api_config.get_headers(), json={
            "model": api_config.AUDIO_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "max_completion_tokens": 512,
        }, timeout=10)

        if resp.status_code == 200:
            raw = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            try:
                # 提取 JSON（可能被 markdown 代码块包裹）
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
                parsed = json.loads(raw.strip())
                ack_text = parsed.get("text", fallback["text"])
                intent = parsed.get("intent", fallback["intent"])
            except (json.JSONDecodeError, KeyError):
                ack_text = raw if raw else fallback["text"]
                intent = fallback["intent"]
        else:
            ack_text = fallback["text"]
            intent = fallback["intent"]

        if intent not in ("ops", "chat"):
            intent = fallback["intent"]

        audio = tts_provider.synthesize(ack_text, language)
        return jsonify({"text": ack_text, "audio": audio, "content_type": "audio/wav", "intent": intent})
    except:
        return jsonify({"text": "好的，稍等", "audio": None, "intent": "ops"}), 200


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    """音频转录"""
    try:
        data = request.get_json()
        audio_b64 = data.get("audio")
        if not audio_b64:
            return jsonify({"error": "缺少音频数据"}), 400

        audio_bytes = base64.b64decode(audio_b64)
        wav_b64 = convert_to_wav(audio_bytes)
        result = transcribe_audio(wav_b64)

        if not result.get("transcript"):
            return jsonify({"error": "未识别到语音内容"}), 400

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Agent 对话入口 — 异步处理"""
    try:
        data = request.get_json()
        user_text = data.get("text", "")
        session_id = data.get("session_id", "default")
        language = data.get("language", "zh")

        if not user_text:
            return jsonify({"error": "缺少文本"}), 400

        # 生成任务 ID
        task_id = f"TASK-{int(time.time() * 1000) % 100000000:08d}"

        # 注册任务
        with tasks_lock:
            tasks[task_id] = {
                "status": "processing",
                "session_id": session_id,
                "transcript": user_text,
                "language": language,
                "created_at": time.time(),
                "result": None,
            }

        # 启动后台线程
        thread = threading.Thread(
            target=process_chat_async,
            args=(task_id, user_text, session_id, language),
            daemon=True,
        )
        thread.start()

        return jsonify({"action": "processing", "task_id": task_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/session/clear", methods=["POST"])
def clear_session():
    """清除会话上下文"""
    try:
        data = request.get_json()
        session_id = data.get("session_id", "default")

        # 清除 Agent 会话
        bridge_session_manager.clear(session_id)

        # 清除该 session 的异步任务
        with tasks_lock:
            to_delete = [tid for tid, t in tasks.items() if t.get("session_id") == session_id]
            for tid in to_delete:
                del tasks[tid]

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/approve", methods=["POST"])
def approve():
    """处理 Agent 命令审批"""
    try:
        data = request.get_json()
        session_id = data.get("session_id", "default")
        approved = data.get("approved", False)
        mode = data.get("mode", "once")  # "once" | "grant"
        task_id = data.get("task_id")

        agent_session = bridge_session_manager.get_or_create(session_id)

        if not agent_session.has_pending_warning:
            return jsonify({"error": "没有待审批的命令"}), 400

        q = get_session_queue(session_id)

        def event_callback(event):
            payload = {"task_id": task_id, "event": event} if task_id else {"event": event}
            q.put(payload)

        agent_session.resolve_warning(approved, mode=mode, event_callback=event_callback)

        # 推送完成事件
        event_callback({"type": "agent_done"})

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/events")
def sse_events():
    """SSE 端点 — 推送任务完成事件"""
    session_id = request.args.get("session_id", "default")
    q = get_session_queue(session_id)

    def generate():
        while True:
            try:
                event = q.get(timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/task/<task_id>")
def get_task(task_id):
    """查询任务状态"""
    with tasks_lock:
        task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify({
        "task_id": task_id,
        "status": task["status"],
        "transcript": task["transcript"],
        "result": task["result"],
    })


@app.route("/api/report/<report_id>", methods=["GET"])
def get_report(report_id):
    with reports_lock:
        report = reports.get(report_id)
    if not report:
        return jsonify({"error": "报告不存在"}), 404
    return jsonify(report)


@app.route("/api/report/<report_id>/complete", methods=["POST"])
def report_complete(report_id):
    """任务完成/失败"""
    try:
        data = request.get_json()
        success = data.get("success", True)
        language = data.get("language", "zh")

        if language == "en":
            text = "Task completed successfully, everything went smoothly!" if success else "Oops, the task failed. Please check the report for details."
        else:
            text = "任务完成啦，一切顺利，没什么问题！" if success else "哎呀，任务出错了，我没搞定，麻烦您看看报告里的详情吧"

        audio = tts_provider.synthesize(text, language)
        return jsonify({"text": text, "audio": audio, "content_type": "audio/wav"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tts", methods=["POST"])
def text_to_speech():
    try:
        data = request.get_json()
        text = data.get("text")
        language = data.get("language", "zh")
        if not text:
            return jsonify({"error": "缺少文本"}), 400
        audio = tts_provider.synthesize(text, language)
        if audio:
            return jsonify({"audio": audio, "content_type": "audio/wav"})
        return jsonify({"error": "TTS 失败"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print(f"服务地址: http://localhost:{config.PORT}")
    print(f"Chat API: {api_config.API_BASE_URL}")
    print(f"TTS  API: {api_config.TTS_API_URL}")
    print(f"TTS Provider: {tts_provider.name}")
    app.run(host="0.0.0.0", port=config.PORT, debug=True)
