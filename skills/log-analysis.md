---
name: log-analysis
triggers:
  zh: ["日志", "log", "报错", "错误", "异常", "崩溃", "crash", "排错", "调试", "debug", "查看日志", "系统日志"]
  en: ["log", "logs", "error", "crash", "debug", "troubleshoot", "syslog", "journal", "dmesg"]
os: [darwin, linux]
---

# 日志分析 (Log Analysis)

## 适用场景
- 查看系统日志排查错误
- 查找应用崩溃原因
- 分析系统异常事件
- 查看内核日志

## macOS 日志系统

### 基础查询
| 命令 | 说明 | 风险 |
|------|------|------|
| `log show --last 1h` | 查看最近 1 小时的所有日志 | low |
| `log show --last 10m` | 查看最近 10 分钟的日志 | low |
| `log show --predicate 'process == "进程名"' --last 1h` | 按进程过滤日志 | low |
| `log show --predicate 'eventMessage contains "关键词"' --last 1h` | 按内容搜索 | low |

### 实时流式日志
| 命令 | 说明 | 风险 |
|------|------|------|
| `log stream` | 实时查看所有日志流 | low |
| `log stream --predicate 'process == "进程名"'` | 实时查看指定进程日志 | low |
| `log stream --level error` | 只看错误级别日志 | low |

### 系统日志文件
| 命令 | 说明 | 风险 |
|------|------|------|
| `ls ~/Library/Logs/` | 查看用户级应用日志目录 | low |
| `ls /var/log/` | 查看系统日志目录 | low |
| `cat /var/log/system.log` | 查看系统日志（旧版 macOS） | low |

### 崩溃日志
| 命令 | 说明 | 风险 |
|------|------|------|
| `ls ~/Library/Logs/DiagnosticReports/` | 查看用户级崩溃报告 | low |
| `ls /Library/Logs/DiagnosticReports/` | 查看系统级崩溃报告 | low |

## Linux 日志系统

### journalctl（systemd）
| 命令 | 说明 | 风险 |
|------|------|------|
| `journalctl -xe` | 查看最近日志并跳转到末尾 | low |
| `journalctl -u 服务名` | 查看指定服务的日志 | low |
| `journalctl --since "1 hour ago"` | 查看最近 1 小时日志 | low |
| `journalctl -f` | 实时跟踪日志 | low |
| `journalctl -p err` | 只看错误级别 | low |

### 传统日志文件
| 命令 | 说明 | 风险 |
|------|------|------|
| `tail -f /var/log/syslog` | 实时查看系统日志 | low |
| `tail -100 /var/log/syslog` | 查看最后 100 行 | low |
| `dmesg` | 查看内核日志 | low |
| `dmesg \| tail -50` | 查看最近 50 条内核消息 | low |
| `cat /var/log/auth.log` | 查看认证日志 | low |

## 常见坑
- macOS 从 10.12 起使用统一日志系统（Unified Logging），旧的 `system.log` 已弃用
- `log show` 默认输出量很大，务必加 `--last` 或 `--predicate` 限制范围
- `journalctl` 的 `--since` 支持自然语言时间表达，如 "2 hours ago"、"yesterday"
- macOS 崩溃日志后缀为 `.ips`（新版）或 `.crash`（旧版）
- Linux 的 `/var/log/auth.log` 记录所有认证事件，排查登录问题时很有用
- `dmesg` 需要 root 权限才能查看完整输出
