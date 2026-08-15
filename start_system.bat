@echo off
echo ========================================
echo    AutoSRE 系统启动
echo ========================================
echo.

echo [1/3] 检查 Docker 服务...
docker ps >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未运行，请先启动 Docker
    pause
    exit /b 1
)
echo [OK] Docker 运行正常

echo.
echo [2/3] 启动 API 服务器...
start "AutoSRE API" python api_server.py

echo.
echo [3/3] 等待服务启动...
timeout /t 3 >nul

echo.
echo ========================================
echo    AutoSRE 系统已启动！
echo.
echo    Web UI:  http://localhost:9999
echo    API 文档: http://localhost:9999/docs
echo    健康检查: http://localhost:9999/health
echo.
echo    API Key: autosre-admin-2024
echo ========================================
echo.
pause
