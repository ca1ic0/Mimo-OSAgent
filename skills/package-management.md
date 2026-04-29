---
name: package-management
triggers:
  zh: ["安装", "卸载", "更新", "升级", "软件", "包", "brew", "homebrew", "apt", "yum", "dnf", "pip", "npm", "版本", "依赖"]
  en: ["install", "uninstall", "update", "upgrade", "package", "brew", "homebrew", "apt", "yum", "dnf", "pip", "npm", "version", "dependency"]
os: [darwin, linux]
---

# 包管理 (Package Management)

## 适用场景
- 安装、卸载、更新软件包
- 查看已安装的软件包
- 清理旧版本和缓存
- 管理软件源

## macOS — Homebrew

### 基础操作
| 命令 | 说明 | 风险 |
|------|------|------|
| `brew install 软件名` | 安装软件包 | low |
| `brew uninstall 软件名` | 卸载软件包 | low |
| `brew upgrade 软件名` | 升级指定软件包 | low |
| `brew upgrade` | 升级所有可升级的包 | medium |
| `brew update` | 更新 Homebrew 自身和软件源 | low |

### 查询
| 命令 | 说明 | 风险 |
|------|------|------|
| `brew list` | 列出已安装的软件包 | low |
| `brew search 关键词` | 搜索软件包 | low |
| `brew info 软件名` | 查看软件包详情 | low |
| `brew outdated` | 列出可升级的包 | low |

### 清理
| 命令 | 说明 | 风险 |
|------|------|------|
| `brew cleanup` | 清理旧版本和缓存 | low |
| `brew autoremove` | 删除不再需要的依赖 | low |
| `brew doctor` | 检查 Homebrew 健康状态 | low |

## Linux — apt (Debian/Ubuntu)

### 基础操作
| 命令 | 说明 | 风险 |
|------|------|------|
| `sudo apt update` | 更新软件源索引 | low |
| `sudo apt install 软件名` | 安装软件包 | low |
| `sudo apt remove 软件名` | 卸载软件包 | low |
| `sudo apt upgrade` | 升级所有可升级的包 | medium |

### 查询
| 命令 | 说明 | 风险 |
|------|------|------|
| `apt list --installed` | 列出已安装的包 | low |
| `apt search 关键词` | 搜索软件包 | low |
| `apt show 软件名` | 查看软件包详情 | low |

## Linux — dnf (Fedora/RHEL)

| 命令 | 说明 | 风险 |
|------|------|------|
| `sudo dnf install 软件名` | 安装软件包 | low |
| `sudo dnf remove 软件名` | 卸载软件包 | low |
| `sudo dnf upgrade` | 升级所有包 | medium |
| `dnf search 关键词` | 搜索软件包 | low |
| `dnf list installed` | 列出已安装的包 | low |

## 常见坑
- macOS 首次使用 Homebrew 需要先安装 Xcode Command Line Tools：`xcode-select --install`
- `brew update` 和 `brew upgrade` 不同：前者更新软件源索引，后者更新已安装的软件
- Linux 的 `apt install` 前建议先 `apt update` 确保索引是最新的
- `sudo apt upgrade` 可能升级内核，生产环境需谨慎
- pip 安装的包建议用 `pip3` 明确 Python 版本，避免混淆
- 如果 brew 安装太慢，可以考虑换国内镜像源
