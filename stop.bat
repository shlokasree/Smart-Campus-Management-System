@echo off
echo Stopping CampusCare services...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5500') do taskkill /f /pid %%a 2>nul

echo All CampusCare servers stopped.
pause
