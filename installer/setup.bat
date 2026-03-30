@echo off
chcp 65001 >nul
title 符籙便簽 v3.0 安装程序

:: 检查是否在临时目录（ZIP内部直接运行）
echo %~dp0 | findstr /i "\\Temp\\" >nul
if not errorlevel 1 (
    echo.
    echo  ⚠  检测到您从 ZIP 内部运行！
    echo.
    echo  请先将 ZIP 解压到文件夹，再运行 setup.bat
    echo.
    pause
    exit /b 1
)

:: 用内置 Python 运行安装程序
set "DIR=%~dp0"
set "PYTHON=%DIR%files\python.exe"

if not exist "%PYTHON%" (
    echo 找不到 Python 运行时，请重新下载安装包！
    pause
    exit /b 1
)

:: 启动 GUI 安装程序（隐藏控制台）
start "" "%PYTHON%w" "%DIR%setup.pyw"
