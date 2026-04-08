@echo off
title Milky Way Market Query
cd /d "%~dp0"
git pull --quiet 2>nul
python query.py
pause
