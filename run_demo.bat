@echo off
start cmd /k "python server\server.py"
timeout /t 1 >nul
start cmd /k "python client\client.py"
start cmd /k "python client\client.py"
