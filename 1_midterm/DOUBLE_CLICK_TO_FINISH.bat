@echo off
setlocal
cd /d "%~dp0"
echo ===============================================
echo CSE558 MIDTERM - FINALIZE AND PACKAGE
echo ===============================================
echo First edit: midterm\member_contributions.csv
echo Do not proceed with REPLACE_ME placeholders.
echo.
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 FINISH_AND_PACKAGE.py
) else (
    python FINISH_AND_PACKAGE.py
)
if errorlevel 1 (
    echo.
    echo FINALIZATION DID NOT PASS. Read 01_START_HERE_TEAM.md and fix errors.
    pause
    exit /b 1
)
echo.
echo OPENING PDF FOR REQUIRED MANUAL INSPECTION...
start "" "%~dp0SUBMIT_TO_CLASSROOM\CSE558_Final_Report.pdf"
pause
