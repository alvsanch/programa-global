#!/bin/bash

# --- Script para lanzar la aplicación de tesis completa en una sola ventana ---

echo "============================================="
echo "===     Lanzador de Interfaz de Tesis     ==="
echo "============================================="

# Nos aseguramos de estar en el directorio correcto
cd /home/alvar/

# Activamos el entorno virtual de Python
echo "[INFO] Activando el entorno virtual 'venv_tesis'..."
source venv_tesis/bin/activate

# Función de limpieza: se ejecuta cuando cierras la ventana o pulsas Ctrl+C
cleanup() {
    echo ""
    echo "[INFO] Señal de salida recibida. Limpiando procesos en segundo plano..."
    # 'pkill' es una forma segura de matar el proceso usando parte de su nombre
    pkill -f "python3 mqtt/receptor_controlado.py"
    echo "[INFO] Limpieza completada. Adios."
    exit 0
}

# 'trap' asocia la función de limpieza a las señales de salida (INT, TERM)
trap cleanup INT TERM

# Lanzamos el receptor MQTT en segundo plano usando '&'
echo "[INFO] Lanzando receptor MQTT en segundo plano..."
python3 mqtt/receptor_controlado.py &

# Damos un pequeño respiro para que el receptor se inicie correctamente
sleep 2

# Finalmente, lanzamos la interfaz de Gradio en primer plano
# La terminal se quedará "ocupada" por este proceso
echo "[INFO] Lanzando la interfaz principal de Gradio..."
python3 app_tesis.py

# Cuando cierres la interfaz con Ctrl+C, el 'trap' se activará y limpiará todo
