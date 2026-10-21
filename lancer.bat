@echo off
title Odoo 19 - Prets au personnel - ne pas fermer
set PYTHONUTF8=1
set ODOO=C:\Users\CC USER\Downloads\odoo-19.0\odoo-19.0
echo Demarrage d'Odoo 19 (Prets) sur http://localhost:8078 ...
"%ODOO%\.venv\Scripts\python.exe" "%ODOO%\run_demo19.py" -c "%~dp0odoo.conf"
echo.
echo Le serveur s'est arrete. Appuyez sur une touche pour fermer.
pause >nul
