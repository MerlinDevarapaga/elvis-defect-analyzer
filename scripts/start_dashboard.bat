@echo off
:: Auto-start Bug Zero Live Dashboard
set PYTHONPATH=C:\pylibs
cd /d "c:\My Workspace\Projects\MSIL\Github Repo\elvis-defect-analyzer"
python -m streamlit run scripts/bug_zero_live_dashboard.py --server.address 0.0.0.0
