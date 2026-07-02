@echo off
chcp 65001 >nul
title AI 医药业务助手

echo ========================================
echo   AI 医药业务日报与月报助手
echo ========================================
echo.

REM Auto-detect project directory (where this .bat file is located)
cd /d "%~dp0"
echo 📁 项目目录: %cd%
echo.

REM Check if .env exists, if not create from example
if not exist ".env" (
    echo [0/3] 创建 .env 配置文件...
    copy .env.example .env >nul
    echo   ✅ 已使用 Mock 模式（无需 API Key）
)

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)
echo   ✅ Python 已就绪

echo [2/3] 检查依赖...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo   ⏳ 安装依赖中...
    pip install -r requirements.txt
)
echo   ✅ 依赖已就绪

echo [3/3] 启动 Streamlit 应用...
echo.
echo ========================================
echo   🚀 正在启动...
echo   本机访问:  http://localhost:8501
echo   局域网访问:  http://<本机IP>:8501
echo   按 Ctrl+C 停止服务器
echo ========================================
echo.

streamlit run app.py --server.headless true

pause
