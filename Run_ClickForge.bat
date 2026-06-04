@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 main.py >nul 2>nul && goto :end
    py -3.11 main.py >nul 2>nul && goto :end
    py -3 main.py
    goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python main.py
    goto :end
)

echo Python 3.11+ was not found on this system.
echo Install Python and run: pip install -r requirements.txt
pause

:end
endlocal
