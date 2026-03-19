@echo off
chcp 65001 >nul
title Bili2Text
call conda activate bili2text
cd /d "%~dp0"
python window.py
pause
