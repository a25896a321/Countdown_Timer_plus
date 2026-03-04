@echo off
chcp 65001 > nul
echo ================================================
echo   Countdown Timer Plus - Build Script (onefile)
echo ================================================
echo.

cd /d "%~dp0"

REM ── 清除舊版本 ──────────────────────────────────────────────────
echo [1/5] Cleaning old build...
if exist "dist\Countdown_Timer_plus_v1.3.0" rmdir /s /q "dist\Countdown_Timer_plus_v1.3.0"
if exist "build"                             rmdir /s /q "build"
if exist "Countdown_Timer_plus_v1.3.0.spec" del /q "Countdown_Timer_plus_v1.3.0.spec"

REM ── PyInstaller 打包（單一 exe）──────────────────────────────────
echo [2/5] Running PyInstaller (--onefile)...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name Countdown_Timer_plus_v1.3.0 ^
    --distpath "dist\Countdown_Timer_plus_v1.3.0" ^
    --icon "ico_timer.ico" ^
    --add-data "ico_timer.ico;." ^
    --hidden-import PIL._tkinter_finder ^
    --noconfirm ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed. Please check the output above.
    pause
    exit /b 1
)

REM ── 複製資源資料夾（放在 exe 旁邊，不內嵌）─────────────────────
echo.
echo [3/5] Copying sound_type folder...
if exist "sound_type" (
    xcopy /E /I /Y "sound_type" "dist\Countdown_Timer_plus_v1.3.0\sound_type"
    echo        Done.
) else (
    echo        [WARN] sound_type not found, skipping.
)

echo [4/5] Copying png_type folder...
if exist "png_type" (
    xcopy /E /I /Y "png_type" "dist\Countdown_Timer_plus_v1.3.0\png_type"
    echo        Done.
) else (
    echo        [WARN] png_type not found, skipping.
)

REM ── 顯示結果 ────────────────────────────────────────────────────
echo.
echo [5/5] Verifying output...
echo.
echo ================================================
echo   Build complete!
echo   Output: dist\Countdown_Timer_plus_v1.3.0\
echo ================================================
echo.
dir "dist\Countdown_Timer_plus_v1.3.0" /b /a-d 2>nul
echo.
pause
