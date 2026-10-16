@echo off
echo ========================================================
echo Starting CampusCare Full-Stack System
echo ========================================================
echo.

echo Starting FastAPI Backend (Port 8000)...
start "CampusCare Backend" python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000

echo Starting Flask Analytics Service (Port 5001)...
start "CampusCare Analytics" python analytics_service/app.py

echo Starting Frontend Web Server (Port 5500)...
start "CampusCare Frontend" python -m http.server 5500 --directory frontend

timeout /t 2 >nul

echo.
echo Opening CampusCare in your browser...
start http://127.0.0.1:5500

echo.
echo ========================================================
echo CampusCare is running!
echo - Frontend:          http://127.0.0.1:5500
echo - Backend API:       http://127.0.0.1:8000
echo - Swagger Docs:      http://127.0.0.1:8000/docs
echo - Analytics API:     http://127.0.0.1:5001
echo ========================================================
pause
