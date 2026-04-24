@echo off
REM ============================================================
REM  build_windows.bat — Build de Xtuber para Windows
REM  Genera: dist\Xtuber.exe
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════════════╗
echo ║       Xtuber — Build para Windows           ║
echo ╚══════════════════════════════════════════════╝
echo.

REM ── 1. Dependencias Python ───────────────────────────────────────────────
echo [1/4] Instalando dependencias Python...
pip install -r requirements.txt --quiet
if errorlevel 1 (echo ERROR: fallo pip install & exit /b 1)

REM ── 2. Descargar ffmpeg estático para Windows ────────────────────────────
if not exist "bin" mkdir bin

if not exist "bin\ffmpeg.exe" (
    echo [2/4] Descargando ffmpeg para Windows...
    REM Descarga la build esencial de gyan.dev (estática, sin dependencias)
    set FFMPEG_URL=https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip
    curl -L "!FFMPEG_URL!" -o "%TEMP%\ffmpeg_win.zip" --progress-bar
    if errorlevel 1 (echo ERROR: fallo descarga ffmpeg & exit /b 1)

    echo    Extrayendo ffmpeg.exe...
    powershell -command "Expand-Archive -Path '%TEMP%\ffmpeg_win.zip' -DestinationPath '%TEMP%\ffmpeg_win' -Force"
    REM El zip tiene una subcarpeta; buscar ffmpeg.exe recursivamente
    for /r "%TEMP%\ffmpeg_win" %%f in (ffmpeg.exe) do copy "%%f" "bin\ffmpeg.exe" >nul
    del "%TEMP%\ffmpeg_win.zip"
    rmdir /s /q "%TEMP%\ffmpeg_win"
    echo    OK ffmpeg.exe listo.
) else (
    echo [2/4] ffmpeg.exe ya existe, omitiendo descarga.
)

REM ── 3. Limpiar builds anteriores ────────────────────────────────────────
echo [3/4] Limpiando builds anteriores...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

REM ── 4. PyInstaller ───────────────────────────────────────────────────────
echo [4/4] Empaquetando con PyInstaller...
pyinstaller xtuber.spec --noconfirm
if errorlevel 1 (echo ERROR: fallo PyInstaller & exit /b 1)

echo.
if exist "dist\Xtuber.exe" (
    echo ╔══════════════════════════════════════════════╗
    echo ║  OK Build completado                        ║
    echo ║     dist\Xtuber.exe                         ║
    echo ╚══════════════════════════════════════════════╝
) else (
    echo ERROR: no se encontro Xtuber.exe en dist\
    exit /b 1
)
