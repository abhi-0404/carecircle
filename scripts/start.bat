@echo off
rem Starts CareCircle's two code agents (@ledger and @pillbox). Keep this window open.
rem Needs: Docker running, the Switch server running (Switch Console > Admin > Status),
rem and .env filled in (see README). Double-click, or run from a terminal.
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
echo Starting @ledger and @pillbox. Leave this window open; close it to stop them.
uv run carecircle run
pause
