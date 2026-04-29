# 青耕鸟 运维助手 (Mimo-OSAgent)

一个**语音交互式 AI 运维助手**。用自然语言说出你的运维需求，系统自动识别意图、生成命令、评估风险并执行，全程语音反馈。

## 功能特性

- **语音输入** — 按住麦克风说话，支持中英文自动识别
- **智能意图识别** — 自动区分运维指令、闲聊和需要澄清的请求
- **风险评估** — 每条命令标注风险等级（低/中/高/危急），高危命令需确认
- **语音播报** — TTS 语音反馈执行计划和结果
- **实时工作台** — 侧边栏实时显示任务状态（处理中/执行中/已完成/出错）
- **技能手册** — 内置 8 类运维知识库（网络诊断、磁盘管理、进程管理等）

## 快速开始

### 环境要求

- Python 3.9+
- ffmpeg（用于音频格式转换）

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd Mimo-OSAgent

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 配置

复制环境变量模板并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 必填：MiMo API 密钥
OPENAI_API_KEY=your-api-key-here

# 以下为默认值，通常无需修改
OPENAI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
OPENAI_MODEL=mimo-v2.5
TTS_API_URL=https://token-plan-cn.xiaomimimo.com/v1
TTS_MODEL=mimo-v2.5-tts
TTS_VOICE=Chloe
TTS_PROVIDER=mimo
```

### 运行

```bash
source venv/bin/activate
python3 app.py
```

浏览器打开 http://localhost:5001 即可使用。

## 使用方式

1. **语音输入** — 按住页面中央的麦克风按钮，说出运维需求
2. **文字输入** — 也可以在底部输入框直接打字
3. **快捷操作** — 点击页面上的示例标签快速发起请求
4. **查看报告** — 任务完成后可在工作台查看详细报告，支持复制命令和语音播报

### 示例

- "帮我看看磁盘使用情况"
- "检查一下系统内存"
- "安装 btop 监控工具"
- "查看 Nginx 服务状态"

## 项目结构

```
Mimo-OSAgent/
├── app.py              # Flask 主应用（路由、异步任务、SSE）
├── agent.py            # LangChain 意图识别与命令生成
├── agent_bridge.py     # Agent 桥接层
├── tools.py            # LangChain 工具定义
├── api_config.py       # API 配置
├── config.py           # 应用配置
├── tts/                # TTS 语音合成模块
│   ├── base.py         # TTS 提供者基类
│   └── mimo.py         # MiMo TTS 实现
├── skills/             # 运维技能知识库（8 类）
├── static/             # 前端页面
│   ├── index.html      # 主页面
│   ├── app.js          # 前端逻辑
│   ├── report.html     # 报告详情页
│   └── style.css       # 样式
└── artifacts/          # 运行时审计日志
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python / Flask |
| AI 框架 | LangChain + LangGraph |
| 语音识别 | MiMo 多模态模型 |
| 语音合成 | MiMo TTS |
| 前端 | 原生 HTML/JS/CSS |
| 实时通信 | Server-Sent Events (SSE) |

## 许可证

MIT
