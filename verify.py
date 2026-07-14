#!/usr/bin/env python3
"""
OpenVPN 认证程序
被 OpenVPN 服务端通过 auth-user-pass-verify 调用
接收从 OpenVPN 传递的用户名和密码，与数据库中的哈希密码进行比对
返回 0 表示认证成功，返回 1 表示认证失败

运行模式：
- 开发模式：作为 verify.py 由 Python 解释器运行
- 打包模式：作为 verify.exe 独立运行（无需 Python 环境）

路径策略：
- 开发模式：从项目源码目录读取 .env、auth.db、写入日志
- 打包模式：从 EXE 同级目录读取 .env、auth.db、写入日志
  （与 OpenVPN-WebAdmin.exe 共享同一目录和数据库）
"""

import logging
import os
import sys

# ==================== 运行模式检测与路径设置 ====================
# 判断当前是否运行在 PyInstaller 打包环境中
IS_FROZEN = getattr(sys, 'frozen', False)

if IS_FROZEN:
    # 打包模式：EXE 所在目录作为数据目录
    # verify.exe 与 OpenVPN-WebAdmin.exe 在同一目录，共享 auth.db 和 .env
    APP_DIR = os.path.dirname(sys.executable)
else:
    # 开发模式：源码目录作为数据目录
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# 将项目目录添加到 Python 路径，以便导入 config 和 database 模块
# 打包模式下这些模块已被 PyInstaller 内联，不需要额外添加
if not IS_FROZEN:
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)

# ==================== 加载 .env 配置 ====================
# 从 EXE 同级目录（打包模式）或项目根目录（开发模式）读取 .env
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(APP_DIR, ".env")
    load_dotenv(_env_path, override=False)
except ImportError:
    pass  # 未安装 python-dotenv 时静默跳过

# ==================== 导入项目模块 ====================
# 需要在路径设置和 .env 加载之后导入，确保 config 能正确读取环境变量
import database
from config import LOG_DIR

# ==================== 日志配置 ====================
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "verify.log"),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    主函数 - 被 OpenVPN 调用
    OpenVPN 通过环境变量（via-env 模式）或命令行参数传递用户名和密码
    """
    # OpenVPN 通过环境变量传递用户名和密码（使用 via-env 模式时）
    username = os.environ.get('username')
    password = os.environ.get('password')

    # 如果没有环境变量，尝试通过命令行参数获取（兼容 via-file 模式）
    if not username and len(sys.argv) >= 2:
        username = sys.argv[1]
    if not password and len(sys.argv) >= 3:
        password = sys.argv[2]

    # 获取客户端 IP（通过 OpenVPN 环境变量）
    client_ip = os.environ.get('untrusted_ip', 'unknown')

    # 检查凭据是否完整
    if not username or not password:
        logger.warning(f"认证失败：缺少用户名或密码，客户端IP: {client_ip}")
        database.log_connection("unknown", client_ip, False, "missing credentials")
        sys.exit(1)

    # 验证用户凭据
    success, msg = database.verify_user(username, password)

    # 记录连接日志
    database.log_connection(username, client_ip, success, msg)

    if success:
        logger.info(f"认证成功: {username}, 客户端IP: {client_ip}")
        sys.exit(0)  # 返回 0 表示认证成功
    else:
        logger.warning(f"认证失败: {username} - {msg}, 客户端IP: {client_ip}")
        sys.exit(1)  # 返回非 0 表示认证失败


if __name__ == "__main__":
    main()
