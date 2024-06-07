cd /D "%~dp0"
.\venv\Scripts\activate && python .\bdk.py --mod DarkestHourDev build --name_filter=*.usx --clean
pause
