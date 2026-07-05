@echo off
echo ========================================
echo  Gmail Manager V1.1 - Build Installer
echo ========================================
echo.

echo [1/5] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller!
    pause
    exit /b 1
)

echo.
echo [2/5] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist GmailManager.spec del GmailManager.spec

echo.
echo [3/5] Building executable...
pyinstaller --onefile ^
            --noconfirm ^
            --clean ^
            --name "GmailManager" ^
            --add-data "templates;templates" ^
            --add-data "credentials.json;." ^
            --icon "icon.ico" ^
            app.py

if errorlevel 1 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo [4/5] Creating Release folder...
if not exist Release mkdir Release
copy dist\GmailManager.exe Release\
copy setup.bat Release\
copy start.bat Release\
copy requirements.txt Release\
copy README.md Release\
if exist icon.ico copy icon.ico Release\

echo.
echo [5/5] Build complete!
echo Your release is in the "Release" folder.
echo.
pause
