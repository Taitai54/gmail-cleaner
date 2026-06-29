@echo off
title Gmail Label Manager
cd /d "C:\Users\mattieform\GitHub\gmail-cleaner"
echo.
echo  Starting Gmail Label Manager...
echo  Your browser will open automatically.
echo.
python -m streamlit run label_manager_ui.py --server.port 8504 --browser.gatherUsageStats false
