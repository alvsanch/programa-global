#!/bin/bash

# =================================================================
# --- CONFIGURACIÓN (sin cambios) ---
# =================================================================
WATCH_DIR="/home/alvar/ACE-Step/outputs"
DEST_DIR="/mnt/c/Users/alvar/Desktop/DOCTORADO/PROGRAMAS/musica_generada"
FRAMES_DIR="/mnt/c/Users/alvar/Desktop/DOCTORADO/PROGRAMAS/frames"
ANALYZER_SCRIPT="/home/alvar/analizar_emocion.py"
CAPTURE_SCRIPT="C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\capture_10s.py"
RECEPTOR_SCRIPT="/home/alvar/ruta/a/receptor_controlado.py" # <-- ¡Añade la ruta a tu script de python!

# --- Configuración MQTT ---
MQTT_BROKER="localhost"
MQTT_CONTROL_TOPIC="tesis/control"

# =================================================================
# --- ARRANQUE Y LIMPIEZA AUTOMÁTICA ---
# =================================================================

### NUEVO: Función de limpieza que se ejecutará al salir ###
cleanup() {
    echo "" # Nueva línea para claridad
    echo "--- Finalizando el script. Realizando limpieza... ---"
    # Matamos el proceso del receptor de MQTT que iniciamos
    if ps -p $RECEPTOR_PID > /dev/null; then
       echo "Deteniendo el receptor de biométricas (PID: $RECEPTOR_PID)..."
       kill $RECEPTOR_PID
    fi
    echo "Limpieza completada. ¡Adiós!"
}

### NUEVO: 'trap' para llamar a la función cleanup al salir ###
# Se ejecutará al terminar el script (EXIT) o al pulsar Ctrl+C (INT)
trap cleanup EXIT INT

### NUEVO: Lanzar el receptor de MQTT en segundo plano ###
echo "--- Iniciando el receptor de biométricas en segundo plano... ---"
python3 "$RECEPTOR_SCRIPT" &

# Guardamos el Process ID (PID) del último proceso lanzado en segundo plano
RECEPTOR_PID=$!
echo "Receptor iniciado con PID: $RECEPTOR_PID."

# Damos un segundo al script de Python para que se inicie y conecte al broker
sleep 2

# =================================================================
# --- FUNCIÓN DE PROCESAMIENTO (sin cambios) ---
# =================================================================
process_song() {
    local NEW_FILE="$1"
    local FILENAME=$(basename "$NEW_FILE")
    local BASE_NAME="${FILENAME%.*}"

    echo "----------------------------------------------------"
    echo "Procesando Sesión: $BASE_NAME"
    echo "----------------------------------------------------"

    # 1. Copiar archivo
    echo "1. Copiando '$FILENAME' a '$DEST_DIR/'..."
    cp "$NEW_FILE" "$DEST_DIR/"

    # 2. Enviar START
    echo "2. Enviando comando START al receptor..."
    START_PAYLOAD="{\"command\": \"start\", \"session_id\": \"$BASE_NAME\"}"
    mosquitto_pub -h "$MQTT_BROKER" -t "$MQTT_CONTROL_TOPIC" -m "$START_PAYLOAD"

    # 3. Lanzar captura
    echo "3. Lanzando captura de frames y audio en Windows..."
    /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
      "python \"$CAPTURE_SCRIPT\" --output \"C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\frames\\$BASE_NAME\" --audio \"C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\musica_generada\\$FILENAME\" --camera_index 1"

    # 4. Enviar STOP
    echo "4. Enviando comando STOP al receptor..."
    STOP_PAYLOAD="{\"command\": \"stop\"}"
    mosquitto_pub -h "$MQTT_BROKER" -t "$MQTT_CONTROL_TOPIC" -m "$STOP_PAYLOAD"

    # 5. Esperar carpeta
    echo "5. Esperando carpeta de frames..."
    while [ ! -d "$FRAMES_DIR/$BASE_NAME" ]; do sleep 1; done
    LATEST_SUBDIR=$(find "$FRAMES_DIR/$BASE_NAME" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)
    if [ -z "$LATEST_SUBDIR" ]; then echo "ERROR: No se encontró subcarpeta."; return 1; fi

    # 6. Ejecutar análisis
    echo "6. Ejecutando análisis emocional sobre: $LATEST_SUBDIR"
    python3 "$ANALYZER_SCRIPT" --input "$LATEST_SUBDIR"

    echo "Proceso finalizado para la sesión: $BASE_NAME"
    echo "----------------------------------------------------"
}

# =================================================================
# --- MENÚ DE OPCIONES (sin cambios) ---
# =================================================================
echo ""
echo "--- Sistema de Captura y Análisis Emocional v3.0 (Todo en Uno) ---"
echo "Seleccione una opción:"
# ... (el resto de tu script del menú va aquí sin cambios) ...