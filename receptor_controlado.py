import paho.mqtt.client as mqtt
import json
import os
import pandas as pd
from datetime import datetime
import csv

# ===============================================================
# --- CONFIGURACIÓN ---
# ===============================================================
BROKER_ADDRESS = "localhost"
TOPIC = "tesis/biomedidas"
CONTROL_TOPIC = "tesis/control"
# Directorio base para guardar los datos.
DATA_DIR_BASE = "/home/alvar/biomedidas"

# ===============================================================
# --- VARIABLES GLOBALES ---
# ===============================================================
is_recording = False
session_id = ""
output_file_path = ""
csv_writer = None
output_file = None
# ===============================================================
# --- FUNCIONES AUXILIARES ---
# ===============================================================
def on_connect(client, userdata, flags, rc):
    """Callback que se ejecuta cuando el cliente se conecta."""
    if rc == 0:
        print("✅ Conectado al bróker MQTT.")
        client.subscribe(TOPIC)
        client.subscribe(CONTROL_TOPIC)
        print(f"👂 Suscrito a los tópicos: '{TOPIC}' y '{CONTROL_TOPIC}'")
    else:
        print(f"❌ Fallo en la conexión, código de retorno: {rc}")

def on_message(client, userdata, msg):
    """Callback que se ejecuta cuando se recibe un mensaje."""
    global is_recording, session_id, output_file_path, csv_writer, output_file
    
    if msg.topic == CONTROL_TOPIC:
        try:
            command = json.loads(msg.payload.decode())
            if command.get("command") == "start":
                # Si ya estamos grabando, lo ignoramos.
                if is_recording:
                    print("⚠️  Comando START ignorado. Ya hay una grabación en curso.")
                    return
                
                session_id = command.get("session_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
                
                # Prepara el directorio y el archivo de salida
                data_dir_path = os.path.join(DATA_DIR_BASE, session_id)
                if not os.path.exists(data_dir_path):
                    os.makedirs(data_dir_path)
                    print(f"📂 Creado directorio de salida: {data_dir_path}")

                output_file_path = os.path.join(data_dir_path, "biomedidas.csv")

                # Abre el archivo en modo 'append' para no sobreescribir y añade la cabecera si es nuevo
                output_file = open(output_file_path, 'a', newline='')
                csv_writer = csv.DictWriter(output_file, fieldnames=['timestamp', 'gsr', 'temp', 'hr', 'spo2'], delimiter=';')
                
                # Solo escribe la cabecera si el archivo no existía previamente
                if output_file.tell() == 0:
                    csv_writer.writeheader()

                is_recording = True
                print(f"▶️  Comando START recibido. Iniciando grabación de la sesión '{session_id}'.")
                
            elif command.get("command") == "stop":
                if not is_recording:
                    print("⚠️  Comando STOP ignorado. No hay ninguna grabación en curso.")
                    return

                is_recording = False
                
                # Cierra el archivo de grabación
                if output_file:
                    output_file.close()
                    output_file = None
                    csv_writer = None
                    print(f"⏹️  Comando STOP recibido. Grabación detenida y datos guardados en '{output_file_path}'.")
                
        except json.JSONDecodeError:
            print(f"⚠️ Error al decodificar JSON de control: {msg.payload}")
    
    elif msg.topic == TOPIC and is_recording:
        try:
            biomedida = json.loads(msg.payload.decode())
            
            # Escribe la muestra directamente al archivo CSV
            if csv_writer:
                csv_writer.writerow(biomedida)
                print(f"➡️ Recibido y guardado dato para la sesión '{session_id}': {biomedida}")
        except json.JSONDecodeError:
            print(f"⚠️ Error al decodificar JSON de datos: {msg.payload}")

# ===============================================================
# --- FUNCIÓN PRINCIPAL ---
# ===============================================================
def main():
    """Función principal del script."""
    print("\n--- Receptor MQTT de Bioseñales ---")
    
    client = mqtt.Client(client_id=f"receptor_biomedidas_{os.getpid()}")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_ADDRESS, 1883, 60)
        client.loop_forever()
    except Exception as e:
        print(f"❌ No se pudo conectar al bróker MQTT: {e}")
    finally:
        if output_file:
            output_file.close()
        client.disconnect()
        print("🔌 Conexión MQTT cerrada.")

if __name__ == "__main__":
    main()
