@echo off
setlocal
title SCC Plotter
cd /d "%~dp0"

rem --- Refuse to run from inside a zip (Windows runs it from a temp folder) ---
echo %~dp0 | findstr /i "\\Temp\\" >nul && (
  echo.
  echo  It looks like this was started from inside the zip file.
  echo  Right-click the zip, choose "Extract All...", then run run_app.bat
  echo  from the extracted folder.
  goto :fail
)

rem --- Find Python: the "py" launcher first, then "python" ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
  echo.
  echo  Python was not found.
  echo  Install it from https://www.python.org/downloads/
  echo  and tick "Add python.exe to PATH" in the installer, then run this again.
  goto :fail
)
echo Using: & %PY% --version

rem --- Private environment in .venv so other Python projects are not affected ---
if not exist ".venv\Scripts\python.exe" (
  echo Creating environment ^(first run only^) ...
  %PY% -m venv .venv || goto :fail
)
set "VPY=.venv\Scripts\python.exe"

echo Installing / checking packages ^(first run takes a few minutes^) ...
"%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt || (
  echo.
  echo  Package installation failed. Check your internet connection and the message above.
  goto :fail
)

echo.
echo Starting SCC Plotter. Your browser will open at http://localhost:8501
echo Close this window to stop the app.
"%VPY%" -m streamlit run app.py
if errorlevel 1 goto :fail
goto :eof

:fail
echo.
echo  Something went wrong. Please send a screenshot of this window.
pause
exit /b 1
