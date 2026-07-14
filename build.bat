@echo off
chcp 65001 >nul
title OpenVPN Web 管理系统 - 打包工具

echo ============================================
echo    OpenVPN Web 管理系统 - 一键打包
echo ============================================
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查 PyInstaller
.venv\Scripts\pip.exe show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 正在安装 PyInstaller...
    .venv\Scripts\pip.exe install pyinstaller
    echo.
)

echo [步骤 1/3] 打包 verify.exe（VPN 认证程序）...
.venv\Scripts\pyinstaller.exe verify.spec --noconfirm
if %errorlevel% neq 0 (
    echo [错误] verify.exe 打包失败！
    pause
    exit /b 1
)
echo [完成] verify.exe 打包成功
echo.

echo [步骤 2/3] 打包 OpenVPN-WebAdmin.exe（Web 管理后台）...
.venv\Scripts\pyinstaller.exe openvpn_webadmin.spec --noconfirm
if %errorlevel% neq 0 (
    echo [错误] OpenVPN-WebAdmin.exe 打包失败！
    pause
    exit /b 1
)
echo [完成] OpenVPN-WebAdmin.exe 打包成功
echo.

echo [步骤 3/3] 验证打包产物...
if exist "dist\OpenVPN-WebAdmin\OpenVPN-WebAdmin.exe" (
    echo   [OK] OpenVPN-WebAdmin.exe
) else (
    echo   [缺失] OpenVPN-WebAdmin.exe
)
if exist "dist\OpenVPN-WebAdmin\verify.exe" (
    echo   [OK] verify.exe
) else (
    echo   [缺失] verify.exe
)
if exist "dist\OpenVPN-WebAdmin\.env.example" (
    echo   [OK] .env.example
) else (
    echo   [缺失] .env.example
)
echo.

echo ============================================
echo    打包完成！
echo ============================================
echo.
echo  产物目录: %cd%\dist\OpenVPN-WebAdmin\
echo.
echo  使用方法:
echo    1. 将 dist\OpenVPN-WebAdmin\ 整个目录复制到目标服务器
echo    2. 复制 .env.example 为 .env 并修改配置
echo    3. 双击 OpenVPN-WebAdmin.exe 启动管理后台
echo    4. 在 OpenVPN 配置中引用 verify.exe 进行认证
echo.

pause
