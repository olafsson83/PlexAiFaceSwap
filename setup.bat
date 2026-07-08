@echo off
echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Something went wrong installing dependencies. Make sure Python is installed and on PATH.
    pause
    exit /b 1
)

python setup.py
pause
