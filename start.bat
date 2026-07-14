@echo off
chcp 65001 >nul
title OpenVPN Web 管理系统

echo ============================================
echo    OpenVPN Web 管理系统 启动脚本
echo ============================================
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查虚拟环境是否存在
if exist ".venv\Scripts\python.exe" (
    echo [信息] 检测到虚拟环境，使用 .venv 中的 Python
    set PYTHON=.venv\Scripts\python.exe
) else (
    REM 检查系统 Python
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 未检测到 Python，请先安装 Python 3.10+
        echo 下载地址: https://www.python.org/downloads/
        echo.
        echo 或者使用 uv 创建虚拟环境:
        echo   uv venv --python 3.10
        echo   uv pip install -r requirements.txt
        pause
        exit /b 1
    )
    set PYTHON=python
)

REM 检查是否需要安装依赖
%PYTHON% -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 正在安装项目依赖...
    if exist ".venv\Scripts\pip.exe" (
        .venv\Scripts\pip.exe install -r requirements.txt
    ) else (
        pip install -r requirements.txt
    )
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
    echo [信息] 依赖安装完成
    echo.
)

REM 初始化数据库（首次运行）
if not exist "auth.db" (
    echo [信息] 首次运行，正在初始化数据库...
    %PYTHON% database.py
    echo.
)

REM 启动应用
echo [信息] 正在启动 OpenVPN Web 管理系统...
echo [信息] 访问地址: http://localhost:5000
echo [信息] 默认管理员账号: admin / admin123
echo [信息] 按 Ctrl+C 停止服务
echo.

%PYTHON% app.py

pause
