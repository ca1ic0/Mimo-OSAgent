---
name: ssh-remote
triggers:
  zh: ["SSH", "ssh", "远程", "远程连接", "远程服务器", "远程登录", "跳板机", "端口转发", "隧道", "密钥", "免密登录", "scp", "rsync", "远程拷贝"]
  en: ["SSH", "ssh", "remote", "remote server", "login", "jump host", "bastion", "port forwarding", "tunnel", "key", "scp", "rsync", "remote copy"]
os: [darwin, linux]
---

# SSH 远程管理 (SSH Remote Management)

## 适用场景
- 通过 SSH 连接远程服务器
- 配置 SSH 密钥实现免密登录
- 文件传输（scp / rsync）
- 端口转发和隧道
- 跳板机（ProxyJump）连接

## 标准操作流程

### Step 1: 基础连接
| 命令 | 说明 | 风险 |
|------|------|------|
| `ssh 用户名@主机地址` | 基础 SSH 连接（默认端口 22） | low |
| `ssh -p 端口号 用户名@主机地址` | 指定端口连接 | low |
| `ssh -v 用户名@主机地址` | 详细模式，排查连接问题 | low |

### Step 2: SSH 密钥管理
| 命令 | 说明 | 风险 |
|------|------|------|
| `ssh-keygen -t ed25519 -C "备注"` | 生成 Ed25519 密钥对（推荐） | low |
| `ssh-keygen -t rsa -b 4096 -C "备注"` | 生成 RSA 4096 密钥对 | low |
| `ssh-copy-id 用户名@主机地址` | 将公钥复制到远程服务器 | low |
| `cat ~/.ssh/id_ed25519.pub` | 查看公钥内容 | low |
| `ssh-add ~/.ssh/id_ed25519` | 将私钥添加到 SSH Agent | low |

### Step 3: SSH 配置文件
| 命令 | 说明 | 风险 |
|------|------|------|
| `cat ~/.ssh/config` | 查看 SSH 配置 | low |
| `vim ~/.ssh/config` | 编辑 SSH 配置 | medium |

推荐的 `~/.ssh/config` 配置模板：
```
Host myserver
    HostName 192.168.1.100
    User deploy
    Port 22
    IdentityFile ~/.ssh/id_ed25519

Host jumphost
    HostName jump.example.com
    User admin

Host internal
    HostName 10.0.0.50
    User root
    ProxyJump jumphost
```

### Step 4: 文件传输
| 命令 | 说明 | 风险 |
|------|------|------|
| `scp 本地文件 用户名@主机:远程路径` | 上传文件到远程 | low |
| `scp 用户名@主机:远程文件 本地路径` | 从远程下载文件 | low |
| `scp -r 本地目录 用户名@主机:远程路径` | 上传整个目录 | low |
| `rsync -avz 本地目录 用户名@主机:远程路径` | 增量同步目录（推荐） | low |
| `rsync -avz --progress 本地文件 用户名@主机:远程路径` | 同步并显示进度 | low |

### Step 5: 端口转发
| 命令 | 说明 | 风险 |
|------|------|------|
| `ssh -L 本地端口:目标地址:目标端口 用户名@跳板机` | 本地端口转发 | medium |
| `ssh -R 远程端口:本地地址:本地端口 用户名@远程` | 远程端口转发 | medium |
| `ssh -D 1080 用户名@主机` | SOCKS5 动态代理 | medium |
| `ssh -N -f -L 8080:localhost:80 用户名@主机` | 后台运行端口转发 | medium |

### Step 6: 常用排查
| 命令 | 说明 | 风险 |
|------|------|------|
| `ssh -T git@github.com` | 测试 GitHub SSH 连接 | low |
| `ssh -o ConnectTimeout=5 用户名@主机` | 设置连接超时（秒） | low |
| `netstat -an \| grep 22` | 检查本地 22 端口状态 | low |
| `lsof -i :22` | 查看 SSH 端口占用 | low |

## 常见坑
- `ssh-copy-id` 首次需要输入密码，之后就可以免密登录了
- `~/.ssh` 目录权限必须是 700，`authorized_keys` 必须是 600，否则 SSH 会拒绝密钥
- macOS 的 SSH Agent 需要手动启动：`eval "$(ssh-agent -s)"` 然后 `ssh-add`
- `scp -r` 传输大量小文件时比 `rsync` 慢很多，推荐用 `rsync`
- 端口转发加 `-N` 不执行远程命令，加 `-f` 后台运行
- ProxyJump 需要 OpenSSH 7.3+，旧版本用 `ProxyCommand` 代替
- 连接超时可以检查防火墙规则、远程 sshd 服务是否运行、端口是否正确
