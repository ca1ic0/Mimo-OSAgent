---
name: service-management
triggers:
  zh: ["服务", "启动", "停止", "重启", "状态", "守护进程", "daemon", "launchctl", "systemctl", "后台", "自启", "开机启动"]
  en: ["service", "start", "stop", "restart", "status", "daemon", "launchctl", "systemctl", "background", "autostart", "boot"]
os: [darwin, linux]
---

# 服务管理 (Service Management)

## 适用场景
- 启动、停止、重启系统服务
- 查看服务运行状态
- 管理开机自启动服务
- 排查服务异常

## macOS — launchctl

### 基础操作
| 命令 | 说明 | 风险 |
|------|------|------|
| `launchctl list` | 列出所有已加载的服务 | low |
| `launchctl list \| grep 关键词` | 搜索特定服务 | low |
| `launchctl print system/` | 查看系统级服务详情 | low |
| `launchctl print gui/$(id -u)/` | 查看当前用户级服务详情 | low |

### 服务控制
| 命令 | 说明 | 风险 |
|------|------|------|
| `launchctl start 服务标识` | 启动服务 | medium |
| `launchctl stop 服务标识` | 停止服务 | medium |
| `launchctl restart 服务标识` | 重启服务 | medium |
| `launchctl kickstart -k system/服务标识` | 强制重启系统服务 | high |

### 服务配置文件位置
| 路径 | 说明 |
|------|------|
| `/Library/LaunchDaemons/` | 系统级守护进程（开机自启） |
| `/Library/LaunchAgents/` | 系统级用户代理 |
| `~/Library/LaunchAgents/` | 用户级代理（登录自启） |
| `/System/Library/LaunchDaemons/` | Apple 系统守护进程（勿改） |

## Linux — systemctl

### 基础操作
| 命令 | 说明 | 风险 |
|------|------|------|
| `systemctl list-units --type=service` | 列出所有服务 | low |
| `systemctl status 服务名` | 查看服务状态 | low |
| `systemctl is-active 服务名` | 检查服务是否运行 | low |

### 服务控制
| 命令 | 说明 | 风险 |
|------|------|------|
| `sudo systemctl start 服务名` | 启动服务 | medium |
| `sudo systemctl stop 服务名` | 停止服务 | medium |
| `sudo systemctl restart 服务名` | 重启服务 | medium |
| `sudo systemctl reload 服务名` | 重新加载配置（不中断服务） | low |

### 开机自启
| 命令 | 说明 | 风险 |
|------|------|------|
| `systemctl is-enabled 服务名` | 查看是否开机自启 | low |
| `sudo systemctl enable 服务名` | 设置开机自启 | medium |
| `sudo systemctl disable 服务名` | 取消开机自启 | medium |

### 查看日志
| 命令 | 说明 | 风险 |
|------|------|------|
| `journalctl -u 服务名 -f` | 实时查看服务日志 | low |
| `journalctl -u 服务名 --since "1 hour ago"` | 查看最近服务日志 | low |

## 常见坑
- macOS 的 launchctl 服务标识格式通常是反向域名，如 `com.apple.some.daemon`
- 修改 `/Library/LaunchDaemons/` 下的 plist 需要 root 权限
- macOS 的 `launchctl stop` 在某些系统服务上可能不生效，需要用 `kickstart`
- Linux 的 `systemctl` 和 `service` 命令不同，推荐用 `systemctl`
- 重启服务前建议先 `status` 确认服务当前状态
- `/System/Library/LaunchDaemons/` 下是 Apple 系统服务，不建议修改
- Linux 的 systemd 服务文件在 `/etc/systemd/system/` 或 `/lib/systemd/system/`
