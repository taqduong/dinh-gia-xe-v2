@echo off
REM Chạy ứng dụng trên Windows: tự tạo .venv và cài thư viện ở lần đầu.
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Dang tao moi truong ao .venv ...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" -m streamlit run src\app.py
pause
