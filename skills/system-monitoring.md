---
name: system-monitoring
triggers:
  zh: ["监控", "负载", "性能", "CPU", "内存", "使用率", "系统信息", "运行状态", "负载高", "内存不足", "swap", "交换分区", "uptime"]
  en: ["monitor", "load", "performance", "CPU", "memory", "usage", "system info", "status", "swap", "uptime", "resource"]
os: [darwin, linux]
---

# 系统监控 (System Monitoring)

## 适用场景
- 查看系统整体运行状态
- 监控 CPU、内存、负载使用情况
- 排查系统性能瓶颈
- 查看系统运行时间和基本信息

## 标准排查流程

### Step 1: 系统概览
| 命令 | 说明 | 风险 |
|------|------|------|
| `uptime` | 查看系统运行时间和负载均值 | low |
| `uname -a` | 查看系统内核信息 | low |
| `sw_vers` | 查看 macOS 版本信息（仅 macOS） | low |
| `cat /etc/os-release` | 查看 Linux 发行版信息（仅 Linux） | low |

### Step 2: CPU 和负载
| 命令 | 说明 | 风险 |
|------|------|------|
| `sysctl -n machdep.cpu.brand_string` | 查看 CPU 型号（macOS） | low |
| `lscpu` | 查看 CPU 信息（Linux） | low |
| `top -l 1 -s 0 \| head -12` | 查看 macOS CPU 和负载快照 | low |
| `mpstat` | 查看多核 CPU 使用率（如已安装） | low |

### Step 3: 内存状态
| 命令 | 说明 | 风险 |
|------|------|------|
| `vm_stat` | 查看 macOS 虚拟内存统计 | low |
| `free -h` | 查看 Linux 内存使用（仅 Linux） | low |
| `sysctl -n hw.memsize` | 查看 macOS 物理内存大小（字节） | low |
| `memory_pressure` | 查看 macOS 内存压力（仅 macOS） | low |

### Step 4: 磁盘 I/O
| 命令 | 说明 | 风险 |
|------|------|------|
| `iostat` | 查看磁盘 I/O 统计 | low |
| `iostat -d -x 1 3` | 采样 3 次磁盘 I/O 详情 | low |

### Step 5: 网络流量
| 命令 | 说明 | 风险 |
|------|------|------|
| `netstat -ib` | 查看网络接口流量统计（macOS） | low |
| `netstat -s` | 查看网络协议统计 | low |

## 常见坑
- macOS 的 `top` 和 Linux 的 `top` 输出格式和参数差异很大
- load average 的值应该与 CPU 核心数比较，4 核机器 load 超过 4 才算高
- `vm_stat` 输出的页大小通常是 4096 字节，需要手动换算
- macOS 的 `memory_pressure` 命令可以直观判断内存是否紧张
- Linux 的 `free -h` 中 buff/cache 是可回收的，看 available 列更准确
- `iostat` 在 macOS 上需要先安装 `sysstat` 或使用 Homebrew 安装
