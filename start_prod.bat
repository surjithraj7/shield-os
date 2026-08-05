@echo off
rem Production launcher for the Tunneling Management Platform
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_prod.ps1" %*
