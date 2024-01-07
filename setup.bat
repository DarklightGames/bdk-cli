cd /D "%~dp0"
.\venv\Scripts\activate && pip install -r requirements.txt && python bdk.py env & pause
