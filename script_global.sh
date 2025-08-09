#!/bin/bash

# =================================================================
# --- CONFIGURACIÓN ---
# =================================================================
WATCH_DIR="/home/alvar/ACE-Step/outputs"
DEST_DIR="/mnt/c/Users/alvar/Desktop/DOCTORADO/PROGRAMAS/musica_generada"
FRAMES_DIR="/mnt/c/Users/alvar/Desktop/DOCTORADO/PROGRAMAS/frames"
ANALYZER_SCRIPT="/home/alvar/analizar_emocion.py"
CAPTURE_SCRIPT="C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\capture_10s.py"
RECEPTOR_SCRIPT="/home/alvar/mqtt/receptor_controlado.py"

# --- Configuración MQTT ---
MQTT_BROKER="localhost"
MQTT_CONTROL_TOPIC="tesis/control"

# Ruta compartida para el archivo de señal
SHARED_DATA_DIR="/mnt/c/Users/alvar/Desktop/DOCTORADO/PROGRAMAS/shared_data"

# =================================================================
# --- ARRANQUE Y LIMPIEZA AUTOMÁTICA ---
# =================================================================

cleanup() {
    echo ""
    echo "--- Finalizando el script. Realizando limpieza... ---"
    if ps -p $RECEPTOR_PID > /dev/null; then
       echo "Deteniendo el receptor de biométricas (PID: $RECEPTOR_PID)..."
       kill $RECEPTOR_PID
    fi
    echo "Limpieza completada. ¡Adiós!"
}

trap cleanup EXIT INT

echo "--- Iniciando el receptor de biométricas en segundo plano... ---"
python3 "$RECEPTOR_SCRIPT" &

RECEPTOR_PID=$!
echo "Receptor iniciado con PID: $RECEPTOR_PID."

sleep 2

# =================================================================
# --- FUNCIÓN DE PROCESAMIENTO ---
# =================================================================
process_song() {
    local NEW_FILE="$1"
    local FILENAME=$(basename "$NEW_FILE")
    local BASE_NAME="${FILENAME%.*}"

    echo "----------------------------------------------------"
    echo "Procesando Sesión: $BASE_NAME"
    echo "----------------------------------------------------"

    echo "1. Copiando '$FILENAME' a '$DEST_DIR/'..."
    cp "$NEW_FILE" "$DEST_DIR/"

    echo "2. Lanzando captura de frames y audio en Windows..."
    
    /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
      "python \"$CAPTURE_SCRIPT\" --output \"C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\frames\\$BASE_NAME\" --audio \"C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\musica_generada\\$FILENAME\" --camera_index 1 --delay 3 --session_id \"$BASE_NAME\""

    # Esperamos el archivo de señal de Windows en la ruta compartida
    local SIGNAL_FILE_PATH="$SHARED_DATA_DIR/$BASE_NAME/start_signal.txt"
    echo "3. Esperando señal de inicio de grabación desde Windows..."
    while [ ! -f "$SIGNAL_FILE_PATH" ]; do
        sleep 0.2
    done
    rm "$SIGNAL_FILE_PATH"

    echo "4. Señal recibida. Enviando comando START al receptor..."
    START_PAYLOAD="{\"command\": \"start\", \"session_id\": \"$BASE_NAME\"}"
    mosquitto_pub -h "$MQTT_BROKER" -t "$MQTT_CONTROL_TOPIC" -m "$START_PAYLOAD"

    echo "5. Esperando carpeta de frames..."
    while [ ! -d "$FRAMES_DIR/$BASE_NAME" ]; do sleep 1; done
    LATEST_SUBDIR=$(find "$FRAMES_DIR/$BASE_NAME" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)
    if [ -z "$LATEST_SUBDIR" ]; then echo "ERROR: No se encontró subcarpeta."; return 1; fi

    echo "6. Enviando comando STOP al receptor..."
    STOP_PAYLOAD="{\"command\": \"stop\"}"
    mosquitto_pub -h "$MQTT_BROKER" -t "$MQTT_CONTROL_TOPIC" -m "$STOP_PAYLOAD"

    echo "7. Ejecutando análisis emocional sobre: $LATEST_SUBDIR"
    python3 "$ANALYZER_SCRIPT" --input "$LATEST_SUBDIR"

    echo "Proceso finalizado para la sesión: $BASE_NAME"
    echo "----------------------------------------------------"
}

# =================================================================
# --- MENÚ DE OPCIONES Y BUCLE PRINCIPAL ---
# =================================================================
while true; do
    echo ""
    echo "--- Sistema de Captura de Estímulos Musicales ---"
    echo "Seleccione una opción:"
    echo "  1) Procesar una canción existente (Manual)"
    echo "  2) Monitorear carpeta para nuevas canciones (Automático)"
    echo "  q) Salir del programa"
    echo ""
    read -p "Tu elección: " choice

    case "$choice" in
        1)
            read -p "Ingresa el nombre del archivo de la canción (ej: cancion.wav): " manual_file
            FULL_PATH_FILE="$WATCH_DIR/$manual_file"
            if [ -f "$FULL_PATH_FILE" ]; then
                process_song "$FULL_PATH_FILE"
            else
                echo "ERROR: El archivo '$manual_file' no existe en '$WATCH_DIR'."
            fi
            ;;
        2)
            echo "--- MODO MONITOR ACTIVADO ---"
            echo "Vigilando la carpeta: $WATCH_DIR"
            
            existing_files=()
            for file in "$WATCH_DIR"/*; do
                if [ -f "$file" ]; then
                    existing_files+=("$(basename "$file")")
                fi
            done
            echo "Ignorando ${#existing_files[@]} archivos existentes. Presiona Ctrl+C para detener."
            
            if ! command -v inotifywait &> /dev/null; then
                echo "ERROR: inotifywait no está instalado. Ejecuta 'sudo apt-get install inotify-tools'."
                exit 1
            fi

            while inotifywait -e create -q "$WATCH_DIR"; do
                for new_file in "$WATCH_DIR"/*; do
                    if [ -f "$new_file" ]; then
                        filename=$(basename "$new_file")
                        is_new=true
                        for existing in "${existing_files[@]}"; do
                            if [[ "$filename" == "$existing" ]]; then
                                is_new=false
                                break
                            fi
                        done
                        
                        if [ "$is_new" = true ]; then
                            echo "----------------------------------------------------"
                            echo "🎵 Procesando Nueva Canción: $filename"
                            process_song "$new_file"
                            echo "----------------------------------------------------"
                            existing_files+=("$filename")
                        fi
                    fi
                done
                echo "--- Vigilando de nuevo... ---"
            done
            ;;
        q)
            echo "Saliendo del programa."
            exit 0
            ;;
        *)
            echo "Opción no válida. Por favor, elige 1, 2 o q."
            ;;
    esac
done
