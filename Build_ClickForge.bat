@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 -c "import sys" >nul 2>nul && (
        py -3.12 build.py
        goto :end
    )
    py -3.11 -c "import sys" >nul 2>nul && (
        py -3.11 build.py
        goto :end
    )
    py -3 build.py
    goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python build.py
    goto :end
)

echo Python 3.11+ was not found on this system.
echo Install Python and run: pip install -r requirements.txt
pause

:end
endlocal
