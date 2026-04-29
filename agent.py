"""LangChain Agent - 意图路由和对话管理（基于结构化输出）"""

import json
import os
import platform

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

import api_config

OS_INFO = f"{platform.system()} {platform.release()}"

# === 技能手册系统 ===

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills")


def _parse_frontmatter(content):
    """手动解析 YAML frontmatter，不引入 pyyaml 依赖"""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm = {}
    current_key = None
    current_lang = None

    for raw_line in parts[1].strip().split("\n"):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip())

        # 顶级 key: value（无缩进）
        if indent == 0 and ": " in stripped:
            key, val = stripped.split(": ", 1)
            key, val = key.strip(), val.strip()
            if val.startswith("["):
                fm[key] = [x.strip().strip('"').strip("'") for x in val.strip("[]").split(",")]
            else:
                fm[key] = val.strip('"').strip("'")
            current_key = key
            current_lang = None
            continue

        # 顶级 key:（无值，如 triggers:）
        if indent == 0 and stripped.endswith(":"):
            current_key = stripped[:-1].strip()
            current_lang = None
            continue

        # 缩进行：子键或列表项
        if indent > 0:
            # 子键 zh: [...] 或 en: [...]
            if ": " in stripped:
                sub_key, val = stripped.split(": ", 1)
                sub_key, val = sub_key.strip(), val.strip()
                if current_key == "triggers":
                    current_lang = sub_key
                    if "triggers" not in fm:
                        fm["triggers"] = {}
                    if val.startswith("["):
                        fm["triggers"][sub_key] = [x.strip().strip('"').strip("'") for x in val.strip("[]").split(",")]
                    else:
                        fm["triggers"][sub_key] = [val.strip('"').strip("'")]
                continue

            # 子键无值（如 zh: 后面跟列表）
            if stripped.endswith(":") and current_key == "triggers":
                current_lang = stripped[:-1].strip()
                if "triggers" not in fm:
                    fm["triggers"] = {}
                fm["triggers"][current_lang] = []
                continue

            # 列表项 - "xxx"
            if stripped.startswith("- ") and current_lang and "triggers" in fm:
                val = stripped[2:].strip().strip('"').strip("'")
                fm["triggers"][current_lang].append(val)

    return fm, parts[2].strip()


def load_all_skills():
    """加载 skills/ 目录下所有 .md 技能手册"""
    skills = []
    if not os.path.isdir(SKILLS_DIR):
        return skills
    for fname in sorted(os.listdir(SKILLS_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(SKILLS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        fm, body = _parse_frontmatter(content)
        skills.append({
            "name": fm.get("name", fname.replace(".md", "")),
            "triggers": fm.get("triggers", {}),
            "os": fm.get("os", ["darwin", "linux"]),
            "content": body,
        })
    return skills


def select_skills(user_text, skills, max_skills=2):
    """按关键词匹配打分，返回 top N 适用的技能手册"""
    text_lower = user_text.lower()
    current_os = platform.system().lower()
    scored = []
    for skill in skills:
        if current_os not in skill.get("os", [current_os]):
            continue
        score = 0
        for lang_key in ["zh", "en"]:
            for kw in skill["triggers"].get(lang_key, []):
                if kw.lower() in text_lower:
                    score += 1
        if score > 0:
            scored.append((score, skill))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:max_skills]]


ALL_SKILLS = load_all_skills()

SYSTEM_PROMPT_ZH = """你是青耕鸟，一名具有丰富行业经验的运维工程师。你通过语音与用户交流，擅长快速定位和解决系统问题。

当前操作系统环境：""" + OS_INFO + """

你的核心任务是分析用户意图并返回一个 JSON 对象。不要返回其他内容，只返回 JSON。

## 意图分类规则

根据用户输入，判断属于以下哪种意图，返回对应的 JSON：

### 1. 需要澄清（clarify）
当用户需求不清晰、模糊、信息不足时：
{"action": "clarify", "reason": "没听清具体软件名称"}

### 2. 需要执行系统命令（report）
当用户明确要求安装软件、配置系统、执行操作等需要生成命令报告时：
{"action": "report", "description": "用户需求的整体描述", "overall_risk": "low", "commands": [{"step": 1, "command": "具体命令", "description": "命令说明", "risk": "low", "risk_reason": "风险说明"}], "tts_text": "用亲切自然的语气简述操作原理和步骤"}

命令风险等级说明：
- low: 只读操作、标准软件安装
- medium: 修改配置文件
- high: 删除文件、修改系统设置
- critical: 格式化、权限修改

### 3. 闲聊（chat）
当用户只是打招呼、闲聊、问知识性问题、不需要系统操作时：
{"action": "chat", "message": "自然亲切的回复文本，适合语音播放"}

## 重要规则
- 只返回 JSON，不要返回其他任何内容
- 语音回复要自然亲切，避免使用 markdown 格式
- 命令列表要最小化，只包含必要的步骤
- 如果不确定用户的意图，返回 clarify
- 所有字段值（description, tts_text, message, reason 等）必须使用中文
"""

SYSTEM_PROMPT_EN = """You are Qinggenniao, an experienced operations engineer with rich industry expertise. You communicate with users via voice and excel at quickly diagnosing and resolving system issues.

Current OS environment: """ + OS_INFO + """

Your core task is to analyze user intent and return a JSON object. Do not return anything else, only JSON.

## Intent Classification Rules

Based on user input, determine which intent it belongs to and return the corresponding JSON:

### 1. Clarification needed (clarify)
When the user's request is unclear, ambiguous, or lacks information:
{"action": "clarify", "reason": "didn't catch the specific software name"}

### 2. System command execution (report)
When the user explicitly requests to install software, configure the system, or perform operations that require a command report:
{"action": "report", "description": "overall description of user request", "overall_risk": "low", "commands": [{"step": 1, "command": "specific command", "description": "command description", "risk": "low", "risk_reason": "risk explanation"}], "tts_text": "brief explanation of the operation in a warm and natural tone"}

Command risk levels:
- low: read-only operations, standard software installation
- medium: modifying configuration files
- high: deleting files, changing system settings
- critical: formatting, permission changes

### 3. Chat (chat)
When the user is just greeting, chatting, asking knowledge questions, or doesn't need system operations:
{"action": "chat", "message": "natural and friendly reply text, suitable for voice playback"}

## Important Rules
- Only return JSON, do not return any other content
- Voice replies should be natural and friendly, avoid markdown format
- Command list should be minimal, only include necessary steps
- If unsure about user intent, return clarify
- All field values (description, tts_text, message, reason, etc.) must be in English
"""


def create_llm():
    """创建 LLM 实例"""
    return ChatOpenAI(
        base_url=api_config.API_BASE_URL,
        api_key=api_config.API_TOKEN,
        model=api_config.AUDIO_MODEL,
        temperature=0.3,
        max_tokens=2048,
    )


class SessionManager:
    """管理多轮对话的会话状态"""

    def __init__(self):
        self.sessions = {}

    def get_history(self, session_id: str) -> list:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str):
        history = self.get_history(session_id)
        if role == "user":
            history.append(HumanMessage(content=content))
        elif role == "assistant":
            history.append(AIMessage(content=content))

        # 压缩：保留最近 20 条消息
        if len(history) > 20:
            old = history[:10]
            summary = "; ".join(
                f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content[:50]}"
                for m in old
            )
            history = [SystemMessage(content=f"Previous conversation summary: {summary}")] + history[10:]
            self.sessions[session_id] = history

    def clear(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]


# 全局实例
session_manager = SessionManager()
_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = create_llm()
    return _llm


def process_input(user_text: str, session_id: str = "default", language: str = "zh") -> dict:
    """处理用户输入，返回路由结果"""
    llm = get_llm()
    history = session_manager.get_history(session_id)

    # 根据语言选择系统提示词
    system_prompt = SYSTEM_PROMPT_EN if language == "en" else SYSTEM_PROMPT_ZH

    # 匹配技能手册并注入 system prompt
    selected = select_skills(user_text, ALL_SKILLS)
    if selected:
        skill_header = (
            "\n\n## 参考技能手册\n以下是从运维知识库中匹配到的相关操作手册，请作为参考生成命令"
            "（根据实际需求灵活调整，不必完全照搬）：\n"
            if language == "zh"
            else "\n\n## Reference Skill Manuals\nThe following operation manuals matched from the ops knowledge base. "
            "Use them as reference to generate commands (adapt as needed, no need to follow exactly):\n"
        )
        skill_context = skill_header
        for skill in selected:
            skill_context += f"\n### {skill['name']}\n{skill['content']}\n"
        system_prompt += skill_context

    # 构建消息列表
    messages = [SystemMessage(content=system_prompt)]
    for msg in history:
        messages.append(msg)
    messages.append(HumanMessage(content=user_text))

    try:
        result = llm.invoke(messages)
        content = result.content.strip()

        # 提取 JSON（可能被 markdown 代码块包裹）
        if content.startswith("```"):
            lines = content.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    json_lines.append(line)
            content = "\n".join(json_lines)

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"action": "chat", "message": content}

        # 记录对话历史
        session_manager.add_message(session_id, "user", user_text)
        if parsed.get("action") == "chat":
            session_manager.add_message(session_id, "assistant", parsed.get("message", ""))
        elif parsed.get("action") == "report":
            session_manager.add_message(session_id, "assistant", f"[Report] {parsed.get('description', '')}")
        elif parsed.get("action") == "clarify":
            session_manager.add_message(session_id, "assistant", f"[Clarify] {parsed.get('reason', '')}")

        return parsed

    except Exception as e:
        return {"action": "chat", "message": f"Error: {str(e)}"}
