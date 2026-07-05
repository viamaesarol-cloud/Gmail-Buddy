@echo off
echo ========================================
echo  Gmail Manager V1.1 - Setup
echo ========================================
echo.

echo [1/4] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo.
echo [2/4] Installing dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo [3/4] Setting up database...
python -c "from database import init_db, init_undo_table; init_db(); init_undo_table(); print('Database ready!')"

echo.
echo [4/4] Setup complete!
echo.
echo To start Gmail Manager, double-click start.bat
echo.
pause
