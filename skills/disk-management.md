---
name: disk-management
triggers:
  zh: ["磁盘", "硬盘", "存储", "空间", "满了", "清理", "容量", "分区", "挂载", "df", "du", "磁盘空间"]
  en: ["disk", "storage", "space", "full", "cleanup", "capacity", "partition", "mount", "df", "du"]
os: [darwin, linux]
---

# 磁盘管理 (Disk Management)

## 适用场景
- 查看磁盘使用情况和剩余空间
- 查找占用空间大的文件或目录
- 清理磁盘空间
- 磁盘分区和挂载管理

## 标准排查流程

### Step 1: 查看磁盘概览
| 命令 | 说明 | 风险 |
|------|------|------|
| `df -h` | 以人类可读格式查看所有挂载点的磁盘使用 | low |
| `df -h /` | 查看根分区使用情况 | low |

### Step 2: 查找大文件/目录
| 命令 | 说明 | 风险 |
|------|------|------|
| `du -sh *` | 当前目录下各项大小 | low |
| `du -sh ~/*` | 主目录下各项大小 | low |
| `du -sh ~/.Trash` | 查看废纸篓大小（macOS） | low |
| `du -sh ~/Library/Caches` | 查看缓存大小（macOS） | low |

### Step 3: 查找大文件（精确）
| 命令 | 说明 | 风险 |
|------|------|------|
| `find / -size +100M -type f 2>/dev/null` | 查找大于 100M 的文件 | low |
| `find ~ -size +50M -type f 2>/dev/null` | 主目录下大于 50M 的文件 | low |

### Step 4: macOS 磁盘工具
| 命令 | 说明 | 风险 |
|------|------|------|
| `diskutil list` | 列出所有磁盘和分区 | low |
| `diskutil info /` | 查看系统盘详细信息 | low |
| `diskutil apfs list` | 列出 APFS 容器信息（仅 macOS） | low |

### Step 5: 清理建议
| 命令 | 说明 | 风险 |
|------|------|------|
| `rm -rf ~/Library/Caches/*` | 清理用户缓存（macOS） | medium |
| `brew cleanup` | 清理 Homebrew 旧版本和缓存 | low |
| `rm -rf ~/.Trash/*` | 清空废纸篓（macOS） | medium |
| `docker system prune` | 清理 Docker 无用数据（如已安装） | medium |

## 常见坑
- `du` 和 `df` 结果可能不一致，`df` 包含已删除但未释放的文件，`du` 不包含
- macOS 的 APFS 是稀疏分配的，`df` 显示的"已用"可能比实际大
- 清理 `~/Library/Caches` 前建议先确认没有正在运行的应用依赖这些缓存
- `diskutil` 的擦除和分区操作会丢失数据，只读查询命令是安全的
- Linux 上查看磁盘用 `lsblk` 或 `fdisk -l`（需 root）
