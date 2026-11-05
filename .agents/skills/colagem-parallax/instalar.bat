@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo.
  echo Python nao encontrado. Instale em https://www.python.org/downloads/
  echo e marque "Add python.exe to PATH" durante a instalacao.
  echo.
  pause
  exit /b 1
)
%PY% "%~dp0video-colagem-parallax\scripts\preparar.py" %*
echo.
pause
