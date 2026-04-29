---
name: network-diagnostics
triggers:
  zh: ["网络", "ping", "连不上", "断网", "DNS", "网速", "丢包", "延迟", "wifi", "端口", "连接", "上网", "打不开网页", "网络不通", "超时"]
  en: ["network", "ping", "connection", "DNS", "internet", "wifi", "port", "latency", "timeout", "unreachable", "packet loss"]
os: [darwin, linux]
---

# 网络诊断 (Network Diagnostics)

## 适用场景
- 网络连接异常、无法访问特定网站或服务
- DNS 解析问题
- 端口连通性检查
- 网络延迟或丢包排查
- WiFi / 有线网络故障

## 标准排查流程

### Step 1: 基础连通性
| 命令 | 说明 | 风险 |
|------|------|------|
| `ping -c 4 8.8.8.8` | 测试基础网络连通性（Google DNS） | low |
| `ping -c 4 baidu.com` | 测试 DNS 解析是否正常 | low |

### Step 2: DNS 诊断
| 命令 | 说明 | 风险 |
|------|------|------|
| `nslookup baidu.com` | 查询 DNS 记录 | low |
| `scutil --dns` | 查看 macOS DNS 配置（仅 macOS） | low |
| `cat /etc/resolv.conf` | 查看 Linux DNS 配置（仅 Linux） | low |

### Step 3: 路由追踪
| 命令 | 说明 | 风险 |
|------|------|------|
| `traceroute -I baidu.com` | 追踪网络路径（macOS 用 -I 切 ICMP） | low |
| `traceroute baidu.com` | 追踪网络路径（Linux 默认 ICMP） | low |

### Step 4: 端口检查
| 命令 | 说明 | 风险 |
|------|------|------|
| `lsof -i :80` | 查看 80 端口占用（macOS/Linux） | low |
| `lsof -i :443` | 查看 443 端口占用 | low |
| `netstat -an \| grep LISTEN` | 查看所有监听端口 | low |

### Step 5: 网络接口信息
| 命令 | 说明 | 风险 |
|------|------|------|
| `ifconfig` | 查看网络接口配置 | low |
| `networksetup -listallhardwareports` | 列出 macOS 所有网络硬件端口 | low |
| `ip addr` | 查看 Linux 网络接口（仅 Linux） | low |

## 常见坑
- macOS 的 traceroute 默认用 UDP，建议加 `-I` 切换到 ICMP 模式
- ping 被防火墙拦截不代表服务不可用，需要结合端口检查判断
- macOS 没有 `ss` 命令，用 `netstat -an` 或 `lsof -i` 替代
- macOS 的 `networksetup` 可以管理 WiFi 和有线网络，比 ifconfig 更方便
- 检查 DNS 时建议同时测试 IP 和域名，区分是 DNS 问题还是网络问题
