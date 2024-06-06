CD /D "%~dp0"
WHERE /q python
IF ERRORLEVEL 1 (
    ECHO Python not found. Please install Python 3.11 or later.
    PAUSE
    EXIT
)
WHERE /q virtualenv
IF ERRORLEVEL 1 (
    ECHO Installing virtualenv...
    pip install virtualenv
)
virtualenv venv
.\venv\Scripts\activate && pip install -r requirements.txt && python bdk.py env & pause
