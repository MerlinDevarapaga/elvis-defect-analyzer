@echo off
REM Refresh Bug Zero dashboard HTML and publish to GitHub Pages (origin + harman)
cd /d "C:\My Workspace\Projects\MSIL\Github Repo\elvis-defect-analyzer"
set BUGZERO_EMAIL_BACKEND=none
set BUGZERO_REQUIRE_APPROVAL=false

echo [1/3] Fetching latest data and generating HTML...
.\.venv\Scripts\python.exe scripts\bug_zero_dashboard_email.py
if errorlevel 1 (
    echo ERROR: Dashboard generation failed. Aborting.
    pause
    exit /b 1
)

echo [2/3] Publishing to GitHub Pages...
git stash
git checkout gh-pages
for /f "tokens=*" %%f in ('dir /b /od "C:\My Workspace\Projects\MSIL\BugZero_Reports\YTB_BugZero_Dashboard_*.html"') do set LATEST_HTML=%%f
copy /y "C:\My Workspace\Projects\MSIL\BugZero_Reports\%LATEST_HTML%" "index.html"
git add index.html
git commit -m "pages: auto-refresh %date% %time:~0,5%"
git push origin gh-pages
git push harman gh-pages:gh-pages --force
git checkout main
git stash pop

echo [3/3] Done! Dashboard live at https://studious-barnacle-p3mrz5j.pages.github.io/
