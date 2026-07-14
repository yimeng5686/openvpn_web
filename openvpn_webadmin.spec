# -*- mode: python ; coding: utf-8 -*-
"""
=============================================================================
  PyInstaller 打包配置文件 - OpenVPN-WebAdmin.exe（Web 管理后台）
=============================================================================

一、说明
--------
将 OpenVPN Web 管理系统打包为独立可执行文件，用户无需安装 Python 即可运行。
打包产物包含两个 EXE：
  - OpenVPN-WebAdmin.exe  → Web 管理后台（浏览器访问 http://localhost:5000）
  - verify.exe            → VPN 认证程序（被 OpenVPN 服务端调用）

二、环境准备
------------
1. Python 3.10+ 已安装并可用
2. 项目虚拟环境已创建且依赖已安装：
   > uv venv --python 3.10
   > uv pip install -r requirements.txt
3. PyInstaller 已安装（包含在 requirements.txt 中）：
   > uv pip install pyinstaller

三、打包命令（按顺序执行）
--------------------------
# 步骤 1：先打包 verify.exe（认证程序）
> .venv\Scripts\pyinstaller.exe verify.spec --noconfirm

# 步骤 2：再打包 OpenVPN-WebAdmin.exe（主程序，会自动复制 verify.exe）
> .venv\Scripts\pyinstaller.exe openvpn_webadmin.spec --noconfirm

# 或者使用一键打包脚本：
> .\build.bat

四、打包产物
------------
dist/OpenVPN-WebAdmin/
├── OpenVPN-WebAdmin.exe      # Web 管理后台主程序
├── verify.exe                # VPN 认证程序（由步骤 1 生成，自动复制）
├── .env.example              # 配置文件模板（自动复制）
├── auth.db                   # SQLite 数据库（首次运行自动生成）
├── logs/                     # 日志目录（自动创建）
├── temp/                     # 临时文件目录（自动创建）
├── config/
│   └── server.ovpn           # OpenVPN 服务端配置模板
└── _internal/                # PyInstaller 运行时依赖

五、部署步骤
------------
1. 将 dist/OpenVPN-WebAdmin/ 整个目录复制到目标服务器（如 C:\OpenVPN-WebAdmin\）
2. 复制 .env.example 为 .env 并修改配置：
   > copy .env.example .env
   > notepad .env
   必须修改的配置项：
     OPENVPN_SERVER_IP=你的VPN服务器IP地址
3. 双击 OpenVPN-WebAdmin.exe 启动管理后台
4. 浏览器访问 http://localhost:5000，默认账号 admin / admin123

六、OpenVPN 服务端对接
----------------------
编辑 OpenVPN 服务端配置文件（通常在 C:\Program Files\OpenVPN\config\server\），
添加或修改以下配置项：

  # 认证脚本（修改路径为实际部署路径）
  auth-user-pass-verify "C:\\OpenVPN-WebAdmin\\verify.exe" via-env
  script-security 3
  client-cert-not-required
  username-as-common-name

  # 状态日志（Web 管理端读取此文件获取在线信息）
  status "C:\\OpenVPN-WebAdmin\\status.log" 5

  # 日志文件
  log-append "C:\\OpenVPN-WebAdmin\\openvpn.log"

修改后重启 OpenVPN 服务：
  > Restart-Service -Name "OpenVPNService"

七、路径策略说明
----------------
打包后程序区分两种路径：
  - APP_DIR（EXE 所在目录）：存放可写文件（.env、auth.db、logs/、temp/）
  - RES_DIR（临时解压目录）：存放只读资源（templates/、static/）

  .env 和 auth.db 放在 EXE 同级目录，用户可直接编辑和备份。
  模板和静态资源打包在 EXE 内部，每次运行自动解压到临时目录。

八、配置优先级
--------------
系统环境变量 > .env 文件 > config.py 中的默认值

  示例：通过环境变量覆盖配置（无需修改 .env 文件）
  > $env:OPENVPN_SERVER_IP = "203.0.113.10"
  > .\OpenVPN-WebAdmin.exe

九、常见问题
------------
Q: 打包后启动报错 "Failed to execute script run"？
A: 检查是否遗漏了 hiddenimports，在 spec 文件的 hiddenimports 列表中添加。

Q: verify.exe 认证失败？
A: 1. 确认 verify.exe 与 auth.db 在同一目录
   2. 确认 OpenVPN 服务账户（SYSTEM）有权限访问该目录
   3. 检查 logs/verify.log 日志文件

Q: 如何修改端口？
A: 编辑 .env 文件添加 PORT=8080，或设置环境变量 $env:PORT=8080

Q: 如何更新版本？
A: 重新打包后，只需替换 EXE 文件和 _internal 目录，
   .env、auth.db、logs/ 不受影响。
=============================================================================
"""

import os
import shutil

block_cipher = None

# 项目根目录
PROJECT_DIR = os.path.abspath('.')

a = Analysis(
    ['run.py'],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=[
        # 包含模板文件（只读资源，打包到临时目录）
        ('templates', 'templates'),
        # 包含静态资源（只读资源，打包到临时目录）
        ('static', 'static'),
        # 包含 OpenVPN 服务端配置模板（只读参考）
        ('config', 'config'),
    ],
    hiddenimports=[
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
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='OpenVPN-WebAdmin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 使用控制台模式，方便查看日志
    icon=None,  # 可添加自定义图标: icon='static/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OpenVPN-WebAdmin',
)

# ==================== 打包后处理 ====================
# 将 .env.example 复制到输出目录，方便用户复制为 .env 使用
# 注意：.env 文件不打包（包含敏感信息），仅提供 .env.example 模板
DIST_DIR = os.path.join(PROJECT_DIR, 'dist', 'OpenVPN-WebAdmin')
env_example_src = os.path.join(PROJECT_DIR, '.env.example')
env_example_dst = os.path.join(DIST_DIR, '.env.example')

if os.path.exists(env_example_src) and os.path.exists(DIST_DIR):
    shutil.copy2(env_example_src, env_example_dst)
    print(f"[打包后处理] 已复制 .env.example 到 {DIST_DIR}")

# 将 verify.exe 及其 _internal 内容合并到主 EXE 输出目录
# 打包顺序：先执行 pyinstaller verify.spec，再执行 pyinstaller openvpn_webadmin.spec
# 合并原理：两个 EXE 的 .pyz 文件名不同（OpenVPN-WebAdmin.pyz vs verify.pyz），
#           共享的 Python 运行时和依赖库版本一致，合并不会冲突
verify_dist_dir = os.path.join(PROJECT_DIR, 'dist', 'verify')
verify_exe_src = os.path.join(verify_dist_dir, 'verify.exe')
verify_internal_src = os.path.join(verify_dist_dir, '_internal')
main_internal_dst = os.path.join(DIST_DIR, '_internal')

if os.path.exists(verify_exe_src) and os.path.exists(DIST_DIR):
    # 复制 verify.exe 到主程序目录
    shutil.copy2(verify_exe_src, os.path.join(DIST_DIR, 'verify.exe'))
    print(f"[打包后处理] 已复制 verify.exe 到 {DIST_DIR}")

    # 合并 verify 的 _internal 内容到主程序的 _internal 目录
    # 两个 EXE 共享同一个 _internal，各自通过 .pyz 文件名区分字节码
    if os.path.exists(verify_internal_src) and os.path.exists(main_internal_dst):
        for item in os.listdir(verify_internal_src):
            src_item = os.path.join(verify_internal_src, item)
            dst_item = os.path.join(main_internal_dst, item)
            if os.path.isdir(src_item):
                # 目录：递归合并（如 collected packages 子目录）
                if os.path.exists(dst_item):
                    shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                else:
                    shutil.copytree(src_item, dst_item)
            else:
                # 文件：直接复制（同名文件会被覆盖，但同版本依赖内容相同）
                if not os.path.exists(dst_item):
                    shutil.copy2(src_item, dst_item)
        print(f"[打包后处理] 已合并 verify/_internal 到主程序 _internal 目录")
elif os.path.exists(DIST_DIR):
    print(f"[打包后处理] 警告: 未找到 verify.exe，请先执行 pyinstaller verify.spec")
    print(f"             寻找路径: {verify_dist_dir}")

# 在输出目录创建必要的空目录
for dir_name in ['logs', 'temp']:
    dir_path = os.path.join(DIST_DIR, dir_name)
    os.makedirs(dir_path, exist_ok=True)
    print(f"[打包后处理] 已创建目录: {dir_path}")
