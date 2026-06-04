@echo off
setlocal
cd /d "%~dp0"

where pyw >nul 2>nul
if %errorlevel%==0 (
    pyw -3.12 -c "import sys" >nul 2>nul && (
        start "" pyw -3.12 main.pyw
        goto :end
    )
    pyw -3.11 -c "import sys" >nul 2>nul && (
        start "" pyw -3.11 main.pyw
        goto :end
    )
    start "" pyw -3 main.pyw
    goto :end
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw main.pyw
    goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 -c "import sys" >nul 2>nul && (
        py -3.12 main.py
        goto :end
    )
    py -3.11 -c "import sys" >nul 2>nul && (
        py -3.11 main.py
        goto :end
    )
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
