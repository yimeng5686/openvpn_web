# -*- mode: python ; coding: utf-8 -*-
"""
=============================================================================
  PyInstaller 打包配置文件 - verify.exe（OpenVPN 认证程序）
=============================================================================

一、说明
--------
verify.exe 是专供 OpenVPN 服务端调用的轻量级认证程序。
它与 OpenVPN-WebAdmin.exe 共享同一目录下的 auth.db 和 .env 文件。

运行原理：
  OpenVPN 客户端连接 → OpenVPN 调用 verify.exe（via-env 模式）
  → verify.exe 读取环境变量中的 username/password
  → verify.exe 查询同目录下的 auth.db 验证用户
  → 返回 0（成功）或 1（失败），同时写入连接日志

二、环境准备
------------
1. Python 3.10+ 已安装并可用
2. 项目虚拟环境已创建且依赖已安装：
   > uv venv --python 3.10
   > uv pip install -r requirements.txt

三、打包命令
------------
# 方式一：使用虚拟环境中的 PyInstaller
> .venv\Scripts\pyinstaller.exe verify.spec --noconfirm

# 方式二：如果系统已安装 PyInstaller
> pyinstaller verify.spec --noconfirm

四、打包产物
------------
dist/verify/
├── verify.exe        # 认证程序（需要复制到 OpenVPN-WebAdmin 目录）
└── _internal/        # PyInstaller 运行时依赖

五、OpenVPN 配置
----------------
打包模式（推荐，无需 Python 环境）：
  auth-user-pass-verify "C:\\OpenVPN-WebAdmin\\verify.exe" via-env

开发模式（需要 Python 环境）：
  auth-user-pass-verify "C:\\Python310\\python.exe C:\\OpenVPN-WebAdmin\\verify.py" via-env

六、手动测试
------------
# PowerShell 中模拟 OpenVPN 环境变量调用
> $env:username = "admin"; $env:password = "admin123"; .\verify.exe
> echo $LASTEXITCODE    # 0 = 认证成功

> $env:username = "admin"; $env:password = "wrong"; .\verify.exe
> echo $LASTEXITCODE    # 1 = 认证失败

七、注意事项
------------
- verify.exe 必须与 auth.db 在同一目录
- 打包顺序：先打包 verify.exe，再打包 OpenVPN-WebAdmin.exe
  （主程序打包时会自动复制 verify.exe 到输出目录）
- 如需修改认证逻辑，修改 verify.py 后重新打包即可
=============================================================================
"""

import os

block_cipher = None

PROJECT_DIR = os.path.abspath('.')

a = Analysis(
    ['verify.py'],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=[],  # verify.exe 不需要模板和静态资源，保持轻量
    hiddenimports=[
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大型模块，减小 verify.exe 体积
        'flask',
        'flask_login',
        'flask_wtf',
        'waitress',
        'wtforms',
        'jinja2',
        'werkzeug',
        'markupsafe',
        'itsdangerous',
        'click',
        'blinker',
        'unittest',
        'xml',
        'html',
        'http',
        'email',
        'pydoc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='verify',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 控制台模式（OpenVPN 通过命令行调用）
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='verify',
)
