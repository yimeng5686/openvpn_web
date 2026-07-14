"""
OpenVPN Web 管理系统 - Flask 主程序
提供 Web 管理后台，实现用户管理、在线监控、日志查询、客户端配置下载等功能
"""

import os
import re
import hashlib
import datetime
import logging
import subprocess

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, send_file
)
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# 导入项目配置和数据库模块
from config import (
    SECRET_KEY, PERMANENT_SESSION_LIFETIME, HOST, PORT, DEBUG,
    TEMP_DIR, LOG_DIR, OPENVPN_STATUS_LOG,
    OPENVPN_SERVER_IP, OPENVPN_SERVER_PORT, OPENVPN_PROTOCOL, OPENVPN_CIPHER,
    MIN_PASSWORD_LENGTH, USERNAME_PATTERN, SESSION_EXPIRE_HOURS, LOG_PER_PAGE,
    DEFAULT_ADMIN_USERNAME
)
import database

# ==================== 日志配置 ====================
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== Flask 应用初始化 ====================
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(seconds=PERMANENT_SESSION_LIFETIME)

# 确保临时目录存在
os.makedirs(TEMP_DIR, exist_ok=True)

# ==================== Flask-Login 配置 ====================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    """用户模型类，用于 Flask-Login"""
    def __init__(self, id, username, is_admin=True):
        self.id = id
        self.username = username
        self.is_admin = is_admin


@login_manager.user_loader
def load_user(user_id):
    """根据用户ID加载用户对象"""
    user = database.get_user_by_id(user_id)
    if user:
        return User(user['id'], user['username'])
    return None


# ==================== 路由定义 ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    # 如果用户已登录，直接跳转到仪表盘
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # 验证用户凭据
        user = database.get_user_by_username(username)
        if user and hashlib.sha256(password.encode()).hexdigest() == user['password_hash']:
            # 登录成功
            login_user(User(user['id'], user['username']))
            session.permanent = True  # 启用会话过期
            logger.info(f"管理员登录成功: {username}")
            flash('登录成功！', 'success')
            # 跳转到之前请求的页面
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            logger.warning(f"登录失败: {username}")
            flash('用户名或密码错误', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """退出登录"""
    logger.info(f"用户退出登录: {current_user.username}")
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    """仪表盘 - 显示统计数据和系统状态"""
    try:
        stats = database.get_dashboard_stats()

        # 检查 OpenVPN 服务状态
        service_status = "未知"
        try:
            result = subprocess.run(
                ['sc', 'query', 'OpenVPNService'],
                capture_output=True, text=True, timeout=5
            )
            if 'RUNNING' in result.stdout:
                service_status = "运行中"
            elif 'STOPPED' in result.stdout:
                service_status = "已停止"
        except Exception:
            service_status = "无法检测"

        return render_template('dashboard.html',
                               stats=stats,
                               service_status=service_status,
                               db_path=database.DB_PATH)
    except Exception as e:
        logger.error(f"仪表盘加载失败: {e}")
        flash('加载仪表盘数据时出错', 'danger')
        return render_template('dashboard.html',
                               stats={'total_users': 0, 'active_users': 0, 'online_users': 0, 'today_connects': 0},
                               service_status="未知",
                               db_path=database.DB_PATH)


@app.route('/users')
@login_required
def users():
    """用户管理页面"""
    user_list = database.get_all_users()
    return render_template('users.html', users=user_list)


@app.route('/user/add', methods=['POST'])
@login_required
def add_user():
    """添加新用户"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    notes = request.form.get('notes', '').strip()

    # 验证用户名格式
    if not re.match(USERNAME_PATTERN, username):
        flash(f'用户名格式错误：仅支持字母、数字、下划线，长度3-32', 'danger')
        return redirect(url_for('users'))

    # 验证密码长度
    if len(password) < MIN_PASSWORD_LENGTH:
        flash(f'密码长度至少{MIN_PASSWORD_LENGTH}位', 'danger')
        return redirect(url_for('users'))

    # 密码哈希
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    # 添加用户
    success, msg = database.add_user(username, password_hash, notes)
    if success:
        logger.info(f"添加用户: {username}, 操作者: {current_user.username}")
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('users'))


@app.route('/user/edit/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    """编辑用户（重置密码/启用/禁用/删除）"""
    action = request.form.get('action')

    if action == 'reset_password':
        # 重置密码
        new_password = request.form.get('new_password', '')
        if len(new_password) < MIN_PASSWORD_LENGTH:
            flash(f'新密码长度至少{MIN_PASSWORD_LENGTH}位', 'danger')
            return redirect(url_for('users'))

        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        database.update_user_password(user_id, password_hash)
        logger.info(f"重置用户密码, 用户ID: {user_id}, 操作者: {current_user.username}")
        flash('密码重置成功', 'success')

    elif action == 'toggle_status':
        # 切换启用/禁用状态
        new_status = database.toggle_user_status(user_id)
        status_text = "启用" if new_status == 1 else "禁用"
        logger.info(f"切换用户状态: 用户ID {user_id} -> {status_text}, 操作者: {current_user.username}")
        flash(f'用户已{status_text}', 'success')

    elif action == 'delete':
        # 删除用户
        if database.delete_user(user_id):
            logger.info(f"删除用户, 用户ID: {user_id}, 操作者: {current_user.username}")
            flash('用户已删除', 'success')
        else:
            flash('无法删除该用户（可能是管理员账户）', 'danger')

    return redirect(url_for('users'))


@app.route('/online')
@login_required
def online_users():
    """在线用户监控页面"""
    online_list = database.get_online_users()

    # 尝试读取 OpenVPN 状态日志获取更准确的在线信息
    status_info = []
    try:
        if os.path.exists(OPENVPN_STATUS_LOG):
            with open(OPENVPN_STATUS_LOG, 'r', encoding='utf-8') as f:
                status_info = f.readlines()
    except Exception as e:
        logger.warning(f"读取 OpenVPN 状态日志失败: {e}")

    return render_template('online.html', users=online_list)


@app.route('/logs')
@login_required
def logs():
    """连接日志页面（支持分页）"""
    page = request.args.get('page', 1, type=int)
    log_list, total_pages, current_page = database.get_connection_logs(page, LOG_PER_PAGE)
    return render_template('logs.html', logs=log_list, page=current_page, total_pages=total_pages)


@app.route('/client/download')
@login_required
def client_download():
    """客户端下载页面"""
    return render_template('client_download.html')


@app.route('/client/config/<username>')
@login_required
def generate_client_config(username):
    """生成并下载客户端配置文件"""
    # 检查用户是否存在
    if not database.user_exists(username):
        flash('用户不存在', 'danger')
        return redirect(url_for('users'))

    # 生成客户端配置文件内容
    config_content = f'''
##############################################
# Sample client-side OpenVPN 2.6 config file #
# for connecting to multi-client server.     #
#                                            #
# This configuration can be used by multiple #
# clients, however each client should have   #
# its own cert and key files.                #
#                                            #
# On Windows, you might want to rename this  #
# file so it has a .ovpn extension           #
##############################################

# Specify that we are a client and that we
# will be pulling certain config file directives
# from the server.
client

# Use the same setting as you are using on
# the server.
# On most systems, the VPN will not function
# unless you partially or fully disable
# the firewall for the TUN/TAP interface.
;dev tap
dev tun

# Windows needs the TAP-Win32 adapter name
# from the Network Connections panel
# if you have more than one.  On XP SP2,
# you may need to disable the firewall
# for the TAP adapter.
;dev-node MyTap

# Are we connecting to a TCP or
# UDP server?  Use the same setting as
# on the server.
proto {OPENVPN_PROTOCOL}

# The hostname/IP and port of the server.
# You can have multiple remote entries
# to load balance between the servers.
remote {OPENVPN_SERVER_IP} {OPENVPN_SERVER_PORT}

# Choose a random host from the remote
# list for load-balancing.  Otherwise
# try hosts in the order specified.
;remote-random

# Keep trying indefinitely to resolve the
# host name of the OpenVPN server.  Very useful
# on machines which are not permanently connected
# to the internet such as laptops.
resolv-retry infinite

# Most clients don't need to bind to
# a specific local port number.
nobind

# Downgrade privileges after initialization (non-Windows only)
;user openvpn
;group openvpn

# Try to preserve some state across restarts.
persist-tun

# If you are connecting through an
# HTTP proxy to reach the actual OpenVPN
# server, put the proxy server/IP and
# port number here.  See the man page
# if your proxy server requires
# authentication.
;http-proxy-retry # retry on connection failures
;http-proxy [proxy server] [proxy port #]

# Wireless networks often produce a lot
# of duplicate packets.  Set this flag
# to silence duplicate packet warnings.
;mute-replay-warnings

# SSL/TLS parms.
# See the server config file for more
# description.  It's best to use
# a separate .crt/.key file pair
# for each client.  A single ca
# file can be used for all clients.
ca ca.crt
cert client.crt
key client.key

# Verify server certificate by checking that the
# certificate has the correct key usage set.
# This is an important precaution to protect against
# a potential attack discussed here:
#  http://openvpn.net/howto.html#mitm
auth-user-pass
# To use this feature, you will need to generate
# your server certificates with the keyUsage set to
#   digitalSignature, keyEncipherment
# and the extendedKeyUsage to
#   serverAuth
# EasyRSA can do this for you.
remote-cert-tls server

# Allow to connect to really old OpenVPN versions
# without AEAD support (OpenVPN 2.3.x or older)
# This adds AES-256-CBC as fallback cipher and
# keeps the modern ciphers as well.
;data-ciphers AES-256-GCM:AES-128-GCM:?CHACHA20-POLY1305:AES-256-CBC

# If a tls-auth key is used on the server
# then every client must also have the key.
;tls-auth ta.key 1

# Set log file verbosity.
verb 3

# Silence repeating messages
;mute 20


# OpenVPN 客户端配置文件
# 用户名: {username}
# 请在连接时输入对应的密码
'''

    # 写入临时文件
    config_filename = f"{username}.ovpn"
    config_path = os.path.join(TEMP_DIR, config_filename)

    try:
        with open(config_path, "w", encoding='utf-8') as f:
            f.write(config_content)

        logger.info(f"生成客户端配置: {username}, 操作者: {current_user.username}")
        return send_file(config_path, as_attachment=True, download_name=config_filename)
    except Exception as e:
        logger.error(f"生成客户端配置失败: {e}")
        flash('生成配置文件失败', 'danger')
        return redirect(url_for('users'))


@app.route('/cleanup')
@login_required
def cleanup_sessions():
    """手动清理过期会话"""
    deleted = database.cleanup_expired_sessions(SESSION_EXPIRE_HOURS)
    flash(f'已清理 {deleted} 条过期会话记录', 'success')
    return redirect(url_for('online_users'))


# ==================== 错误处理 ====================

@app.errorhandler(404)
def page_not_found(e):
    """404 页面未找到"""
    return render_template('login.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    """500 服务器内部错误"""
    logger.error(f"服务器内部错误: {e}")
    return render_template('login.html'), 500


# ==================== 应用启动 ====================

def create_app():
    """应用工厂函数，用于创建和配置 Flask 应用"""
    # 初始化数据库
    database.init_db()
    return app


if __name__ == '__main__':
    # 初始化数据库
    database.init_db()
    logger.info(f"OpenVPN Web 管理系统启动，访问地址: http://{HOST}:{PORT}")
    logger.info(f"默认管理员账号: {DEFAULT_ADMIN_USERNAME} / admin123")

    # 使用 waitress 作为生产服务器（如果可用），否则使用 Flask 开发服务器
    try:
        from waitress import serve
        logger.info("使用 waitress 生产服务器")
        serve(app, host=HOST, port=PORT)
    except ImportError:
        logger.warning("未安装 waitress，使用 Flask 开发服务器（不建议用于生产环境）")
        app.run(host=HOST, port=PORT, debug=DEBUG)
