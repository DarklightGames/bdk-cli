cd /D "%~dp0"
virtualenv venv
.\venv\Scripts\activate && pip install -r requirements.txt && python bdk.py env & pause
