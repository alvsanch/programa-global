#!/bin/bash

echo "--- Lanzador Robusto de ACE-Step ---"
PROCESS_NAME="acestep.gui"

# Paso 1: Buscar el PID del proceso antiguo
PID=$(pgrep -f "$PROCESS_NAME")

# Paso 2: Si el proceso existe (si el PID no está vacío), intentar terminarlo
if [ ! -z "$PID" ]; then
    echo "[INFO] Se encontró una instancia antigua de '$PROCESS_NAME' con PID: $PID."

    # Intento de cierre normal primero
    echo "[INFO] Intentando terminar el proceso de forma normal..."
    kill "$PID"
    sleep 1

    # Volver a comprobar si el proceso sigue vivo
    if ps -p "$PID" > /dev/null; then
        echo "[ADVERTENCIA] El proceso no se cerró. Forzando el cierre (kill -9)..."
        kill -9 "$PID"
        sleep 1
    fi
    echo "[INFO] Proceso antiguo limpiado."
else
    echo "[INFO] No se encontraron instancias antiguas de '$PROCESS_NAME'. El entorno está limpio."
fi

# Paso 3: Activar el entorno virtual
echo "[INFO] Activando el entorno virtual 'venv_acestep'..."
source /home/alvar/venv_acestep/bin/activate

# Paso 4: Navegar a la carpeta del proyecto
cd /home/alvar/ACE-Step

# Paso 5: Ejecutar la nueva instancia
echo "[INFO] Lanzando nueva instancia de la GUI de ace-step..."
python3 -m acestep.gui
