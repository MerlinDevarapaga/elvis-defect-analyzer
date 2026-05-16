@echo off
cd /d "C:\My Workspace\Projects\MSIL\Github Repo\elvis-defect-analyzer"
python scripts\deploy_sharepoint.py >> "%USERPROFILE%\OneDrive - HARMAN\BugZero_Dashboard\update_log.txt" 2>&1
python scripts\publish_dashboard.py >> "%USERPROFILE%\OneDrive - HARMAN\BugZero_Dashboard\update_log.txt" 2>&1
