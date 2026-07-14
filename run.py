"""
OpenVPN Web 管理系统 - PyInstaller 打包入口脚本
用于将项目打包为独立可执行文件

打包后的目录结构：
  dist/OpenVPN-WebAdmin/
  ├── OpenVPN-WebAdmin.exe    # 主程序
  ├── .env                    # 用户配置文件（从 .env.example 复制）
  ├── .env.example            # 配置文件模板
  ├── auth.db                 # 数据库（运行后自动生成）
  ├── logs/                   # 日志目录（运行后自动生成）
  ├── temp/                   # 临时文件目录（运行后自动生成）
  └── _internal/              # PyInstaller 内部依赖（自动生成）
"""

import os
import sys

# 导入配置模块（此时 config.py 已根据 IS_FROZEN 正确设置了路径）
from config import IS_FROZEN, APP_DIR, RES_DIR


def resource_path(relative_path):
    """
    获取资源文件的绝对路径（兼容 PyInstaller 打包后的路径）
    - 打包模式：从临时解压目录（sys._MEIPASS）读取只读资源
    - 开发模式：从项目源码目录读取
    """
    if IS_FROZEN:
        return os.path.join(RES_DIR, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


if __name__ == '__main__':
    # 导入 Flask 应用和数据库模块
    import app as flask_app

    # 打包模式下，更新 Flask 的模板和静态文件路径为临时解压目录
    # 这些是只读资源，从 PyInstaller 打包的临时目录中读取
    flask_app.app.template_folder = resource_path('templates')
    flask_app.app.static_folder = resource_path('static')

    # 初始化数据库（数据库文件位于 EXE 同级目录，由 config.APP_DIR 决定）
    flask_app.database.init_db()

    # 打印启动信息
    print("=" * 50)
    print("  OpenVPN Web 管理系统")
    print("=" * 50)
    print(f"  运行模式: {'打包模式 (EXE)' if IS_FROZEN else '开发模式'}")
    print(f"  数据目录: {APP_DIR}")
    print(f"  资源目录: {RES_DIR}")
    print(f"  访问地址: http://localhost:5000")
    print(f"  默认账号: admin / admin123")
    print("=" * 50)
    print()
    print("  提示: 如需修改配置，请编辑 EXE 同级目录下的 .env 文件")
    print("        首次使用请将 .env.example 复制为 .env 并修改其中的值")
    print()

    # 使用 waitress 作为生产服务器
    try:
        from waitress import serve
        serve(flask_app.app, host='0.0.0.0', port=5000)
    except ImportError:
        flask_app.app.run(host='0.0.0.0', port=5000, debug=False)
