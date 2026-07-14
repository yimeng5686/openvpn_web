# OpenVPN Web 管理系统

基于 Python + Flask 构建的 OpenVPN 账号管理 Web 后台，提供用户管理、在线监控、连接日志查询和客户端配置文件自动生成等功能。

---

## 目录

- [项目背景](#项目背景)
- [主要功能](#主要功能)
- [技术栈](#技术栈)
- [核心特性](#核心特性)
- [适用场景](#适用场景)
- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [配置参数详解](#配置参数详解)
- [启动命令](#启动命令)
- [OpenVPN 服务端对接](#openvpn-服务端对接)
- [常用操作指南](#常用操作指南)
- [打包为可执行文件](#打包为可执行文件)
- [数据库说明](#数据库说明)
- [安全注意事项](#安全注意事项)
- [故障排除](#故障排除)

---

## 项目背景

在 Windows 环境下部署 OpenVPN 服务时，用户账号管理通常需要手动编辑配置文件或使用命令行工具，操作繁琐且容易出错。本项目旨在提供一个轻量级的 Web 管理界面，让管理员可以通过浏览器完成所有日常运维操作，降低 OpenVPN 的管理门槛。

系统采用用户名/密码认证模式（替代传统的证书认证），通过 OpenVPN 的 `auth-user-pass-verify` 机制调用 Python 验证脚本，实现与 Web 管理后台共享同一套用户数据库。

---

## 主要功能

| 功能模块 | 说明 |
|---------|------|
| **用户管理** | 添加、删除、启用/禁用 VPN 用户，重置密码，添加备注 |
| **在线监控** | 实时查看当前在线用户列表，支持手动清理过期会话 |
| **连接日志** | 分页查询所有连接记录，区分认证成功与失败 |
| **客户端配置** | 一键生成并下载 `.ovpn` 客户端配置文件 |
| **仪表盘** | 统计总用户数、7日活跃用户、当前在线、今日连接次数 |
| **VPN 认证** | 独立验证脚本，被 OpenVPN 服务端调用完成用户身份校验 |

---

## 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Flask 3.0 | 轻量级 Python Web 框架 |
| 登录管理 | Flask-Login | 管理员会话与认证 |
| 表单验证 | Flask-WTF | CSRF 保护与表单处理 |
| 生产服务器 | Waitress | WSGI 生产级 HTTP 服务器 |
| 数据库 | SQLite | 零配置嵌入式数据库 |
| 密码存储 | SHA-256 | 密码哈希加密存储 |
| 前端 | HTML + CSS + JS | 原生实现，无额外框架依赖 |
| 打包工具 | PyInstaller | 可选，打包为独立 EXE |

---

## 核心特性

- **零外部数据库依赖** — 使用 SQLite，无需安装 MySQL/PostgreSQL 等数据库服务
- **生产级服务器** — 默认使用 Waitress 替代 Flask 开发服务器，稳定可靠
- **密码安全存储** — 所有密码使用 SHA-256 哈希存储，数据库中不保留明文
- **响应式界面** — 支持桌面和移动端浏览器访问
- **集中化配置** — 所有参数集中在 `config.py`，支持环境变量覆盖
- **完整日志** — 应用日志和认证日志分别记录，便于排查问题
- **一键启动** — 提供 `start.bat` 脚本，自动检测环境、安装依赖、初始化数据库

---

## 适用场景

- 企业内网 OpenVPN 用户管理
- 小型团队 VPN 账号运维
- Windows 环境下需要 Web 界面管理 OpenVPN 的场景
- 需要快速开通/关闭 VPN 账号的临时访问场景
- 需要审计 VPN 连接日志的合规场景

---

## 项目结构

```
openvpn_web/
├── app.py                    # Flask 主程序（路由、业务逻辑）
├── config.py                 # 配置文件（所有可配置参数）
├── database.py               # 数据库模块（表结构、CRUD 操作）
├── verify.py                 # OpenVPN 认证脚本（被 OpenVPN 调用）
├── run.py                    # PyInstaller 打包入口
├── requirements.txt          # Python 依赖列表
├── start.bat                 # Windows 一键启动脚本
├── openvpn_webadmin.spec     # PyInstaller 打包配置
├── auth.db                   # SQLite 数据库（运行后自动生成）
├── static/
│   ├── style.css             # 全局样式表（响应式设计）
│   └── main.js               # 前端交互脚本
├── templates/
│   ├── base.html             # 基础模板（导航栏、Flash 消息）
│   ├── login.html            # 登录页面
│   ├── dashboard.html        # 仪表盘
│   ├── users.html            # 用户管理
│   ├── online.html           # 在线监控
│   ├── logs.html             # 连接日志
│   └── client_download.html  # 客户端下载
├── config/
│   └── server.ovpn           # OpenVPN 服务端配置模板
├── temp/                     # 临时文件（客户端配置文件生成）
└── logs/                     # 日志目录
    ├── app.log               # 应用运行日志
    └── verify.log            # 认证脚本日志
```

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / Windows Server 2016 及以上 |
| Python | 3.10 及以上 |
| 内存 | 最低 256MB |
| 磁盘 | 最低 100MB（含依赖） |
| 浏览器 | Chrome / Firefox / Edge 现代版本 |
| OpenVPN | OpenVPN 2.4+（如需对接 VPN 认证） |

---

## 安装步骤

### 方式一：使用 uv（推荐）

```powershell
# 1. 进入项目目录
cd e:\workspace-python\study\openvpn_web

# 2. 创建虚拟环境（Python 3.10）
uv venv --python 3.10

# 3. 安装依赖
uv pip install -r requirements.txt

# 4. 初始化数据库
.venv\Scripts\python.exe database.py

# 5. 启动应用
.venv\Scripts\python.exe app.py
```

### 方式二：使用 pip

```powershell
# 1. 进入项目目录
cd e:\workspace-python\study\openvpn_web

# 2. 创建虚拟环境
python -m venv .venv

# 3. 激活虚拟环境
.venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 初始化数据库
python database.py

# 6. 启动应用
python app.py
```

### 方式三：一键启动

```powershell
# 双击 start.bat，脚本将自动完成环境检测、依赖安装、数据库初始化和应用启动
.\start.bat
```

启动成功后，浏览器访问 **http://localhost:5000** 即可进入管理后台。

默认管理员账号：

| 项目 | 值 |
|------|-----|
| 用户名 | `admin` |
| 密码 | `admin123` |

> **重要**：首次登录后请立即修改管理员密码！

---

## 配置参数详解

所有配置参数集中在 `config.py` 中，部分参数支持通过环境变量覆盖。

### 基础路径配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `BASE_DIR` | 自动检测 | 项目根目录 |
| `DB_PATH` | `{BASE_DIR}/auth.db` | SQLite 数据库文件路径 |
| `TEMP_DIR` | `{BASE_DIR}/temp` | 临时文件目录 |
| `LOG_DIR` | `{BASE_DIR}/logs` | 日志文件目录 |
| `OPENVPN_STATUS_LOG` | `{BASE_DIR}/status.log` | OpenVPN 状态日志路径 |

### Flask 配置

| 参数 | 默认值 | 环境变量 | 说明 |
|------|--------|----------|------|
| `SECRET_KEY` | 随机生成 | `SECRET_KEY` | Session 加密密钥，生产环境务必设置固定值 |
| `PERMANENT_SESSION_LIFETIME` | `86400` | — | 会话有效期（秒），默认 24 小时 |

### 服务器配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `5000` | 监听端口 |
| `DEBUG` | `False` | 调试模式，生产环境务必关闭 |

### OpenVPN 配置

| 参数 | 默认值 | 环境变量 | 说明 |
|------|--------|----------|------|
| `OPENVPN_SERVER_IP` | `YOUR_SERVER_IP` | `OPENVPN_SERVER_IP` | VPN 服务器地址，用于生成客户端配置 |
| `OPENVPN_SERVER_PORT` | `1194` | `OPENVPN_SERVER_PORT` | VPN 服务器端口 |
| `OPENVPN_PROTOCOL` | `udp` | `OPENVPN_PROTOCOL` | 协议类型（`udp` / `tcp`） |
| `OPENVPN_CIPHER` | `AES-256-GCM` | — | 加密算法 |

### 安全配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MIN_PASSWORD_LENGTH` | `6` | 密码最小长度 |
| `USERNAME_PATTERN` | `^[a-zA-Z0-9_]{3,32}$` | 用户名正则验证规则 |
| `SESSION_EXPIRE_HOURS` | `24` | 在线会话过期时间（小时） |

### 分页配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `LOG_PER_PAGE` | `20` | 每页显示日志条数 |

### 环境变量配置示例

通过环境变量覆盖配置，无需修改代码：

```powershell
# 设置 VPN 服务器地址
$env:OPENVPN_SERVER_IP = "203.0.113.10"

# 设置 VPN 端口
$env:OPENVPN_SERVER_PORT = "1194"

# 设置协议
$env:OPENVPN_PROTOCOL = "tcp"

# 设置 Session 密钥（生产环境必须）
$env:SECRET_KEY = "your-strong-random-secret-key-here"

# 启动应用
.venv\Scripts\python.exe app.py
```

---

## 启动命令

### 开发/测试启动

```powershell
# 使用虚拟环境中的 Python
.venv\Scripts\python.exe app.py
```

### 生产环境启动

```powershell
# 使用 waitress 生产服务器（app.py 默认已集成）
.venv\Scripts\python.exe app.py

# 或直接使用 waitress-serve 命令
.venv\Scripts\waitress-serve.exe --host=0.0.0.0 --port=5000 app:app
```

### 后台服务启动（Windows）

如果需要将应用注册为 Windows 服务，可使用 [NSSM](https://nssm.cc/)：

```powershell
# 安装 NSSM 后执行
nssm install OpenVPN-WebAdmin "E:\workspace-python\study\openvpn_web\.venv\Scripts\python.exe" "E:\workspace-python\study\openvpn_web\app.py"
nssm start OpenVPN-WebAdmin
```

---

## OpenVPN 服务端对接

### 1. 配置 server.ovpn

将 `config/server.ovpn` 模板复制到 OpenVPN 配置目录，修改以下关键参数：

```ini
# 指定验证脚本路径（修改为实际路径）
auth-user-pass-verify "C:\\Python310\\python.exe C:\\openvpn-webadmin\\verify.py" via-env

# 状态文件路径（修改为项目实际路径）
status "C:\\openvpn-webadmin\\status.log" 5

# 日志文件路径
log-append "C:\\openvpn-webadmin\\openvpn.log"
```

### 2. 配置权限

OpenVPN 服务默认以 SYSTEM 账户运行，需要确保 SYSTEM 有权限访问项目目录：

```powershell
# 授予 SYSTEM 账户对项目目录的读取和执行权限
icacls "E:\workspace-python\study\openvpn_web" /grant "SYSTEM:(RX)"
```

### 3. 重启 OpenVPN 服务

```powershell
Restart-Service -Name "OpenVPNService"
```

### 4. 验证对接

```powershell
# 手动测试验证脚本
.venv\Scripts\python.exe verify.py admin admin123

# 返回 0 表示认证成功，返回 1 表示认证失败
echo $LASTEXITCODE
```

---

## 常用操作指南

### 添加 VPN 用户

1. 登录管理后台 → 点击「用户管理」
2. 在「添加新用户」表单中填写用户名、密码和备注
3. 点击「添加用户」
4. 用户即可使用该账号连接 VPN

### 下载客户端配置

1. 进入「用户管理」页面
2. 找到目标用户，点击「下载配置」按钮
3. 浏览器将下载 `{username}.ovpn` 文件
4. 将该文件导入 OpenVPN 客户端，输入用户名密码即可连接

> 生成配置文件前，请先在 `config.py` 中设置正确的 `OPENVPN_SERVER_IP`。

### 重置用户密码

1. 进入「用户管理」页面
2. 找到目标用户，在「新密码」输入框中输入新密码
3. 点击「重置密码」

### 禁用/启用用户

1. 进入「用户管理」页面
2. 找到目标用户，点击「禁用」或「启用」按钮
3. 被禁用的用户将无法通过 VPN 认证

### 查看在线用户

1. 点击「在线监控」
2. 查看当前在线用户列表（用户名、客户端 IP、登录时间）
3. 可点击「清理过期会话」移除超过 24 小时无活动的记录

### 查询连接日志

1. 点击「连接日志」
2. 浏览所有连接记录，支持分页
3. 日志状态说明：
   - `connected` — 认证成功并连接
   - `auth_failed: xxx` — 认证失败（附失败原因）

---

## 打包为可执行文件

使用 PyInstaller 将项目打包为独立的 `.exe`，用户无需安装 Python 即可运行。

```powershell
# 1. 安装 PyInstaller
uv pip install pyinstaller
# 或
pip install pyinstaller

# 2. 执行打包
pyinstaller openvpn_webadmin.spec

# 3. 打包产物在 dist 目录
# dist/OpenVPN-WebAdmin/OpenVPN-WebAdmin.exe
```

打包完成后，将 `dist/OpenVPN-WebAdmin/` 整个目录分发给用户，双击 `OpenVPN-WebAdmin.exe` 即可运行。

---

## 数据库说明

系统使用 SQLite 数据库，文件为 `auth.db`，包含以下三张表：

### users — 用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| username | TEXT | 用户名，唯一 |
| password_hash | TEXT | SHA-256 密码哈希 |
| created_at | TEXT | 创建时间（ISO 格式） |
| is_active | INTEGER | 状态：1=启用，0=禁用 |
| notes | TEXT | 备注 |

### connection_logs — 连接日志表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| username | TEXT | 用户名 |
| client_ip | TEXT | 客户端 IP |
| connect_time | TEXT | 连接时间 |
| disconnect_time | TEXT | 断开时间 |
| bytes_sent | INTEGER | 发送字节数 |
| bytes_received | INTEGER | 接收字节数 |
| status | TEXT | 状态（connected / auth_failed:xxx） |

### active_sessions — 在线会话表

| 字段 | 类型 | 说明 |
|------|------|------|
| username | TEXT | 用户名，主键 |
| client_ip | TEXT | 客户端 IP |
| login_time | TEXT | 登录时间 |
| bytes_sent | INTEGER | 发送字节数 |
| bytes_received | INTEGER | 接收字节数 |

### 数据库备份

```powershell
# 直接复制数据库文件即可完成备份
Copy-Item "auth.db" "auth_backup_$(Get-Date -Format 'yyyyMMdd').db"
```

---

## 安全注意事项

1. **修改默认密码** — 首次登录后立即修改 `admin` 账户密码
2. **设置 SECRET_KEY** — 生产环境通过环境变量设置固定的强随机密钥
3. **启用 HTTPS** — 建议使用 Nginx 反向代理并配置 SSL 证书
4. **限制访问** — 将 `HOST` 设为 `127.0.0.1`，通过反向代理暴露服务
5. **数据库权限** — 确保 `auth.db` 仅允许管理员和 SYSTEM 账户访问
6. **定期备份** — 定期备份数据库文件
7. **日志审计** — 定期检查 `logs/` 目录下的日志文件

---

## 故障排除

### 常见问题

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 启动报错 `ModuleNotFoundError: No module named 'flask'` | 依赖未安装 | 执行 `pip install -r requirements.txt` |
| 端口 5000 被占用 | 其他程序占用端口 | 修改 `config.py` 中的 `PORT`，或终止占用进程：`netstat -ano \| findstr :5000` |
| 登录后页面空白 | SECRET_KEY 异常 | 检查 `config.py` 中 `SECRET_KEY` 是否正确设置 |
| OpenVPN 认证失败 | verify.py 路径或权限问题 | 检查 `server.ovpn` 中 `auth-user-pass-verify` 路径，确保 SYSTEM 有执行权限 |
| 在线用户列表为空 | verify.py 未正确记录 | 检查 `logs/verify.log`，确认认证脚本是否被调用 |
| 客户端配置下载失败 | TEMP_DIR 权限不足 | 确保 `temp/` 目录存在且有写入权限 |
| 数据库连接错误 | DB_PATH 路径不正确 | 检查 `config.py` 中 `DB_PATH` 配置 |

### 查看日志

```powershell
# 查看应用日志
Get-Content logs\app.log -Tail 50

# 查看认证日志
Get-Content logs\verify.log -Tail 50

# 查看 OpenVPN 服务日志
Get-Content "C:\openvpn-webadmin\openvpn.log" -Tail 50
```

### 手动测试认证脚本

```powershell
# 测试正确密码（应返回 0）
.venv\Scripts\python.exe verify.py admin admin123
echo $LASTEXITCODE

# 测试错误密码（应返回 1）
.venv\Scripts\python.exe verify.py admin wrongpassword
echo $LASTEXITCODE
```

### 重新初始化数据库

```powershell
# 删除旧数据库
Remove-Item auth.db

# 重新初始化
.venv\Scripts\python.exe database.py
```

> **注意**：重新初始化将丢失所有用户数据和日志记录，请先备份。
