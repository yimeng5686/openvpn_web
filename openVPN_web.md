# 方案一进阶：Python + Flask 实现 OpenVPN 账号管理与 Web 管理端

## 一、方案概述

本方案是在"本地脚本验证"基础上的进阶版本，采用 **Python + Flask** 构建一个完整的 Web 管理后台，实现以下功能：

- 通过 Web 界面管理 OpenVPN 用户账号（增删改查）
- 用户密码加密存储（SHA-256 哈希）
- 实时在线状态监控
- 连接日志记录与查询
- 客户端配置文件自动生成

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     客户端 (OpenVPN Client)                  │
│                     输入用户名/密码登录                       │
└──────────────────────────────┬──────────────────────────────┘
                               │ auth request
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    OpenVPN Server (Windows)                  │
│  server.ovpn 配置:                                            │
│  auth-user-pass-verify verify.py via-env                     │
│  client-cert-not-required                                     │
└──────────────────────────────┬──────────────────────────────┘
                               │ 调用验证脚本
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    verify.py (Python 验证脚本)                │
│  接收用户名/密码 → 查询 users.db → 验证哈希 → 返回 0/1        │
└──────────────────────────────┬──────────────────────────────┘
                               │ 读取/写入
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         SQLite 数据库                        │
│  users (用户名、哈希密码、创建时间、状态)                      │
│  logs (连接时间、断开时间、客户端IP、发送/接收流量)            │
└──────────────────────────────┬──────────────────────────────┘
                               │ 管理操作
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Flask Web 管理后台                           │
│  运行地址: http://your-server:5000                            │
│  功能: 用户管理、在线监控、日志查询、客户端下载                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、环境准备

### 2.1 安装 Python 和相关依赖

```bash
# 安装 Python 3.8+（如果未安装）
# 下载地址: https://www.python.org/downloads/windows/

# 安装完成后，以管理员身份打开 PowerShell，执行：
pip install flask flask-login flask-wtf werkzeug sqlite3
```

### 2.2 创建项目目录结构

```bash
# 在 C:\openvpn-webadmin 下创建以下目录结构：
C:\openvpn-webadmin\
├── app.py                    # Flask 主程序
├── verify.py                 # OpenVPN 认证脚本
├── auth.db                   # SQLite 数据库（自动生成）
├── static/                   # 静态文件（CSS、JS）
│   └── style.css
├── templates/                # HTML 模板
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── users.html
│   ├── logs.html
│   └── client_download.html
└── config/                   # 配置文件目录
    └── server.ovpn           # OpenVPN 服务端配置备份
```

---

## 三、数据库设计

创建 `database.py`，初始化 SQLite 数据库和表结构：

```python
import sqlite3
import hashlib
import datetime

DB_PATH = r"C:\openvpn-webadmin\auth.db"

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            notes TEXT
        )
    ''')

    # 连接日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS connection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            client_ip TEXT,
            connect_time TEXT,
            disconnect_time TEXT,
            bytes_sent INTEGER DEFAULT 0,
            bytes_received INTEGER DEFAULT 0,
            status TEXT
        )
    ''')

    # 在线会话表（用于实时监控）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_sessions (
            username TEXT PRIMARY KEY,
            client_ip TEXT,
            login_time TEXT,
            bytes_sent INTEGER DEFAULT 0,
            bytes_received INTEGER DEFAULT 0
        )
    ''')

    # 创建默认管理员账户（密码: admin123）
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password_hash, created_at, is_active)
        VALUES (?, ?, ?, ?)
    ''', ("admin", admin_hash, datetime.datetime.now().isoformat(), 1))

    conn.commit()
    conn.close()
    print("数据库初始化完成！")

if __name__ == "__main__":
    init_db()
```

---

## 四、OpenVPN 验证脚本 (verify.py)

OpenVPN 通过 `auth-user-pass-verify` 调用此脚本进行认证。

```python
#!/usr/bin/env python3
"""
OpenVPN 认证脚本
接收从 OpenVPN 传递过来的用户名和密码，与数据库中的哈希密码进行比对
"""

import sys
import os
import hashlib
import sqlite3
import datetime

DB_PATH = r"C:\openvpn-webadmin\auth.db"

def get_db():
    return sqlite3.connect(DB_PATH)

def log_connection(username, client_ip, success, status_detail=""):
    """记录连接日志"""
    conn = get_db()
    cursor = conn.cursor()

    if success:
        # 记录连接成功
        cursor.execute('''
            INSERT INTO connection_logs (username, client_ip, connect_time, status)
            VALUES (?, ?, ?, ?)
        ''', (username, client_ip, datetime.datetime.now().isoformat(), "connected"))

        # 更新或插入在线会话
        cursor.execute('''
            INSERT OR REPLACE INTO active_sessions (username, client_ip, login_time)
            VALUES (?, ?, ?)
        ''', (username, client_ip, datetime.datetime.now().isoformat()))
    else:
        # 记录认证失败
        cursor.execute('''
            INSERT INTO connection_logs (username, client_ip, connect_time, status)
            VALUES (?, ?, ?, ?)
        ''', (username, client_ip, datetime.datetime.now().isoformat(), f"auth_failed: {status_detail}"))

    conn.commit()
    conn.close()

def verify_user(username, password):
    """验证用户凭据"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT password_hash, is_active FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, "user not exists"

    if not row[1]:  # is_active == 0
        return False, "user disabled"

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash == row[0]:
        return True, "success"
    else:
        return False, "wrong password"

def main():
    """主函数 - 被 OpenVPN 调用"""
    # OpenVPN 通过环境变量传递用户名和密码（使用 via-env 模式时）
    username = os.environ.get('username')
    password = os.environ.get('password')

    # 如果没有环境变量，尝试通过命令行参数获取
    if not username and len(sys.argv) >= 2:
        username = sys.argv[1]
    if not password and len(sys.argv) >= 3:
        password = sys.argv[2]

    # 获取客户端 IP（通过环境变量）
    client_ip = os.environ.get('untrusted_ip', 'unknown')

    if not username or not password:
        print("认证失败：缺少用户名或密码")
        log_connection("unknown", client_ip, False, "missing credentials")
        sys.exit(1)

    success, msg = verify_user(username, password)
    log_connection(username, client_ip, success, msg)

    if success:
        print(f"认证成功: {username}")
        sys.exit(0)  # 返回 0 表示认证成功
    else:
        print(f"认证失败: {username} - {msg}")
        sys.exit(1)  # 返回非 0 表示认证失败

if __name__ == "__main__":
    main()
```

### 配置说明

将 `verify.py` 放置在合适目录（如 `C:\openvpn-webadmin\verify.py`），并确保 OpenVPN 服务（通常以 SYSTEM 用户运行）有权限访问该文件和数据库目录。

> **权限提示**：OpenVPN 服务默认以 SYSTEM 账户运行，可能需要为 `C:\openvpn-webadmin` 目录授予 SYSTEM 的读取和执行权限。

---

## 五、OpenVPN 服务端配置

编辑 `server.ovpn`，添加以下配置：

```ini
# ========== 账号密码认证配置 ==========
# 启用用户名/密码认证
auth-user-pass

# 指定验证脚本（使用 via-env 方式传递用户名和密码）
auth-user-pass-verify "C:\\Python3\\python.exe C:\\openvpn-webadmin\\verify.py" via-env

# 允许通过环境变量传递密码
script-security 3

# 不使用客户端证书
client-cert-not-required

# 将用户名作为 Common Name
username-as-common-name

# 可选：推送内网路由（根据实际情况调整）
push "route 192.168.0.0 255.255.255.0"

# 可选：添加客户端状态文件，用于 Web 管理端读取在线信息
status "C:\\openvpn-webadmin\\status.log" 5
```

**修改后重启 OpenVPN 服务**：

```powershell
Restart-Service -Name "OpenVPNService"
```

> **注意**：`via-env` 和 `via-file` 的区别详见官方文档：via-env 通过环境变量传递凭据，via-file 通过临时文件传递。

---

## 六、Flask Web 管理端开发

### 6.1 主程序 `app.py`

```python
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import hashlib
import datetime
import subprocess
import re

app = Flask(__name__)
app.secret_key = "your-secret-key-change-this"  # 生产环境请使用强随机密钥

# Flask-Login 配置
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

DB_PATH = r"C:\openvpn-webadmin\auth.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class User(UserMixin):
    def __init__(self, id, username, is_admin=True):
        self.id = id
        self.username = username
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'])
    return None

# ================== 路由 ==================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and hashlib.sha256(password.encode()).hexdigest() == user['password_hash']:
            login_user(User(user['id'], user['username']))
            flash('登录成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """仪表盘 - 显示统计数据"""
    conn = get_db()
    cursor = conn.cursor()

    # 总用户数
    cursor.execute('SELECT COUNT(*) FROM users WHERE username != "admin"')
    total_users = cursor.fetchone()[0]

    # 活跃用户数（7天内登录）
    seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    cursor.execute('SELECT COUNT(DISTINCT username) FROM connection_logs WHERE connect_time > ?', (seven_days_ago,))
    active_users = cursor.fetchone()[0]

    # 在线用户数（从 status 文件或 active_sessions 表读取）
    cursor.execute('SELECT COUNT(*) FROM active_sessions')
    online_users = cursor.fetchone()[0]

    # 今天连接次数
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute('SELECT COUNT(*) FROM connection_logs WHERE connect_time LIKE ?', (f"{today}%",))
    today_connects = cursor.fetchone()[0]

    conn.close()

    return render_template('dashboard.html', 
                          total_users=total_users,
                          active_users=active_users,
                          online_users=online_users,
                          today_connects=today_connects)

@app.route('/users')
@login_required
def users():
    """用户管理页面"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, created_at, is_active, notes FROM users ORDER BY id')
    user_list = cursor.fetchall()
    conn.close()
    return render_template('users.html', users=user_list)

@app.route('/user/add', methods=['POST'])
@login_required
def add_user():
    """添加用户"""
    username = request.form['username']
    password = request.form['password']
    notes = request.form.get('notes', '')

    if not re.match(r'^[a-zA-Z0-9_]{3,32}$', username):
        flash('用户名格式错误：仅支持字母、数字、下划线，长度3-32', 'danger')
        return redirect(url_for('users'))

    if len(password) < 6:
        flash('密码长度至少6位', 'danger')
        return redirect(url_for('users'))

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    created_at = datetime.datetime.now().isoformat()

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password_hash, created_at, is_active, notes) VALUES (?, ?, ?, 1, ?)',
                       (username, password_hash, created_at, notes))
        conn.commit()
        flash(f'用户 {username} 添加成功！', 'success')
    except sqlite3.IntegrityError:
        flash(f'用户名 {username} 已存在', 'danger')
    conn.close()

    return redirect(url_for('users'))

@app.route('/user/edit/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    """编辑用户（重置密码/启用/禁用）"""
    action = request.form.get('action')
    conn = get_db()
    cursor = conn.cursor()

    if action == 'reset_password':
        new_password = request.form.get('new_password', '')
        if len(new_password) >= 6:
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
            flash('密码重置成功', 'success')
    elif action == 'toggle_status':
        cursor.execute('SELECT is_active FROM users WHERE id = ?', (user_id,))
        current = cursor.fetchone()
        new_status = 0 if current[0] == 1 else 1
        cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
        flash('用户状态已更新', 'success')
    elif action == 'delete':
        cursor.execute('DELETE FROM users WHERE id = ? AND username != "admin"', (user_id,))
        flash('用户已删除', 'success')

    conn.commit()
    conn.close()
    return redirect(url_for('users'))

@app.route('/online')
@login_required
def online_users():
    """在线用户监控"""
    conn = get_db()
    cursor = conn.cursor()

    # 从 active_sessions 表读取在线用户
    cursor.execute('''SELECT username, client_ip, login_time 
                      FROM active_sessions 
                      ORDER BY login_time DESC''')
    online_list = cursor.fetchall()

    # 可选：尝试读取 OpenVPN 的 status 文件获取更准确的流量信息
    status_log = []
    try:
        with open(r"C:\openvpn-webadmin\status.log", 'r') as f:
            status_log = f.readlines()
    except:
        pass

    conn.close()
    return render_template('online.html', users=online_list)

@app.route('/logs')
@login_required
def logs():
    """连接日志页面"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM connection_logs')
    total = cursor.fetchone()[0]

    cursor.execute('''SELECT id, username, client_ip, connect_time, disconnect_time, status 
                      FROM connection_logs 
                      ORDER BY connect_time DESC 
                      LIMIT ? OFFSET ?''', (per_page, offset))
    log_list = cursor.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template('logs.html', logs=log_list, page=page, total_pages=total_pages)

@app.route('/client/download')
@login_required
def client_download():
    """客户端下载页面"""
    return render_template('client_download.html')

@app.route('/client/config/<username>')
@login_required
def generate_client_config(username):
    """生成客户端配置文件"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
    if not cursor.fetchone():
        conn.close()
        flash('用户不存在', 'danger')
        return redirect(url_for('users'))
    conn.close()

    # 读取服务器配置模板
    config_template = f'''client
dev tun
proto udp
remote YOUR_SERVER_IP 1194
resolv-retry infinite
nobind
persist-key
persist-tun
auth-user-pass
remote-cert-tls server
cipher AES-256-GCM
verb 3

# 用户名: {username}
# 请在连接时输入密码
'''

    config_filename = f"{username}.ovpn"
    config_path = f"C:\\openvpn-webadmin\\temp\\{config_filename}"

    import os
    os.makedirs("C:\\openvpn-webadmin\\temp", exist_ok=True)
    with open(config_path, "w") as f:
        f.write(config_template)

    return send_file(config_path, as_attachment=True, download_name=config_filename)

# ================== 定时清理任务 ==================
def cleanup_expired_sessions():
    """清理超过24小时无活动的会话"""
    conn = get_db()
    cursor = conn.cursor()
    expire_time = (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat()
    cursor.execute('DELETE FROM active_sessions WHERE login_time < ?', (expire_time,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### 6.2 HTML 模板文件

创建以下模板文件放在 `templates/` 目录下：

#### `templates/base.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenVPN 管理系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; }
        .navbar { background: #2c3e50; color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        .navbar h1 { font-size: 1.5rem; }
        .nav-links a { color: white; text-decoration: none; margin-left: 1.5rem; padding: 0.5rem; }
        .nav-links a:hover { background: #34495e; border-radius: 4px; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .flash-messages { margin-bottom: 1rem; }
        .flash-success { background: #d4edda; color: #155724; padding: 0.75rem; border-radius: 4px; margin-bottom: 0.5rem; }
        .flash-danger { background: #f8d7da; color: #721c24; padding: 0.75rem; border-radius: 4px; margin-bottom: 0.5rem; }
        .flash-info { background: #d1ecf1; color: #0c5460; padding: 0.75rem; border-radius: 4px; margin-bottom: 0.5rem; }
        .card { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 1.5rem; margin-bottom: 1.5rem; }
        .card h3 { margin-bottom: 1rem; color: #2c3e50; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: 600; }
        .btn { display: inline-block; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9rem; }
        .btn-primary { background: #3498db; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-success { background: #27ae60; color: white; }
        input, select { padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; margin: 0.25rem 0; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2.5rem; font-weight: bold; color: #3498db; }
        .stat-label { color: #7f8c8d; margin-top: 0.5rem; }
    </style>
</head>
<body>
    <nav class="navbar">
        <h1>OpenVPN 管理系统</h1>
        <div class="nav-links">
            <a href="{{ url_for('dashboard') }}">仪表盘</a>
            <a href="{{ url_for('users') }}">用户管理</a>
            <a href="{{ url_for('online_users') }}">在线监控</a>
            <a href="{{ url_for('logs') }}">连接日志</a>
            <a href="{{ url_for('client_download') }}">客户端下载</a>
            <a href="{{ url_for('logout') }}">退出</a>
        </div>
    </nav>
    <div class="container">
        <div class="flash-messages">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% for category, message in messages %}
                    <div class="flash-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endwith %}
        </div>
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

#### `templates/dashboard.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-number">{{ total_users }}</div>
        <div class="stat-label">总用户数</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{{ active_users }}</div>
        <div class="stat-label">7日活跃用户</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{{ online_users }}</div>
        <div class="stat-label">当前在线</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{{ today_connects }}</div>
        <div class="stat-label">今日连接次数</div>
    </div>
</div>

<div class="card">
    <h3>系统状态</h3>
    <p>OpenVPN 服务: 
        <span style="color: #27ae60; font-weight: bold;">
            {% set service = "正在运行" %}  {{ service }}
        </span>
    </p>
    <p>数据库: SQLite ({{ DB_PATH }})</p>
    <p>当前用户: {{ current_user.username }}</p>
</div>

<div class="card">
    <h3>快速操作</h3>
    <a href="{{ url_for('users') }}" class="btn btn-primary">管理用户</a>
    <a href="{{ url_for('online_users') }}" class="btn btn-primary" style="margin-left: 0.5rem;">查看在线用户</a>
</div>
{% endblock %}
```

#### `templates/users.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="card">
    <h3>添加新用户</h3>
    <form method="POST" action="{{ url_for('add_user') }}">
        <input type="text" name="username" placeholder="用户名" required style="width: 200px;">
        <input type="password" name="password" placeholder="密码" required style="width: 200px;">
        <input type="text" name="notes" placeholder="备注" style="width: 200px;">
        <button type="submit" class="btn btn-success">添加用户</button>
    </form>
</div>

<div class="card">
    <h3>用户列表</h3>
    <table>
        <thead>
            <tr><th>ID</th><th>用户名</th><th>创建时间</th><th>状态</th><th>备注</th><th>操作</th></tr>
        </thead>
        <tbody>
            {% for user in users %}
            <tr>
                <td>{{ user.id }}</td>
                <td>{{ user.username }}</td>
                <td>{{ user.created_at[:19] if user.created_at else '-' }}</td>
                <td>{% if user.is_active %}<span style="color: #27ae60;">启用</span>{% else %}<span style="color: #e74c3c;">禁用</span>{% endif %}</td>
                <td>{{ user.notes or '-' }}</td>
                <td>
                    <form method="POST" action="{{ url_for('edit_user', user_id=user.id) }}" style="display: inline;">
                        <input type="hidden" name="action" value="toggle_status">
                        <button type="submit" class="btn btn-warning">{% if user.is_active %}禁用{% else %}启用{% endif %}</button>
                    </form>
                    {% if user.username != 'admin' %}
                    <form method="POST" action="{{ url_for('edit_user', user_id=user.id) }}" style="display: inline;">
                        <input type="hidden" name="action" value="reset_password">
                        <input type="password" name="new_password" placeholder="新密码" style="width: 100px;" required>
                        <button type="submit" class="btn btn-primary">重置密码</button>
                    </form>
                    <form method="POST" action="{{ url_for('edit_user', user_id=user.id) }}" style="display: inline;">
                        <input type="hidden" name="action" value="delete">
                        <button type="submit" class="btn btn-danger" onclick="return confirm('确定删除用户 {{ user.username }}？')">删除</button>
                    </form>
                    <a href="{{ url_for('generate_client_config', username=user.username) }}" class="btn btn-success">下载配置</a>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

#### `templates/online.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="card">
    <h3>当前在线用户</h3>
    <table>
        <thead><tr><th>用户名</th><th>客户端IP</th><th>登录时间</th></tr></thead>
        <tbody>
            {% for user in users %}
            <tr>
                <td>{{ user.username }}</td>
                <td>{{ user.client_ip }}</td>
                <td>{{ user.login_time }}</td>
            </tr>
            {% else %}
            <tr><td colspan="3" style="text-align: center;">暂无在线用户</td></tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

#### `templates/logs.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="card">
    <h3>连接日志</h3>
    <table>
        <thead><tr><th>时间</th><th>用户名</th><th>客户端IP</th><th>状态</th></tr></thead>
        <tbody>
            {% for log in logs %}
            <tr>
                <td>{{ log.connect_time[:19] }}</td>
                <td>{{ log.username }}</td>
                <td>{{ log.client_ip or '-' }}</td>
                <td style="color: {% if 'connected' in log.status %}#27ae60{% elif 'failed' in log.status %}#e74c3c{% else %}#f39c12{% endif %};">{{ log.status }}</td>
            </tr>
            {% else %}
            <tr><td colspan="4">暂无日志记录</td></tr>
            {% endfor %}
        </tbody>
    </table>

    <div style="margin-top: 1rem;">
        {% if page > 1 %}<a href="?page={{ page-1 }}" class="btn btn-primary">上一页</a>{% endif %}
        <span>第 {{ page }} 页</span>
        {% if page < total_pages %}<a href="?page={{ page+1 }}" class="btn btn-primary">下一页</a>{% endif %}
    </div>
</div>
{% endblock %}
```

#### `templates/login.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OpenVPN 管理系统 - 登录</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #2c3e50; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 350px; }
        .login-container h2 { text-align: center; margin-bottom: 1.5rem; color: #2c3e50; }
        input { width: 100%; padding: 0.75rem; margin: 0.5rem 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 0.75rem; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
        button:hover { background: #2980b9; }
        .flash { margin-bottom: 1rem; padding: 0.75rem; border-radius: 4px; }
        .flash-success { background: #d4edda; color: #155724; }
        .flash-danger { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>OpenVPN 管理系统</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="flash flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="用户名" required>
            <input type="password" name="password" placeholder="密码" required>
            <button type="submit">登录</button>
        </form>
    </div>
</body>
</html>
```

#### `templates/client_download.html`

```html
{% extends "base.html" %}
{% block content %}
<div class="card">
    <h3>客户端下载</h3>
    <p>请从以下地址下载 OpenVPN 客户端软件：</p>
    <ul>
        <li><a href="https://openvpn.net/client-connect-vpn-for-windows/" target="_blank">Windows 客户端</a></li>
        <li><a href="https://openvpn.net/client-connect-vpn-for-mac/" target="_blank">macOS 客户端</a></li>
        <li><a href="https://openvpn.net/client-connect-vpn-for-linux/" target="_blank">Linux 客户端</a></li>
        <li><a href="https://play.google.com/store/apps/details?id=net.openvpn.openvpn" target="_blank">Android 客户端</a></li>
        <li><a href="https://apps.apple.com/app/openvpn-connect/id590379981" target="_blank">iOS 客户端</a></li>
    </ul>
    <hr>
    <h3>获取配置文件</h3>
    <p>在 <a href="{{ url_for('users') }}">用户管理</a> 页面，点击每个用户对应的"下载配置"按钮，即可获取该用户的专属配置文件。</p>
    <p>将下载的 .ovpn 文件导入 OpenVPN 客户端，输入用户名和密码即可连接。</p>
</div>
{% endblock %}
```

---

## 七、运行与部署

### 7.1 启动 Flask 管理端

```powershell
# 进入项目目录
cd C:\openvpn-webadmin

# 初始化数据库（首次运行）
python database.py

# 启动 Flask 应用
python app.py
```

访问 `http://your-server-ip:5000` 即可进入管理后台，默认账号 `admin` / `admin123`。

### 7.2 生产环境部署（可选）

Flask 内置的开发服务器不适合生产环境，建议使用 `waitress`：

```powershell
pip install waitress

# 使用 waitress 启动
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

---

## 八、安全注意事项

1. **密码安全**：所有密码使用 SHA-256 哈希存储，不建议使用明文密码。
2. **数据库权限**：确保 `auth.db` 文件仅允许 SYSTEM 和 Administrators 访问。
3. **HTTPS**：生产环境建议使用 Nginx 反向代理并配置 HTTPS。
4. **会话超时**：可以在 Flask 中配置 `PERMANENT_SESSION_LIFETIME`。
5. **定期清理**：设置定时任务清理过期的在线会话和日志记录。

---

## 九、常见问题排查

| 问题           | 解决方法                                                 |
| ------------ | ---------------------------------------------------- |
| OpenVPN 认证失败 | 检查 `verify.py` 权限，确保 OpenVPN 服务有执行权限；查看 OpenVPN 日志   |
| Web 管理端无法启动  | 检查端口 5000 是否被占用，用 `netstat -ano \| findstr :5000` 查看 |
| 数据库连接错误      | 检查 `DB_PATH` 路径是否正确，目录是否有写入权限                        |
| 在线用户不更新      | 检查 `active_sessions` 表是否有数据，可配置定时清理脚本                |
| 客户端配置文件生成失败  | 确保 `temp` 目录已创建且有写入权限                                |

---

## 十、总结

本方案实现了一个完整的 OpenVPN 账号管理 Web 系统：

- **验证脚本**：Python 脚本直接与数据库交互，完成用户名密码验证
- **Web 管理端**：Flask 提供完整的用户管理、在线监控、日志查询界面
- **数据库**：SQLite 轻量级数据库，无需额外安装
- **客户端配置**：支持一键生成客户端配置文件

相比其他方案，本方案的优势在于：全部使用 Python 实现，无需额外安装其他软件；密码采用哈希存储，安全性更高；提供完整的 Web 管理界面，操作便捷；数据库可随时备份和迁移。

如需扩展功能（如双因素认证、LDAP 对接、流量统计等），可在现有代码基础上继续开发。
