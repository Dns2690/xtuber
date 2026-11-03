@echo off
REM ============================================================
REM  build_windows.bat — Build de Xtuber para Windows
REM  Genera: dist\Xtuber.exe
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ==============================================
echo        Xtuber - Build para Windows
echo ==============================================
echo.

REM -- 1. Dependencias Python ------------------------------------------------
echo [1/5] Instalando dependencias Python...
python -m pip install --quiet --upgrade pip
REM -U: siempre empaquetar el yt-dlp mas reciente
python -m pip install --quiet --upgrade -r requirements.txt
if errorlevel 1 (echo ERROR: fallo pip install & exit /b 1)

if not exist "bin" mkdir bin

REM -- 2. ffmpeg + ffprobe (build estatica de gyan.dev) ----------------------
if not exist "bin\ffmpeg.exe" (
    echo [2/5] Descargando ffmpeg y ffprobe...
    curl -fL "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -o "%TEMP%\ffmpeg_win.zip" --progress-bar
    if errorlevel 1 (echo ERROR: fallo descarga ffmpeg & exit /b 1)
    powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\ffmpeg_win.zip' -DestinationPath '%TEMP%\ffmpeg_win' -Force"
    for /r "%TEMP%\ffmpeg_win" %%f in (ffmpeg.exe) do if exist "%%f" copy /y "%%f" "bin\ffmpeg.exe" >nul
    for /r "%TEMP%\ffmpeg_win" %%f in (ffprobe.exe) do if exist "%%f" copy /y "%%f" "bin\ffprobe.exe" >nul
    del "%TEMP%\ffmpeg_win.zip"
    rmdir /s /q "%TEMP%\ffmpeg_win"
) else (
    echo [2/5] ffmpeg ya existe, omitiendo descarga.
)
if not exist "bin\ffprobe.exe" (echo ERROR: falta bin\ffprobe.exe & exit /b 1)

REM -- 3. deno (runtime JavaScript que yt-dlp necesita para YouTube) ---------
if not exist "bin\deno.exe" (
    echo [3/5] Descargando deno...
    curl -fL "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip" -o "%TEMP%\deno_win.zip" --progress-bar
    if errorlevel 1 (echo ERROR: fallo descarga deno & exit /b 1)
    powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\deno_win.zip' -DestinationPath 'bin' -Force"
    del "%TEMP%\deno_win.zip"
) else (
    echo [3/5] deno ya existe, omitiendo descarga.
)

REM -- 4. Limpiar builds anteriores ------------------------------------------
echo [4/5] Limpiando builds anteriores...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

REM -- 5. PyInstaller --------------------------------------------------------
echo [5/5] Empaquetando con PyInstaller...
python -m PyInstaller xtuber.spec --noconfirm
if errorlevel 1 (echo ERROR: fallo PyInstaller & exit /b 1)

echo.
if exist "dist\Xtuber.exe" (
    echo ==============================================
    echo   OK Build completado: dist\Xtuber.exe
    echo ==============================================
) else (
    echo ERROR: no se encontro Xtuber.exe en dist\
    exit /b 1
)
