@echo off
echo Starting Gmail Manager...
start "" python app.py
timeout /t 3 /nobreak >nul
start http://localhost:5000
