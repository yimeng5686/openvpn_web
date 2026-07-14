"""
OpenVPN Web 管理系统 - 配置文件
包含所有可配置参数，避免在代码中硬编码
支持通过 .env 文件或系统环境变量覆盖默认值
优先级：系统环境变量 > .env 文件 > 代码中的默认值

路径策略说明：
- 开发模式：所有文件（.env、数据库、日志）基于项目源码目录
- 打包模式（PyInstaller EXE）：.env 和可写文件基于 EXE 所在目录，
  模板/静态资源等只读文件从打包临时目录读取
"""

import os
import sys
import secrets

# ==================== 运行模式检测 ====================
# 判断当前是否运行在 PyInstaller 打包环境中
# PyInstaller 运行时会设置 sys._MEIPASS 属性指向临时解压目录
IS_FROZEN = getattr(sys, 'frozen', False)

# ==================== 路径计算 ====================
if IS_FROZEN:
    # 打包模式：EXE 所在目录作为数据目录（.env、数据库、日志等可写文件）
    APP_DIR = os.path.dirname(sys.executable)
    # 打包模式：临时解压目录作为资源目录（模板、静态文件等只读资源）
    RES_DIR = sys._MEIPASS
else:
    # 开发模式：源码目录同时作为数据目录和资源目录
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    RES_DIR = APP_DIR

# ==================== 加载 .env 文件 ====================
# .env 文件始终从 EXE 同级目录（打包模式）或项目根目录（开发模式）读取
# 这样用户可以在 EXE 旁边放置 .env 文件来修改配置，无需重新打包
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(APP_DIR, ".env")
    load_dotenv(_env_path, override=False)  # override=False: 系统环境变量优先于 .env 文件
except ImportError:
    pass  # 未安装 python-dotenv 时静默跳过，不影响运行

# ==================== 基础路径配置 ====================
# 项目根目录（开发模式下为源码目录，打包模式下为 EXE 所在目录）
BASE_DIR = APP_DIR

# 数据库文件路径（可写，放在 EXE 同级目录）
DB_PATH = os.path.join(APP_DIR, "auth.db")

# 临时文件目录（可写，用于生成客户端配置文件等）
TEMP_DIR = os.path.join(APP_DIR, "temp")

# 日志文件目录（可写）
LOG_DIR = os.path.join(APP_DIR, "logs")

# OpenVPN 状态日志路径（由 OpenVPN 服务端生成，可写）
OPENVPN_STATUS_LOG = os.path.join(APP_DIR, "status.log")

# ==================== Flask 配置 ====================
# 密钥（用于 session 加密等，生产环境请修改为强随机字符串）
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# 会话有效期（秒），默认 24 小时
PERMANENT_SESSION_LIFETIME = 86400

# ==================== 服务器配置 ====================
# 监听地址
HOST = "0.0.0.0"
# 监听端口
PORT = 5000
# 调试模式（生产环境务必设为 False）
DEBUG = False

# ==================== OpenVPN 配置 ====================
# OpenVPN 服务器地址（用于生成客户端配置文件）
OPENVPN_SERVER_IP = os.environ.get("OPENVPN_SERVER_IP", "YOUR_SERVER_IP")
# OpenVPN 服务器端口
OPENVPN_SERVER_PORT = int(os.environ.get("OPENVPN_SERVER_PORT", 1194))
# OpenVPN 协议（udp / tcp）
OPENVPN_PROTOCOL = os.environ.get("OPENVPN_PROTOCOL", "tcp")
# OpenVPN 加密算法
OPENVPN_CIPHER = "AES-256-GCM"

# ==================== 默认管理员配置 ====================
# 默认管理员用户名
DEFAULT_ADMIN_USERNAME = "admin"
# 默认管理员密码（首次初始化数据库时使用）
DEFAULT_ADMIN_PASSWORD = "admin123"

# ==================== 安全配置 ====================
# 密码最小长度
MIN_PASSWORD_LENGTH = 6
# 用户名正则验证规则
USERNAME_PATTERN = r"^[a-zA-Z0-9_]{3,32}$"
# 会话过期时间（小时），超过此时间的在线会话将被清理
SESSION_EXPIRE_HOURS = 24

# ==================== 分页配置 ====================
# 每页显示日志条数
LOG_PER_PAGE = 20
