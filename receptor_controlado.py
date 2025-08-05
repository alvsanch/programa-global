# nombre_sugerido: receptor_controlado.py

import paho.mqtt.client as mqtt
import os
import json

# --- Configuración ---
# Asegúrate de que estas variables coincidan con tu entorno
MQTT_BROKER = "localhost"  # O "192.168.1.143" si el broker corre en el host
MQTT_PORT = 1883
DATA_TOPIC = "tesis/biomedidas"   # Tópico de donde vienen los datos del ESP32
CONTROL_TOPIC = "tesis/control" # Tópico para recibir comandos (START/STOP)
OUTPUT_DIR = "/home/alvar/datos_tesis/biomedidas" # Directorio base para guardar los CSV

# --- Variables de Estado Globales ---
is_recording = False
output_file_handle = None

# --- Funciones de Callback de MQTT ---

def on_connect(client, userdata, flags, rc):
    """
    Esta función se llama cuando el cliente se conecta exitosamente al broker.
    """
    if rc == 0:
        print("✅ Receptor conectado exitosamente al Broker MQTT.")
        # Se suscribe a ambos tópicos: el de datos y el de control
        client.subscribe([(DATA_TOPIC, 0), (CONTROL_TOPIC, 0)])
        print(f"   -> Escuchando datos en: '{DATA_TOPIC}'")
        print(f"   -> Escuchando comandos en: '{CONTROL_TOPIC}'")
    else:
        print(f"❌ Fallo al conectar al broker, código de error: {rc}")

def on_message(client, userdata, msg):
    """
    Esta función se llama cada vez que llega un mensaje a un tópico suscrito.
    """
    global is_recording, output_file_handle
    
    try:
        payload = msg.payload.decode("utf-8")
        
        # --- Lógica de Control: Procesa los comandos START/STOP ---
        if msg.topic == CONTROL_TOPIC:
            command_data = json.loads(payload)
            command = command_data.get("command")
            session_id = command_data.get("session_id")

            if command == "start" and session_id:
                print(f"\n▶️  COMANDO START RECIBIDO (Sesión: {session_id})")
                is_recording = True
                
                # Crear el directorio de salida si no existe
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                output_filename = os.path.join(OUTPUT_DIR, f"biomedidas_{session_id}.csv")
                
                # Abrir el archivo para esta sesión y escribir la cabecera
                output_file_handle = open(output_filename, "w", newline="")
                output_file_handle.write("timestamp,temp,hr,spo2,gsr\n")
                
                print(f"   -> Grabando datos en: {output_filename}")

            elif command == "stop":
                print(f"\n⏹️  COMANDO STOP RECIBIDO")
                is_recording = False
                if output_file_handle:
                    output_file_handle.close()
                    output_file_handle = None
                print("   -> Grabación de biométricas finalizada.")

        # --- Lógica de Grabación: Guarda los datos biométricos si está activado ---
        elif msg.topic == DATA_TOPIC and is_recording:
            data = json.loads(payload)
            # Validar que el JSON contiene todos los campos esperados
            if all(k in data for k in ["timestamp", "temp", "hr", "spo2", "gsr"]):
                # Formatear la línea para el archivo CSV
                csv_line = f"{data['timestamp']},{data['temp']},{data['hr']},{data['spo2']},{data['gsr']}\n"
                
                # Escribir en el archivo solo si está abierto
                if output_file_handle and not output_file_handle.closed:
                    output_file_handle.write(csv_line)
                    # print(".", end="", flush=True) # Descomentar para un feedback visual de que se reciben datos
            else:
                print(f"\nADVERTENCIA: JSON recibido no tiene el formato esperado. Payload: {payload}")
                
    except json.JSONDecodeError:
        print(f"\nERROR: No se pudo decodificar el JSON. Payload: {payload}")
    except Exception as e:
        print(f"\nERROR inesperado en on_message: {e}")


# --- Programa Principal ---

if __name__ == "__main__":
    print("Iniciando receptor de biométricas controlado...")
    
    # Crear y configurar el cliente MQTT
    client = mqtt.Client("ReceptorControladoTesis")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        # Intentar conectar al broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # loop_forever() es un bucle bloqueante que mantiene la conexión
        # y procesa los mensajes entrantes automáticamente.
        client.loop_forever()
        
    except ConnectionRefusedError:
        print(f"❌ ERROR: Conexión rechazada. ¿Está el broker MQTT corriendo en {MQTT_BROKER}?")
    except Exception as e:
        print(f"❌ ERROR al iniciar el cliente MQTT: {e}")