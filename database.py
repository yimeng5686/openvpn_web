"""
OpenVPN Web 管理系统 - 数据库模块
负责数据库的初始化、连接管理和基础操作
包含用户表、连接日志表、在线会话表
"""

import sqlite3
import hashlib
import datetime
import logging
import os

# 导入配置
from config import DB_PATH, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

# 配置日志
logger = logging.getLogger(__name__)


def get_db():
    """获取数据库连接，设置 row_factory 以便通过列名访问数据"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    初始化数据库表结构
    - users: 用户表（用户名、哈希密码、创建时间、状态、备注）
    - connection_logs: 连接日志表（连接时间、断开时间、客户端IP、流量等）
    - active_sessions: 在线会话表（用于实时监控在线用户）
    """
    # 确保数据库目录存在
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = get_db()
    cursor = conn.cursor()

    # 创建用户表
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

    # 创建连接日志表
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

    # 创建在线会话表（用于实时监控）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_sessions (
            username TEXT PRIMARY KEY,
            client_ip TEXT,
            login_time TEXT,
            bytes_sent INTEGER DEFAULT 0,
            bytes_received INTEGER DEFAULT 0
        )
    ''')

    # 创建默认管理员账户（密码使用 SHA-256 哈希存储）
    admin_hash = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password_hash, created_at, is_active)
        VALUES (?, ?, ?, ?)
    ''', (DEFAULT_ADMIN_USERNAME, admin_hash, datetime.datetime.now().isoformat(), 1))

    conn.commit()
    conn.close()
    logger.info("数据库初始化完成！")


def verify_user(username, password):
    """
    验证用户凭据
    :param username: 用户名
    :param password: 明文密码
    :return: (是否验证成功, 状态消息)
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT password_hash, is_active FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()

    # 用户不存在
    if not row:
        return False, "用户不存在"

    # 用户已被禁用
    if not row['is_active']:
        return False, "用户已被禁用"

    # 比对密码哈希
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash == row['password_hash']:
        return True, "验证成功"
    else:
        return False, "密码错误"


def log_connection(username, client_ip, success, status_detail=""):
    """
    记录连接日志
    :param username: 用户名
    :param client_ip: 客户端IP地址
    :param success: 是否认证成功
    :param status_detail: 状态详情
    """
    try:
        conn = get_db()
        cursor = conn.cursor()

        if success:
            # 记录连接成功日志
            cursor.execute('''
                INSERT INTO connection_logs (username, client_ip, connect_time, status)
                VALUES (?, ?, ?, ?)
            ''', (username, client_ip, datetime.datetime.now().isoformat(), "connected"))

            # 更新或插入在线会话记录
            cursor.execute('''
                INSERT OR REPLACE INTO active_sessions (username, client_ip, login_time)
                VALUES (?, ?, ?)
            ''', (username, client_ip, datetime.datetime.now().isoformat()))
        else:
            # 记录认证失败日志
            cursor.execute('''
                INSERT INTO connection_logs (username, client_ip, connect_time, status)
                VALUES (?, ?, ?, ?)
            ''', (username, client_ip, datetime.datetime.now().isoformat(), f"auth_failed: {status_detail}"))

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"记录连接日志失败: {e}")


def cleanup_expired_sessions(expire_hours=24):
    """
    清理超过指定时间无活动的会话
    :param expire_hours: 过期时间（小时），默认24小时
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        expire_time = (datetime.datetime.now() - datetime.timedelta(hours=expire_hours)).isoformat()
        cursor.execute('DELETE FROM active_sessions WHERE login_time < ?', (expire_time,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"已清理 {deleted} 条过期会话记录")
        return deleted
    except Exception as e:
        logger.error(f"清理过期会话失败: {e}")
        return 0


def get_dashboard_stats():
    """
    获取仪表盘统计数据
    :return: 包含各项统计数据的字典
    """
    conn = get_db()
    cursor = conn.cursor()

    # 总用户数（排除管理员）
    cursor.execute('SELECT COUNT(*) FROM users WHERE username != ?', (DEFAULT_ADMIN_USERNAME,))
    total_users = cursor.fetchone()[0]

    # 活跃用户数（7天内登录）
    seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    cursor.execute('SELECT COUNT(DISTINCT username) FROM connection_logs WHERE connect_time > ?', (seven_days_ago,))
    active_users = cursor.fetchone()[0]

    # 在线用户数
    cursor.execute('SELECT COUNT(*) FROM active_sessions')
    online_users = cursor.fetchone()[0]

    # 今天连接次数
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute('SELECT COUNT(*) FROM connection_logs WHERE connect_time LIKE ?', (f"{today}%",))
    today_connects = cursor.fetchone()[0]

    conn.close()

    return {
        'total_users': total_users,
        'active_users': active_users,
        'online_users': online_users,
        'today_connects': today_connects
    }


def get_all_users():
    """获取所有用户列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, created_at, is_active, notes FROM users ORDER BY id')
    user_list = cursor.fetchall()
    conn.close()
    return user_list


def add_user(username, password_hash, notes=""):
    """
    添加新用户
    :return: (是否成功, 消息)
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        created_at = datetime.datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO users (username, password_hash, created_at, is_active, notes) VALUES (?, ?, ?, 1, ?)',
            (username, password_hash, created_at, notes)
        )
        conn.commit()
        return True, f"用户 {username} 添加成功"
    except sqlite3.IntegrityError:
        return False, f"用户名 {username} 已存在"
    finally:
        conn.close()


def update_user_password(user_id, new_password_hash):
    """重置用户密码"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, user_id))
    conn.commit()
    conn.close()


def toggle_user_status(user_id):
    """切换用户启用/禁用状态"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_active FROM users WHERE id = ?', (user_id,))
    current = cursor.fetchone()
    if current:
        new_status = 0 if current['is_active'] == 1 else 1
        cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
    conn.close()
    return new_status if current else None


def delete_user(user_id):
    """删除用户（不允许删除管理员账户）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ? AND username != ?', (user_id, DEFAULT_ADMIN_USERNAME))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_online_users():
    """获取当前在线用户列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, client_ip, login_time
        FROM active_sessions
        ORDER BY login_time DESC
    ''')
    online_list = cursor.fetchall()
    conn.close()
    return online_list


def get_connection_logs(page=1, per_page=20):
    """
    获取连接日志（分页）
    :param page: 页码
    :param per_page: 每页条数
    :return: (日志列表, 总页数, 当前页码)
    """
    conn = get_db()
    cursor = conn.cursor()
    offset = (page - 1) * per_page

    # 获取总数
    cursor.execute('SELECT COUNT(*) FROM connection_logs')
    total = cursor.fetchone()[0]

    # 分页查询
    cursor.execute('''
        SELECT id, username, client_ip, connect_time, disconnect_time, status
        FROM connection_logs
        ORDER BY connect_time DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    log_list = cursor.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return log_list, total_pages, page


def user_exists(username):
    """检查用户是否存在"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_user_by_id(user_id):
    """根据ID获取用户信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_username(username):
    """根据用户名获取用户信息（含密码哈希，用于登录验证）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user


# 当直接运行此文件时，初始化数据库
if __name__ == "__main__":
    # 配置控制台日志输出
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    init_db()
    print(f"数据库已初始化，路径: {DB_PATH}")
