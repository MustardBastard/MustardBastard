@echo off
rem Double-click to start the SCC Plotter. First run installs the packages.
cd /d "%~dp0"
python -m pip install -r requirements.txt --quiet
python -m streamlit run app.py
pause
