import gradio as gr
import subprocess
import os
import shutil
import json
import pandas as pd
import plotly.express as px
from datetime import datetime
from gradio.themes.base import Base
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import threading
import requests
from PIL import Image
import io
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ===============================================================
# --- TEMA Y CONFIGURACIÓN GLOBAL ---
# ===============================================================
class CustomTheme(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.primary_hue = "blue"; self.text_lg = "1.1rem"; self.text_sm = "1rem"; self.text_md = "1.05rem"
custom_theme = CustomTheme()

WINDOWS_HOST_IP = "192.168.1.143" 
CAMERA_SERVER_URL = f"http://{WINDOWS_HOST_IP}:5000"

ACESTEP_OUTPUT_DIR = "/home/alvar/ACE-Step/outputs"
DEST_DIR_WSL = "/mnt/c/Users/alvar/Desktop/DOCTORADO/PROGRAMAS/musica_generada"; FRAMES_DIR_WSL = "/mnt/c/Users/alvar/Desktop/DOCTORADO/PROGRAMAS/frames"; ANALYZER_SCRIPT_WSL = "/home/alvar/analizar_emocion.py"; BIOMEDIDAS_CSV_DIR = "/home/alvar/biomedidas"; MQTT_BROKER = "localhost"; MQTT_CONTROL_TOPIC = "tesis/control"; MQTT_DATA_TOPIC = "tesis/biomedidas"; ACESTEP_RUN_SCRIPT = "/home/alvar/run_acestep.sh"; CAPTURE_SCRIPT_WIN = "C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\capture_10s.py"; MUSIC_GENERADA_WIN = "C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\musica_generada"; POWERSHELL_PATH = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"

# ===============================================================
# --- LÓGICA PARA EL MODO AUTOMÁTICO (VIGILANCIA DE CARPETA) ---
# ===============================================================
monitoring_thread = None
stop_monitoring_flag = threading.Event()
monitoring_logs = []

def trigger_recording_from_file(file_path):
    try:
        filename = os.path.basename(file_path)
        session_id = os.path.splitext(filename)[0]
        shutil.copy(file_path, DEST_DIR_WSL)
        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Nuevo archivo: {filename}. Copiado."
        monitoring_logs.append(log_msg); print(log_msg)
        params = {'session_id': session_id, 'audio_filename': filename}
        requests.get(f"{CAMERA_SERVER_URL}/record_start", params=params, timeout=10)
        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Orden de grabar enviada para '{session_id}'."
        monitoring_logs.append(log_msg); print(log_msg)
    except Exception as e:
        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error procesando {file_path}: {e}"
        monitoring_logs.append(log_msg); print(log_msg)

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.wav'):
            time.sleep(1); trigger_recording_from_file(event.src_path)

def watchdog_thread_function():
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, ACESTEP_OUTPUT_DIR, recursive=False)
    observer.start()
    print(f"[Watcher] Vigilando la carpeta: {ACESTEP_OUTPUT_DIR}")
    try:
        while not stop_monitoring_flag.is_set(): time.sleep(1)
    finally:
        observer.stop(); observer.join()
        print("[Watcher] Vigilancia detenida.")

def start_monitoring():
    global monitoring_thread
    if monitoring_thread is None or not monitoring_thread.is_alive():
        stop_monitoring_flag.clear(); monitoring_logs.clear()
        monitoring_logs.append("▶️ Iniciando vigilancia de la carpeta de ACE-Step...")
        monitoring_thread = threading.Thread(target=watchdog_thread_function, daemon=True)
        monitoring_thread.start()
    else:
        monitoring_logs.append("⚠️ Vigilancia ya se encontraba activa.")
    return "\n".join(monitoring_logs)
def stop_monitoring():
    if monitoring_thread and monitoring_thread.is_alive():
        stop_monitoring_flag.set()
        monitoring_logs.append("⏹️ Vigilancia detenida.")
    else:
        monitoring_logs.append("⚠️ La vigilancia no estaba activa.")
    return "\n".join(monitoring_logs)
def get_monitoring_logs(): return "\n".join(monitoring_logs)

# ===============================================================
# --- RECEPTOR MQTT Y OTRAS FUNCIONES DE BACKEND ---
# ===============================================================
mqtt_log_queue = []
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"MQTT Log Listener Connected with code {rc}")
    client.subscribe(MQTT_DATA_TOPIC)
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        if len(mqtt_log_queue) > 50: mqtt_log_queue.pop(0)
        mqtt_log_queue.append(f"[{datetime.now().strftime('%H:%M:%S')}] {payload}")
    except Exception as e: mqtt_log_queue.append(f"❌ Error MQTT: {e}")
def mqtt_listener():
    mqtt_client.on_connect = on_connect; mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, 1883, 60); mqtt_client.loop_forever()
mqtt_thread = threading.Thread(target=mqtt_listener, daemon=True)
mqtt_thread.start()
def get_mqtt_log(): return "\n".join(mqtt_log_queue)
def start_camera_remote():
    try:
        requests.get(f"{CAMERA_SERVER_URL}/start_camera", timeout=10)
        return "✅ Cámara iniciada. Pulsa 'Actualizar Foto' para ver la imagen."
    except requests.exceptions.RequestException:
        return f"❌ Error al conectar con el servidor de cámara. ¿Está ejecutándose?"
def stop_camera_remote():
    try:
        requests.get(f"{CAMERA_SERVER_URL}/stop_camera", timeout=10)
        return "✅ Cámara detenida.", None
    except requests.exceptions.RequestException:
        return f"❌ Error al detener la cámara.", None
def update_snapshot():
    try:
        response = requests.get(f"{CAMERA_SERVER_URL}/snapshot", timeout=10)
        if response.status_code == 200 and len(response.content) > 0:
            pil_image = Image.open(io.BytesIO(response.content)); return pil_image
        return None
    except requests.exceptions.RequestException: return None
def record_remote(session_id, audio_file_obj):
    if not session_id: return "❌ Por favor, introduce un ID de sesión."
    audio_filename = None
    if audio_file_obj is not None:
        try:
            audio_dest_path = os.path.join(DEST_DIR_WSL, os.path.basename(audio_file_obj.name))
            shutil.copy(audio_file_obj.name, audio_dest_path)
            audio_filename = os.path.basename(audio_file_obj.name)
            print(f"Audio '{audio_filename}' copiado a la carpeta compartida.")
        except Exception as e: return f"❌ Error al copiar el archivo de audio: {e}"
    try:
        params = {'session_id': session_id, 'audio_filename': audio_filename}
        requests.get(f"{CAMERA_SERVER_URL}/record_start", params=params, timeout=10)
        if audio_filename: return f"✅ Orden de grabar enviada (sincronizada con '{audio_filename}')."
        else: return f"✅ Orden de grabar enviada (10 segundos)."
    except requests.exceptions.RequestException as e: return f"❌ Error al enviar la orden de grabar: {e}"
def create_session(session_id, audio_file_obj):
    if not session_id or not audio_file_obj: return None, "❌ ERROR: El ID de sesión y el archivo de audio son obligatorios.", gr.Button(interactive=False), gr.Button(interactive=False)
    os.makedirs(os.path.join(DEST_DIR_WSL), exist_ok=True); os.makedirs(os.path.join(FRAMES_DIR_WSL, session_id), exist_ok=True)
    audio_path_wsl = os.path.join(DEST_DIR_WSL, os.path.basename(audio_file_obj.name)); shutil.copy(audio_file_obj.name, audio_path_wsl)
    log_message = f"✅ Sesión '{session_id}' creada.\n➡️ Listo para el Paso 2: Iniciar Captura."
    return session_id, log_message, gr.Button(interactive=True), gr.Button(interactive=False)
def start_capture_and_recording(session_id):
    if not session_id: return "❌ ERROR: No hay una sesión activa.", gr.Button(interactive=True)
    try:
        publish.single(MQTT_CONTROL_TOPIC, payload=json.dumps({"command": "start", "session_id": session_id}), hostname=MQTT_BROKER)
        log_message = f"✅ Comando START enviado a ESP32 para '{session_id}'.\n"
    except Exception as e: return f"❌ ERROR MQTT: {e}", gr.Button(interactive=True)
    audio_filename_in_windows = os.path.basename(next((f for f in os.listdir(DEST_DIR_WSL) if session_id in f), f"{session_id}.wav"))
    output_frames_win = os.path.join("C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\frames", session_id)
    audio_path_win = os.path.join(MUSIC_GENERADA_WIN, audio_filename_in_windows); command_win = [POWERSHELL_PATH, "-Command", f"python '{CAPTURE_SCRIPT_WIN}' --output '{output_frames_win}' --audio '{audio_path_win}' --session_id '{session_id}'"]; subprocess.Popen(command_win)
    log_message += "✅ Script de captura lanzado en Windows.\n➡️ Cuando termine, pulsa el Paso 3 para analizar."
    return log_message, gr.Button(interactive=True)
def stop_and_analyze(session_id):
    if not session_id: return "❌ ERROR: No hay una sesión activa."
    try:
        publish.single(MQTT_CONTROL_TOPIC, payload=json.dumps({"command": "stop"}), hostname=MQTT_BROKER)
        log_message = f"✅ Comando STOP enviado a ESP32 para '{session_id}'.\n"
    except Exception as e: return f"❌ ERROR MQTT: {e}"
    frames_to_analyze_wsl = os.path.join(FRAMES_DIR_WSL, session_id)
    try:
        log_message += f"📊 Ejecutando análisis emocional...\n"
        proc = subprocess.run(["python3", ANALYZER_SCRIPT_WSL, "--input", frames_to_analyze_wsl], capture_output=True, text=True, check=True)
        log_message += f"--- SALIDA DEL ANÁLISIS ---\n{proc.stdout}\n{proc.stderr}\n🎉 ¡Flujo de trabajo completado!"
    except (subprocess.CalledProcessError, FileNotFoundError) as e: log_message += f"❌ ERROR al analizar: {e}\nSalida: {e.stderr if hasattr(e, 'stderr') else 'N/A'}"
    return log_message
def start_esp32_mqtt():
    try:
        session_id = f"manual_session_{datetime.now().strftime('%H%M%S')}"
        publish.single(MQTT_CONTROL_TOPIC, payload=json.dumps({"command": "start", "session_id": session_id}), hostname=MQTT_BROKER)
        return f"✅ Comando START manual enviado (sesión: {session_id})."
    except Exception as e: return f"❌ Error: {e}"
def stop_esp32_mqtt():
    try:
        publish.single(MQTT_CONTROL_TOPIC, payload=json.dumps({"command": "stop"}), hostname=MQTT_BROKER)
        return "✅ Comando STOP manual enviado."
    except Exception as e: return f"❌ Error: {e}"
def get_latest_biomedidas(session_id):
    if not session_id: return None, "Introduce un ID de sesión.", pd.DataFrame(), ""
    biomedidas_path = os.path.join(BIOMEDIDAS_CSV_DIR, session_id, 'biomedidas.csv')
    if not os.path.exists(biomedidas_path): return None, f"❌ No existe archivo para '{session_id}'.", pd.DataFrame(), ""
    try:
        df = pd.read_csv(biomedidas_path, sep=';'); df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        fig = px.line(df, x='timestamp', y=['hr', 'temp', 'gsr', 'spo2'], title=f"Bioseñales: {session_id}")
        last_row = df.iloc[-1]
        latest_data = (f"Últimos datos ({last_row['timestamp'].strftime('%H:%M:%S')}):\n - HR: {last_row['hr']} bpm\n - GSR: {last_row['gsr']}")
        return fig, f"✅ Datos de '{session_id}' cargados.", df, latest_data
    except Exception as e: return None, f"❌ Error: {e}", pd.DataFrame(), ""
def run_ace_step():
    wsl_exe_path = "/mnt/c/Windows/System32/wsl.exe"
    command_in_new_terminal = f"{ACESTEP_RUN_SCRIPT}; exec bash"
    command = [wsl_exe_path, "bash", "-c", command_in_new_terminal]
    try:
        subprocess.Popen(command)
        return "✅ Lanzando ace-step en una nueva ventana de terminal..."
    except FileNotFoundError: return f"❌ ERROR: No se encontró wsl.exe"
    except Exception as e: return f"❌ Error inesperado: {e}"
def run_musicgen_placeholder(): return "Futura implementación."

# ===============================================================
# --- DEFINICIÓN DE LA INTERFAZ DE GRADIO ---
# ===============================================================
with gr.Blocks(title="Interfaz de Tesis", theme=custom_theme) as demo:
    session_state = gr.State(None)
    gr.Markdown("# Interfaz de Control y Análisis para Tesis"); gr.Markdown("---")
    with gr.Tabs():
        with gr.Tab("🚀 Flujo de Trabajo Principal"):
            gr.Markdown("### Sigue estos 3 pasos para ejecutar un experimento completo.")
            workflow_log = gr.Textbox(label="Consola de Salida", interactive=False, lines=10)
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### Paso 1: Crear Sesión"); session_id_input = gr.Textbox(label="ID de la Sesión", placeholder="Ej: cancion_triste_01"); audio_input = gr.File(label="Sube el archivo de audio (WAV)"); btn_create = gr.Button("1. Crear Sesión", variant="secondary")
                with gr.Column(scale=1):
                    gr.Markdown("#### Paso 2: Grabar y Capturar"); btn_start = gr.Button("2. Iniciar Captura", variant="primary", interactive=False)
                with gr.Column(scale=1):
                    gr.Markdown("#### Paso 3: Finalizar y Analizar"); btn_finish = gr.Button("3. Detener y Analizar", variant="stop", interactive=False)
        with gr.Tab("📸 Análisis Facial"):
            with gr.Tabs():
                with gr.Tab("🎶 Modo Automático (Vigilando a ACE-Step)"):
                    gr.Markdown("## Captura Automática al Generar Música")
                    gr.Markdown(f"Este modo vigila la carpeta de salida de ACE-Step (`{ACESTEP_OUTPUT_DIR}`).")
                    with gr.Row():
                        btn_start_monitoring = gr.Button("▶️ Iniciar Vigilancia", variant="primary"); btn_stop_monitoring = gr.Button("⏹️ Detener Vigilancia")
                        monitoring_refresh_btn = gr.Button("🔄 Refrescar Log")
                    monitoring_log_output = gr.Textbox(label="Log de Vigilancia", interactive=False, lines=15)
                with gr.Tab("🎤 Modo Manual (Subir Audio)"):
                    gr.Markdown("## Control de Cámara y Grabación Sincronizada Manual")
                    with gr.Row():
                        with gr.Column(scale=2):
                            camera_output = gr.Image(label="Visor de Cámara", type="pil")
                        with gr.Column(scale=1):
                            facial_status = gr.Textbox(label="Estado", interactive=False); btn_start_cam = gr.Button("▶️ Iniciar Cámara"); btn_refresh_cam = gr.Button("🔄 Actualizar Foto"); btn_stop_cam = gr.Button("⏹️ Parar Cámara"); gr.Markdown("---"); facial_session_id = gr.Textbox(label="ID de Sesión para Grabación", placeholder="Ej: prueba_sonrisa_01"); facial_audio_input = gr.File(label="Sube Audio (WAV) (Opcional)", file_types=[".wav"]); btn_record_cam = gr.Button("🔴 Grabar")
        with gr.Tab("❤️ Control y Biomedidas (ESP32)"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Control Manual del Dispositivo"); manual_status = gr.Textbox(label="Estado del control manual", interactive=False)
                    with gr.Row():
                        manual_start_btn = gr.Button("▶️ Arrancar Programa"); manual_stop_btn = gr.Button("⏹️ Parar Programa")
                    gr.Markdown("### Log de Trama MQTT en Tiempo Real"); mqtt_log_box = gr.Textbox(label="Trama MQTT", interactive=False, lines=15, autoscroll=True); refresh_log_btn = gr.Button("🔄 Refrescar Log MQTT")
                with gr.Column(scale=2):
                    gr.Markdown("### Visualización de Datos de Sesiones")
                    with gr.Row():
                        session_dropdown = gr.Dropdown(label="Selecciona una Sesión", choices=sorted(os.listdir(BIOMEDIDAS_CSV_DIR)) if os.path.exists(BIOMEDIDAS_CSV_DIR) else []); refresh_btn = gr.Button("🔄 Refrescar Lista")
                    biomedidas_status = gr.Textbox(label="Estado de la Carga", interactive=False); latest_biomedidas_data = gr.Textbox(label="Últimos Datos Registrados", interactive=False, lines=3); biomedidas_plot = gr.Plot(label="Gráfico de Bioseñales"); biomedidas_table = gr.Dataframe(label="Datos en Tabla", interactive=False)
        with gr.Tab("🧠 Análisis Emocional"):
            gr.Markdown("## Modelo Unificado de Emoción (Imagen + Biomedidas)"); gr.Markdown("Este espacio está reservado para mostrar la salida del modelo unificado que combinará el análisis de imágenes con las bioseñales para una detección de emociones más precisa.")
            with gr.Row():
                placeholder_plot = gr.Plot(label="Resultado Emocional Combinado"); placeholder_text = gr.Textbox(label="Diagnóstico del Modelo", interactive=False)
        with gr.Tab("⚙️ Lanzar Módulos"):
            gr.Markdown("### Ejecución de Módulos Externos")
            with gr.Row():
                with gr.Column():
                    btn_ace = gr.Button("▶️ Ejecutar ace-step"); btn_musicgen = gr.Button("▶️ Ejecutar MusicGen")
                with gr.Column():
                    module_status = gr.Textbox(label="Estado del lanzador", interactive=False)
    # --- Lógica de la Interfaz (Conexiones) ---
    btn_create.click(fn=create_session, inputs=[session_id_input, audio_input], outputs=[session_state, workflow_log, btn_start, btn_finish])
    btn_start.click(fn=start_capture_and_recording, inputs=[session_state], outputs=[workflow_log, btn_finish])
    btn_finish.click(fn=stop_and_analyze, inputs=[session_state], outputs=[workflow_log])
    btn_start_monitoring.click(fn=start_monitoring, outputs=monitoring_log_output)
    btn_stop_monitoring.click(fn=stop_monitoring, outputs=monitoring_log_output)
    monitoring_refresh_btn.click(fn=get_monitoring_logs, inputs=None, outputs=monitoring_log_output)
    btn_start_cam.click(fn=start_camera_remote, inputs=None, outputs=[facial_status]); btn_stop_cam.click(fn=stop_camera_remote, inputs=None, outputs=[facial_status, camera_output]); btn_refresh_cam.click(fn=update_snapshot, inputs=None, outputs=[camera_output]); btn_record_cam.click(fn=record_remote, inputs=[facial_session_id, facial_audio_input], outputs=[facial_status])
    manual_start_btn.click(fn=start_esp32_mqtt, inputs=None, outputs=manual_status); manual_stop_btn.click(fn=stop_esp32_mqtt, inputs=None, outputs=manual_status)
    def update_dropdown(): return gr.Dropdown(choices=sorted(os.listdir(BIOMEDIDAS_CSV_DIR)) if os.path.exists(BIOMEDIDAS_CSV_DIR) else [])
    refresh_btn.click(fn=update_dropdown, outputs=session_dropdown)
    session_dropdown.change(fn=get_latest_biomedidas, inputs=session_dropdown, outputs=[biomedidas_plot, biomedidas_status, biomedidas_table, latest_biomedidas_data])
    btn_ace.click(fn=run_ace_step, inputs=None, outputs=module_status); btn_musicgen.click(fn=run_musicgen_placeholder, inputs=None, outputs=module_status); refresh_log_btn.click(fn=get_mqtt_log, inputs=None, outputs=mqtt_log_box)

if __name__ == "__main__":
    demo.launch(share=False)
