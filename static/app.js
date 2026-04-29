/**
 * 语音命令分析助手 - 前端逻辑 (异步 Agent + 工作台)
 */

const recordBtn = document.getElementById("recordBtn");
const statusEl = document.getElementById("status");
const statusText = statusEl.querySelector(".status-text");
const visualizer = document.getElementById("visualizer");
const vizCtx = visualizer.getContext("2d");
const visualizerWrap = document.getElementById("visualizerWrap");
const workspaceEl = document.getElementById("workspace");
const workspaceEmpty = document.getElementById("workspaceEmpty");
const connectionDot = document.getElementById("connectionDot");
const sidebarToggle = document.getElementById("sidebarToggle");
const sidebar = document.getElementById("sidebar");
const exampleChips = document.getElementById("exampleChips");
const textInput = document.getElementById("textInput");
const textSendBtn = document.getElementById("textSendBtn");
const toastEl = document.getElementById("toast");

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioContext = null;
let analyser = null;
let animationId = null;

// 会话 ID
let sessionId = sessionStorage.getItem("mimo_session_id");
if (!sessionId) {
    sessionId = "sess_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
    sessionStorage.setItem("mimo_session_id", sessionId);
}

// 当前语言
let currentLanguage = null;

// 工作台数据
const workspaceItems = new Map();

// === Toast ===
let toastTimer = null;
function showToast(msg, duration = 2000) {
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), duration);
}

// === SSE 连接 ===
let eventSource = null;

function connectSSE() {
    if (eventSource) eventSource.close();
    eventSource = new EventSource(`/api/events?session_id=${sessionId}`);

    eventSource.onopen = () => {
        connectionDot.classList.remove("disconnected");
        connectionDot.title = "已连接";
    };

    eventSource.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            if (data.event) {
                handleAgentEvent(data.task_id, data.event);
            } else if (data.result) {
                handleTaskComplete(data.task_id, data.result);
            }
        } catch (err) {
            console.error("SSE parse error:", err);
        }
    };

    eventSource.onerror = () => {
        connectionDot.classList.add("disconnected");
        connectionDot.title = "连接断开，正在重连...";
        eventSource.close();
        setTimeout(connectSSE, 3000);
    };
}

connectSSE();

// === 工具函数 ===

function t(zh, en) {
    if (currentLanguage === "en") return en;
    if (currentLanguage === "zh") return zh;
    return zh;
}

function truncate(str, len) {
    return str.length > len ? str.slice(0, len) + "..." : str;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function relativeTime(ts) {
    const diff = Date.now() - ts;
    const sec = Math.floor(diff / 1000);
    if (sec < 60) return "刚刚";
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}分钟前`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}小时前`;
    return new Date(ts).toLocaleDateString("zh-CN");
}

function updateStatus(state, text) {
    statusEl.className = `status ${state}`;
    statusText.textContent = text;
}

// === Canvas Resize ===
function resizeCanvas() {
    const rect = visualizerWrap.getBoundingClientRect();
    visualizer.width = rect.width * window.devicePixelRatio;
    visualizer.height = 60 * window.devicePixelRatio;
    visualizer.style.width = rect.width + "px";
    visualizer.style.height = "60px";
    vizCtx.scale(window.devicePixelRatio, window.devicePixelRatio);
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();

// === 工作台 UI ===

function renderWorkspace() {
    if (workspaceItems.size === 0) {
        workspaceEmpty.classList.remove("hidden");
        const items = workspaceEl.querySelectorAll(".ws-item");
        items.forEach(el => el.remove());
        return;
    }

    workspaceEmpty.classList.add("hidden");

    const sorted = [...workspaceItems.entries()].sort((a, b) => (b[1].timestamp || 0) - (a[1].timestamp || 0));

    let html = "";
    for (const [id, item] of sorted) {
        const timeStr = relativeTime(item.timestamp || Date.now());
        if (item.type === "processing") {
            html += `
            <div class="ws-item processing" data-id="${id}">
                <div class="ws-item-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/>
                    </svg>
                </div>
                <div class="ws-item-info">
                    <div class="ws-item-title">${escapeHtml(truncate(item.transcript, 24))}</div>
                    <div class="ws-item-meta">
                        <span class="ws-item-badge processing-badge">${t("分析中", "Processing")}</span>
                        <span class="ws-item-time">${timeStr}</span>
                    </div>
                </div>
            </div>`;
        } else if (item.type === "executing") {
            html += renderExecutingItem(id, item, timeStr);
        } else if (item.type === "complete") {
            html += renderCompleteItem(id, item, timeStr);
        } else if (item.type === "error") {
            html += `
            <div class="ws-item error-item" data-id="${id}">
                <button class="ws-item-delete" onclick="event.stopPropagation(); deleteWorkspaceItem('${id}')" title="删除">&times;</button>
                <div class="ws-item-icon">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                </div>
                <div class="ws-item-info">
                    <div class="ws-item-title">${escapeHtml(truncate(item.transcript || item.errorMessage || "Error", 24))}</div>
                    <div class="ws-item-meta">
                        <span class="ws-item-badge" style="background:rgba(239,68,68,0.2);color:#f87171">${t("出错", "Error")}</span>
                        <span class="ws-item-time">${timeStr}</span>
                    </div>
                </div>
            </div>`;
        } else if (item.type === "report") {
            const riskLabel = getRiskLabel(item.risk);
            html += `
            <div class="ws-item complete" data-id="${id}" onclick="window.open('/report?id=${item.reportId}','_blank')">
                <button class="ws-item-delete" onclick="event.stopPropagation(); deleteWorkspaceItem('${id}')" title="删除">&times;</button>
                <div class="ws-item-icon">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/>
                    </svg>
                </div>
                <div class="ws-item-info">
                    <div class="ws-item-title">${escapeHtml(truncate(item.transcript, 24))}</div>
                    <div class="ws-item-meta">
                        <span class="ws-item-id">${item.reportId}</span>
                        <span class="ws-item-badge risk-${item.risk}">${riskLabel}</span>
                        <span class="ws-item-time">${timeStr}</span>
                    </div>
                </div>
            </div>`;
        }
    }

    const existingItems = workspaceEl.querySelectorAll(".ws-item");
    existingItems.forEach(el => el.remove());
    workspaceEl.insertAdjacentHTML("beforeend", html);
}

function renderExecutingItem(id, item, timeStr) {
    const title = item.agentTexts.length > 0
        ? escapeHtml(truncate(item.agentTexts[item.agentTexts.length - 1], 24))
        : escapeHtml(truncate(item.transcript || t("执行中...", "Executing..."), 24));

    let stepsHtml = "";
    if (item.steps && item.steps.length > 0) {
        stepsHtml = '<div class="exec-steps">';
        for (const step of item.steps) {
            const statusClass = step.status === "running" ? "step-running"
                : step.status === "done" ? "step-done"
                : step.status === "blocked" ? "step-blocked"
                : step.status === "error" ? "step-error" : "";
            const statusIcon = step.status === "running" ? '<span class="step-spinner"></span>'
                : step.status === "done" ? "&#10003;"
                : step.status === "blocked" ? "&#128683;"
                : step.status === "error" ? "&#10007;" : "";
            stepsHtml += `
            <div class="exec-step ${statusClass}">
                <span class="step-status">${statusIcon}</span>
                <code class="step-cmd">${escapeHtml(truncate(step.command, 40))}</code>
            </div>`;
        }
        stepsHtml += "</div>";
    }

    // 审批面板
    let approvalHtml = "";
    if (item.pendingWarning) {
        const w = item.pendingWarning;
        approvalHtml = `
        <div class="approval-panel">
            <div class="approval-title">${t("需要审批", "Approval Required")}</div>
            <div class="approval-cmd"><code>${escapeHtml(w.command)}</code></div>
            <div class="approval-reason">${escapeHtml(w.reason)}</div>
            <div class="approval-actions">
                <button class="approval-btn approve-once" onclick="approveCommand('${id}', true, 'once')">${t("执行一次", "Approve Once")}</button>
                <button class="approval-btn approve-grant" onclick="approveCommand('${id}', true, 'grant')">${t("本次会话允许", "Allow Session")}</button>
                <button class="approval-btn reject" onclick="approveCommand('${id}', false)">${t("拒绝", "Reject")}</button>
            </div>
        </div>`;
    }

    return `
    <div class="ws-item executing" data-id="${id}">
        <div class="ws-item-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"/>
            </svg>
        </div>
        <div class="ws-item-info">
            <div class="ws-item-title">${title}</div>
            <div class="ws-item-meta">
                <span class="ws-item-badge executing-badge">${t("执行中", "Executing")}</span>
                <span class="ws-item-time">${timeStr}</span>
            </div>
            ${stepsHtml}
            ${approvalHtml}
        </div>
    </div>`;
}

function renderCompleteItem(id, item, timeStr) {
    const title = item.agentTexts && item.agentTexts.length > 0
        ? escapeHtml(truncate(item.agentTexts[item.agentTexts.length - 1], 24))
        : escapeHtml(truncate(item.transcript || t("已完成", "Completed"), 24));

    let stepsHtml = "";
    if (item.steps && item.steps.length > 0) {
        stepsHtml = '<div class="exec-steps">';
        for (const step of item.steps) {
            const statusClass = step.status === "done" ? "step-done"
                : step.status === "blocked" ? "step-blocked"
                : step.status === "error" ? "step-error" : "";
            const statusIcon = step.status === "done" ? "&#10003;"
                : step.status === "blocked" ? "&#128683;"
                : step.status === "error" ? "&#10007;" : "";
            stepsHtml += `
            <div class="exec-step ${statusClass}">
                <span class="step-status">${statusIcon}</span>
                <code class="step-cmd">${escapeHtml(truncate(step.command, 40))}</code>
            </div>`;
        }
        stepsHtml += "</div>";
    }

    return `
    <div class="ws-item complete" data-id="${id}">
        <button class="ws-item-delete" onclick="event.stopPropagation(); deleteWorkspaceItem('${id}')" title="删除">&times;</button>
        <div class="ws-item-icon">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
        </div>
        <div class="ws-item-info">
            <div class="ws-item-title">${title}</div>
            <div class="ws-item-meta">
                <span class="ws-item-badge done-badge">${t("已完成", "Done")}</span>
                <span class="ws-item-time">${timeStr}</span>
            </div>
            ${stepsHtml}
        </div>
    </div>`;
}

function deleteWorkspaceItem(id) {
    workspaceItems.delete(id);
    renderWorkspace();
}

function getRiskLabel(risk) {
    const isEn = currentLanguage === "en";
    const labels = isEn
        ? { low: "Low", medium: "Medium", high: "High", critical: "Critical" }
        : { low: "低", medium: "中", high: "高", critical: "严重" };
    return labels[risk] || risk;
}

// === 录音 ===

async function initRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
        });
        audioContext = new AudioContext();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.8;
        audioContext.createMediaStreamSource(stream).connect(analyser);

        mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = () => {
            const blob = new Blob(audioChunks, { type: "audio/webm" });
            audioChunks = [];
            processAudio(blob);
        };
        return true;
    } catch (err) {
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
            updateStatus("error", "麦克风权限被拒绝，请在浏览器设置中允许");
        } else {
            updateStatus("error", "无法访问麦克风: " + err.message);
        }
        return false;
    }
}

async function startRecording() {
    if (!mediaRecorder && !(await initRecording())) return;
    if (mediaRecorder.state === "recording") return;

    audioChunks = [];
    isRecording = true;
    recordBtn.classList.add("recording");
    recordBtn.querySelector(".btn-text").textContent = t("松开结束", "Release");
    updateStatus("recording", t("正在聆听...", "Listening..."));
    visualizerWrap.classList.add("glow");
    mediaRecorder.start(100);
    drawVisualizer();
}

function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state !== "recording") return;
    isRecording = false;
    recordBtn.classList.remove("recording");
    recordBtn.classList.add("processing");
    recordBtn.querySelector(".btn-text").textContent = t("处理中...", "Processing...");
    recordBtn.disabled = true;
    visualizerWrap.classList.remove("glow");
    mediaRecorder.stop();
    cancelAnimationFrame(animationId);
    clearVisualizer();
}

async function audioToBase64(blob) {
    const buf = await blob.arrayBuffer();
    const bytes = new Uint8Array(buf);
    let bin = "";
    for (let i = 0; i < bytes.byteLength; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
}

async function playAudioBase64(audioB64, contentType) {
    return new Promise((resolve) => {
        const audio = new Audio(`data:${contentType};base64,${audioB64}`);
        audio.onended = resolve;
        audio.onerror = resolve;
        audio.play().catch(resolve);
    });
}

function enableRecording() {
    recordBtn.classList.remove("processing");
    recordBtn.disabled = false;
    recordBtn.querySelector(".btn-text").textContent = t("按住说话", "Hold to speak");
    updateStatus("idle", t("就绪", "Ready"));
}

// === 文字输入 ===

async function submitText(text) {
    if (!text.trim()) return;
    textInput.value = "";
    textInput.disabled = true;
    textSendBtn.disabled = true;

    currentLanguage = "zh"; // default for text input
    updateStatus("processing", t("收到...", "Got it..."));

    try {
        // 提交 agent 分析
        const resp = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text.trim(), session_id: sessionId, language: currentLanguage }),
        });
        const data = await resp.json();

        if (data.task_id) {
            workspaceItems.set(data.task_id, {
                type: "executing",
                transcript: text.trim(),
                steps: [],
                agentTexts: [],
                language: currentLanguage,
                timestamp: Date.now(),
            });
            renderWorkspace();
            showToast(t("已提交执行", "Execution submitted"));
        }
    } catch (err) {
        updateStatus("error", t("提交失败，请重试", "Submit failed, please retry"));
    } finally {
        textInput.disabled = false;
        textSendBtn.disabled = false;
        textInput.focus();
    }
}

textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.isComposing) {
        submitText(textInput.value);
    }
});
textSendBtn.addEventListener("click", () => submitText(textInput.value));

// === 主流程 ===

async function processAudio(audioBlob) {
    updateStatus("processing", t("转录中...", "Transcribing..."));

    try {
        const audioBase64 = await audioToBase64(audioBlob);

        // 1. 转录
        const transcribeResp = await fetch("/api/transcribe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ audio: audioBase64 }),
        });

        if (!transcribeResp.ok) throw new Error(`转录失败: ${transcribeResp.status}`);
        const { transcript, language } = await transcribeResp.json();
        currentLanguage = language || "zh";

        if (!transcript) {
            updateStatus("idle", t("没听清，请再说一遍", "Didn't catch that, please try again"));
            enableRecording();
            return;
        }

        // 显示转录结果
        updateStatus("processing", t(`"${truncate(transcript, 20)}"`, `"${truncate(transcript, 20)}"`));

        // 2. 同步 ack（含意图分类）
        const ackResp = await fetch("/api/ack", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: transcript, session_id: sessionId, language: currentLanguage }),
        }).then(r => r.json()).catch(() => null);

        // 3. 播放 ack
        if (ackResp && ackResp.audio) {
            updateStatus("processing", ackResp.text);
            await playAudioBase64(ackResp.audio, ackResp.content_type);
        }

        // 4. 立即恢复录音
        enableRecording();

        // 5. 只有运维需求才提交 agent 分析，闲聊到此结束
        const intent = ackResp ? ackResp.intent : "ops";
        if (intent === "ops") {
            fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: transcript, session_id: sessionId, language: currentLanguage }),
            }).then(r => r.json()).then(data => {
                if (data.task_id) {
                    workspaceItems.set(data.task_id, {
                        type: "executing",
                        transcript: transcript,
                        steps: [],
                        agentTexts: [],
                        language: currentLanguage,
                        timestamp: Date.now(),
                    });
                    renderWorkspace();
                }
            }).catch(err => {
                console.error("Chat submit failed:", err);
            });
        }

    } catch (err) {
        updateStatus("error", t("分析失败，请重试", "Analysis failed, please retry"));
        enableRecording();
    }
}

// === SSE 事件处理 ===

// Agent 实时执行事件处理
function handleAgentEvent(taskId, event) {
    let item = workspaceItems.get(taskId);

    switch (event.type) {
        case "agent_text":
            // Agent 文字回复 — 更新或创建执行项
            if (!item) {
                item = { type: "executing", transcript: "", steps: [], agentTexts: [], timestamp: Date.now() };
                workspaceItems.set(taskId, item);
            }
            if (event.text) item.agentTexts.push(event.text);
            renderWorkspace();
            break;

        case "tool_call":
            // 即将执行的命令
            if (!item) {
                item = { type: "executing", transcript: "", steps: [], agentTexts: [], timestamp: Date.now() };
                workspaceItems.set(taskId, item);
            }
            item.steps.push({ command: event.command, status: "running", stdout: "", stderr: "", returncode: null });
            renderWorkspace();
            break;

        case "tool_result":
            // 命令执行结果
            if (item && item.steps.length > 0) {
                const lastStep = item.steps[item.steps.length - 1];
                lastStep.status = event.status === "dangerous" ? "blocked" : event.status === "error" ? "error" : "done";
                lastStep.stdout = event.stdout || "";
                lastStep.stderr = event.stderr || "";
                lastStep.returncode = event.returncode;
                lastStep.reason = event.reason || "";
            }
            renderWorkspace();
            break;

        case "warning":
            // 需要审批
            if (item) {
                item.pendingWarning = {
                    command: event.command,
                    reason: event.reason,
                    approvalId: event.approval_id,
                };
            }
            renderWorkspace();
            break;

        case "agent_done":
            // 执行完成
            if (item) {
                item.type = "complete";
                item.completedAt = Date.now();
            }
            renderWorkspace();
            break;

        case "error":
            if (item) {
                item.type = "error";
                item.errorMessage = event.message;
            } else {
                workspaceItems.delete(taskId);
            }
            renderWorkspace();
            break;
    }
}

async function handleTaskComplete(taskId, result) {
    const item = workspaceItems.get(taskId);

    if (result.action === "report") {
        workspaceItems.set(taskId, {
            type: "report",
            transcript: item ? item.transcript : result.report?.transcript || "",
            reportId: result.report_id,
            risk: result.report?.overall_risk || "unknown",
            language: result.report?.language || "zh",
            timestamp: Date.now(),
        });
        renderWorkspace();

        if (result.ready_tts_audio) {
            await playAudioBase64(result.ready_tts_audio, "audio/wav");
        }
        window.open(`/report?id=${result.report_id}`, "_blank");

    } else {
        workspaceItems.delete(taskId);
        renderWorkspace();

        if (result.tts_audio) {
            await playAudioBase64(result.tts_audio, "audio/wav");
        }
    }
}

// 审批操作
async function approveCommand(taskId, approved, mode) {
    try {
        await fetch("/api/approve", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                task_id: taskId,
                approved: approved,
                mode: mode,
            }),
        });
        // 清除 pending warning（SSE 事件会更新最终状态）
        const item = workspaceItems.get(taskId);
        if (item) {
            delete item.pendingWarning;
            renderWorkspace();
        }
        showToast(t(approved ? "已批准" : "已拒绝", approved ? "Approved" : "Rejected"));
    } catch (err) {
        console.error("Approve failed:", err);
        showToast(t("操作失败", "Operation failed"));
    }
}

// === 波形绘制 ===

function drawVisualizer() {
    if (!analyser) return;
    const len = analyser.frequencyBinCount;
    const data = new Uint8Array(len);

    function draw() {
        if (!isRecording) return;
        animationId = requestAnimationFrame(draw);
        analyser.getByteTimeDomainData(data);

        const w = visualizer.width / window.devicePixelRatio;
        const h = 60;
        vizCtx.clearRect(0, 0, w, h);

        // Create gradient
        const grad = vizCtx.createLinearGradient(0, 0, w, 0);
        grad.addColorStop(0, "#6366f1");
        grad.addColorStop(0.5, "#a78bfa");
        grad.addColorStop(1, "#6366f1");

        vizCtx.lineWidth = 2;
        vizCtx.strokeStyle = grad;
        vizCtx.beginPath();

        const sw = w / len;
        let x = 0;
        for (let i = 0; i < len; i++) {
            const y = (data[i] / 128.0) * h / 2;
            i === 0 ? vizCtx.moveTo(x, y) : vizCtx.lineTo(x, y);
            x += sw;
        }
        vizCtx.lineTo(w, h / 2);
        vizCtx.stroke();

        // Glow effect
        vizCtx.shadowColor = "#8b5cf6";
        vizCtx.shadowBlur = 6;
        vizCtx.stroke();
        vizCtx.shadowBlur = 0;
    }
    draw();
}

function clearVisualizer() {
    const w = visualizer.width / window.devicePixelRatio;
    vizCtx.clearRect(0, 0, w, 60);
}

// === 示例 Chips ===

exampleChips.addEventListener("click", (e) => {
    const chip = e.target.closest(".example-chip");
    if (!chip) return;
    const text = chip.dataset.text;
    submitText(text);
});

// === Mobile Sidebar Toggle ===

sidebarToggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
});

// Close sidebar when clicking outside on mobile
document.addEventListener("click", (e) => {
    if (window.innerWidth <= 768 &&
        sidebar.classList.contains("open") &&
        !sidebar.contains(e.target) &&
        e.target !== sidebarToggle &&
        !sidebarToggle.contains(e.target)) {
        sidebar.classList.remove("open");
    }
});

// === 清除上下文 ===

document.getElementById("clearSessionBtn").addEventListener("click", async () => {
    try {
        await fetch("/api/session/clear", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId }),
        });
        // 清除工作台
        workspaceItems.clear();
        renderWorkspace();
        // 生成新 session ID，彻底断开旧上下文
        sessionId = "sess_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
        sessionStorage.setItem("mimo_session_id", sessionId);
        // 重连 SSE
        connectSSE();
        showToast(t("上下文已清除", "Context cleared"));
    } catch (err) {
        console.error("Clear session failed:", err);
    }
});

// === Ripple Effect ===

recordBtn.addEventListener("mousedown", (e) => {
    e.preventDefault();
    recordBtn.classList.add("ripple");
    setTimeout(() => recordBtn.classList.remove("ripple"), 500);
    startRecording();
});

document.addEventListener("mouseup", () => { if (isRecording) stopRecording(); });
recordBtn.addEventListener("touchstart", (e) => { e.preventDefault(); startRecording(); });
document.addEventListener("touchend", () => { if (isRecording) stopRecording(); });
recordBtn.addEventListener("touchmove", (e) => { e.preventDefault(); });
