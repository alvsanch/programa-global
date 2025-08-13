@echo off
title Lanzador Unificado de Tesis

echo [INFO] Iniciando el flujo de trabajo completo...
echo.

REM --- PASO 1: Iniciar el servidor de camara en Windows ---
echo [INFO] Lanzando el servidor de camara (camera_server.py) en una nueva ventana...
REM Modifica la siguiente ruta para que apunte a la ubicacion REAL de tu script.
set CAMERA_SCRIPT_PATH=C:\Users\alvar\Desktop\DOCTORADO\PROGRAMAS\camera_server.py

start "Servidor de Camara (Windows)" cmd /k python "%CAMERA_SCRIPT_PATH%"

REM --- PASO 2: Esperar a que el servidor se inicie ---
echo [INFO] Esperando 3 segundos para que el servidor de camara se estabilice...
timeout /t 3 /nobreak > nul

REM --- PASO 3: Iniciar el entorno de WSL (MQTT y Gradio) ---
echo [INFO] Lanzando el entorno principal de WSL...
echo.
wsl.exe bash -c "/home/alvar/start_all.sh; exec bash"