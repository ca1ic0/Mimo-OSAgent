# 青耕鸟 — 语音命令分析助手 设计文档

## 1. 项目概述

青耕鸟（Qinggenniao）是一个基于语音交互的智能运维助手。用户通过按住按钮说出运维需求，系统自动完成语音转录、意图识别、命令生成，并以语音和可视化报告的形式反馈结果。

**核心特性：**
- 语音输入 → 实时转录 + 语言检测（中/英双语）
- 智能意图路由：闲聊 / 运维命令 / 需求澄清
- 异步 Agent 分析，用户可连续发令
- 结构化命令报告，含风险评估和 TTS 语音说明
- 可插拔 TTS 提供者架构
- 运维技能手册系统（Skills），提升命令生成质量

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Browser)                        │
│  index.html + app.js + style.css                        │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │
│  │ 录音模块  │  │ SSE 监听 │  │ 工作台 (侧边栏)    │    │
│  └────┬─────┘  └────┬─────┘  └────────────────────┘    │
│       │              │                                   │
└───────┼──────────────┼───────────────────────────────────┘
        │ HTTP         │ SSE
        ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                  Flask 后端 (app.py)                     │
│  ┌────────────┐ ┌──────────┐ ┌───────────────────┐     │
│  │ /api/       │ │ /api/    │ │ /api/chat         │     │
│  │ transcribe  │ │ ack      │ │ (异步, 后台线程)  │     │
│  └──────┬─────┘ └────┬─────┘ └────────┬──────────┘     │
│         │            │                 │                 │
│         ▼            ▼                 ▼                 │
│  ┌──────────────────────────────────────────────┐       │
│  │           api_config.py (API 端点)            │       │
│  └──────────────────────────────────────────────┘       │
│         │            │                 │                 │
│         ▼            ▼                 ▼                 │
│  ┌──────────┐  ┌──────────┐   ┌──────────────┐         │
│  │ MiMo API │  │ MiMo API │   │  agent.py    │         │
│  │ (转录)   │  │ (TTS)    │   │  (意图路由)  │         │
│  └──────────┘  └──────────┘   └──────┬───────┘         │
│                                       │                 │
│                              ┌────────▼────────┐        │
│                              │  skills/*.md    │        │
│                              │  (技能手册)     │        │
│                              └─────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 数据流

```
用户按住说话
    │
    ▼
浏览器录音 (MediaRecorder, webm/opus)
    │
    ▼
POST /api/transcribe
    │ ffmpeg 转 WAV → MiMo 多模态模型
    ▼
返回 {transcript, language}
    │
    ├─→ POST /api/ack (同步)
    │       │ MiMo LLM 生成上下文感知的简短回复
    │       │ TTS 合成语音
    │       ▼
    │   播放确认语音 → 立即恢复录音
    │
    └─→ POST /api/chat (异步)
            │ 生成 task_id → 启动后台线程 → 立即返回
            │
            ▼ (后台线程)
        agent.process_input()
            │ 匹配 skills → 注入 system prompt → LLM 推理
            ▼
        ┌─ clarify → TTS → SSE 推送
        ├─ report  → 生成报告 → 存储 → TTS → SSE 推送
        └─ chat    → TTS → SSE 推送
                        │
                        ▼
            前端 SSE 接收 → 播放 TTS / 打开报告页
```

---

## 3. 模块说明

### 3.1 后端模块

| 文件 | 职责 |
|------|------|
| `app.py` | Flask 主应用，路由定义，异步任务管理，SSE 推送 |
| `agent.py` | 意图路由引擎，会话管理，技能手册加载与匹配 |
| `api_config.py` | API 端点、Token、模型名称等外部服务配置 |
| `config.py` | 应用级配置（端口号等） |
| `tools.py` | LangChain 工具定义（预留，当前未启用） |
| `tts/` | TTS 抽象层，可插拔提供者 |
| `skills/` | 运维技能手册（Markdown + YAML frontmatter） |

### 3.2 TTS 抽象层

```
tts/
├── __init__.py     # 工厂函数 create_tts_provider()
├── base.py         # TTSProvider 抽象基类
└── mimo.py         # MiMoTTS 实现
```

**接口定义：**

```python
class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, language: str = "zh") -> Optional[str]:
        """文本 → base64 WAV，失败返回 None"""
        pass
```

**扩展方式：** 继承 `TTSProvider`，实现 `synthesize` 方法，通过 `register_tts_provider()` 注册。

### 3.3 技能手册系统

每个 skill 是一个 Markdown 文件，包含 YAML frontmatter 和操作指南：

```yaml
---
name: network-diagnostics
triggers:
  zh: ["网络", "ping", "连不上", ...]
  en: ["network", "ping", "connection", ...]
os: [darwin, linux]
---
```

**匹配流程：**
1. `load_all_skills()` — import 时一次性加载所有 skill 文件
2. `select_skills(user_text)` — 按关键词命中数打分，取 top 2
3. 命中的 skill 内容追加到 system prompt，LLM 参考生成命令

**当前 Skills：**

| Skill | 覆盖场景 |
|-------|----------|
| network-diagnostics | ping, DNS, traceroute, 端口检查 |
| disk-management | df, du, 磁盘清理, diskutil |
| process-management | ps, top, kill, lsof, 僵尸进程 |
| package-management | Homebrew, apt, dnf |
| system-monitoring | vm_stat, sysctl, load average |
| log-analysis | log show, journalctl, dmesg |
| service-management | launchctl, systemctl |
| ssh-remote | SSH 连接, 密钥, scp, 端口转发 |

### 3.4 前端模块

| 文件 | 职责 |
|------|------|
| `index.html` | 主页面：录音按钮 + 工作台侧边栏 |
| `app.js` | 录音、转录、ack 播放、SSE 监听、工作台渲染 |
| `report.html` | 报告详情页：命令列表、TTS 播放、任务状态 |
| `style.css` | 全局样式，响应式布局 |

**关键交互：**
- 按住录音 → 松开转录 → 同步 ack → 立即恢复录音 → 异步 Agent 分析
- SSE 推送完成事件 → 工作台更新 → 播放 TTS / 打开报告
- 报告页自动播放 TTS 语音说明

---

## 4. API 参考

### 页面路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 主页面 |
| GET | `/report?id=xxx` | 报告详情页 |

### API 端点

| 方法 | 路径 | 说明 | 同步/异步 |
|------|------|------|-----------|
| POST | `/api/transcribe` | 音频转录 + 语言检测 | 同步 |
| POST | `/api/ack` | 快速上下文确认 + TTS | 同步 |
| POST | `/api/chat` | 提交 Agent 分析任务 | 异步（返回 task_id） |
| GET | `/api/events?session_id=xxx` | SSE 事件流 | 长连接 |
| GET | `/api/task/<task_id>` | 查询任务状态 | 同步 |
| GET | `/api/report/<report_id>` | 获取报告数据 | 同步 |
| POST | `/api/report/<report_id>/complete` | 标记任务完成/失败 + TTS | 同步 |
| POST | `/api/tts` | 通用 TTS 合成 | 同步 |

### 请求/响应格式

**POST /api/transcribe**
```json
// Request
{"audio": "<base64 webm/opus>"}
// Response
{"transcript": "帮我安装btop", "language": "zh"}
```

**POST /api/chat**
```json
// Request
{"text": "帮我安装btop", "session_id": "sess_xxx", "language": "zh"}
// Response (immediate)
{"action": "processing", "task_id": "TASK-12345678"}
```

**SSE Event (via /api/events)**
```json
{"task_id": "TASK-12345678", "result": {"action": "report", "report_id": "RPT-...", "report": {...}}}
```

---

## 5. 配置说明

### api_config.py

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `API_BASE_URL` | MiMo API 基础地址 | `https://token-plan-cn.xiaomimimo.com/v1` |
| `API_TOKEN` | API 认证 Token | (项目内置) |
| `AUDIO_MODEL` | LLM / 转录模型 | `mimo-v2.5` |
| `TTS_MODEL` | TTS 模型 | `mimo-v2.5-tts` |
| `TTS_VOICE` | TTS 语音音色 | `Chloe` |
| `TTS_PROVIDER` | TTS 提供者名称 | `mimo` |

### config.py

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PORT` | 服务监听端口 | `5001` |

---

## 6. 部署与运行

### 环境要求

- Python 3.9+
- ffmpeg（用于音频格式转换）
- MiMo API 访问权限

### 安装

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 确保 ffmpeg 已安装
ffmpeg -version
```

### 启动

```bash
source venv/bin/activate
python3 app.py
# 服务地址: http://localhost:5001
```

### 依赖

```
flask>=3.0.0
requests>=2.31.0
langchain>=0.3.0
langchain-openai>=0.2.0
```

---

## 7. 扩展指南

### 添加新的 TTS 提供者

1. 创建 `tts/your_provider.py`，继承 `TTSProvider`
2. 实现 `synthesize(text, language) -> Optional[str]`
3. 在 `tts/__init__.py` 中注册：
   ```python
   from tts.your_provider import YourTTS
   _PROVIDERS["your_name"] = YourTTS
   ```
4. 修改 `api_config.TTS_PROVIDER = "your_name"`

### 添加新的技能手册

1. 在 `skills/` 目录创建 `your-skill.md`
2. 添加 YAML frontmatter（name, triggers, os）
3. 编写操作流程（表格格式，含命令/说明/风险）
4. 重启服务，新 skill 自动加载

### 切换 LLM 后端

修改 `api_config.py` 中的 `API_BASE_URL`、`API_TOKEN`、`AUDIO_MODEL` 即可。
Agent 使用 LangChain `ChatOpenAI`，兼容所有 OpenAI API 兼容的后端。
