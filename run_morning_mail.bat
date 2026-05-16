@echo off
REM DA2.8 Bug Zero Morning Mail — Auto-runner
REM Fetches data, builds dashboard, sends email via Outlook, publishes to GitHub Pages
cd /d "C:\My Workspace\Projects\MSIL\Github Repo\elvis-defect-analyzer"
echo [%date% %time%] Starting morning mail... >> "%USERPROFILE%\BugZero_morning_log.txt"
python scripts\bug_zero_dashboard_email.py >> "%USERPROFILE%\BugZero_morning_log.txt" 2>&1
echo [%date% %time%] Done. >> "%USERPROFILE%\BugZero_morning_log.txt"
