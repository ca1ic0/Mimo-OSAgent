---
name: process-management
triggers:
  zh: ["进程", "程序", "卡死", "杀掉", "kill", "CPU", "内存", "占用", "僵尸", "top", "htop", "ps", "任务管理器", "死机", "很卡"]
  en: ["process", "kill", "CPU", "memory", "zombie", "top", "htop", "ps", "stuck", "hang", "frozen", "slow"]
os: [darwin, linux]
---

# 进程管理 (Process Management)

## 适用场景
- 查看系统运行的进程
- 查找占用 CPU 或内存高的进程
- 终止卡死或异常的进程
- 排查系统卡顿原因
- 处理僵尸进程

## 标准排查流程

### Step 1: 查看进程概况
| 命令 | 说明 | 风险 |
|------|------|------|
| `ps aux` | 查看所有进程详细信息 | low |
| `ps aux --sort=-%cpu` | 按 CPU 使用率排序（Linux） | low |
| `ps aux -m` | 按内存排序（macOS） | low |
| `top -l 1 -n 10` | 显示前 10 个进程（macOS 快照模式） | low |
| `top -b -n 1` | 显示所有进程（Linux 批处理模式） | low |

### Step 2: 查找特定进程
| 命令 | 说明 | 风险 |
|------|------|------|
| `ps aux \| grep 关键词` | 按名称搜索进程 | low |
| `pgrep -f 关键词` | 按名称搜索并返回 PID | low |
| `lsof -i :端口号` | 查看占用某端口的进程 | low |

### Step 3: 终止进程
| 命令 | 说明 | 风险 |
|------|------|------|
| `kill PID` | 发送 SIGTERM 优雅终止 | medium |
| `kill -9 PID` | 强制终止进程 | high |
| `killall 进程名` | 按名称终止所有同名进程 | high |
| `pkill -f 关键词` | 按关键词匹配终止进程 | high |

### Step 4: 僵尸进程处理
| 命令 | 说明 | 风险 |
|------|------|------|
| `ps aux \| grep Z` | 查找僵尸进程 | low |
| `ps -eo pid,ppid,stat,cmd \| grep Z` | 查看僵尸进程及其父进程 | low |
| `kill 父进程PID` | 终止父进程以清理僵尸进程 | medium |

## 常见坑
- `kill -9` 是强制杀进程，可能导致数据丢失，优先用 `kill`（SIGTERM）让进程自行清理
- macOS 的 `top` 和 Linux 的 `top` 参数不同，macOS 用 `-l` 指定采样次数
- macOS 没有 `htop`，需要 `brew install htop` 安装
- 僵尸进程本身不占资源，但大量僵尸进程说明父进程有问题
- 系统关键进程（PID 1、kernel_task）不能杀，会导致系统崩溃
- `killall` 在 macOS 上是按进程名匹配，在 Linux 上也是，但注意大小写
