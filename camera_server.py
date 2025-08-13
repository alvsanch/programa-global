from flask import Flask, Response, request
from flask_cors import CORS
import cv2
import threading
import time
import os
from datetime import datetime
from pygame import mixer
from mutagen.wave import WAVE

# --- Configuración ---
FRAMES_OUTPUT_DIR = "C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\frames"
MUSIC_INPUT_DIR = "C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\musica_generada"
SHARED_SIGNALS_DIR = "C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\shared_data\\signals"

# --- Variables Globales ---
app = Flask(__name__)
CORS(app)
camera_state = {'capture': None} 

# ===============================================================
# --- FUNCIONES DE LÓGICA ---
# ===============================================================

def record_frames_thread(session_id, audio_filename=None):
    """Graba frames sincronizados con un audio, o durante 10s si no hay audio."""
    if camera_state['capture'] is None or not camera_state['capture'].isOpened():
        print("[SERVER] Error: Intento de grabar con la cámara apagada.")
        return

    duration_sec = 10.0 # Duración por defecto si no hay audio
    
    # Preparamos el audio si se proporcionó un nombre de archivo
    if audio_filename:
        audio_path = os.path.join(MUSIC_INPUT_DIR, audio_filename)
        if os.path.exists(audio_path):
            try:
                audio_file = WAVE(audio_path)
                duration_sec = audio_file.info.length
                print(f"[SERVER] Duración del audio detectada: {duration_sec:.2f} segundos")
                mixer.init()
                mixer.music.load(audio_path)
            except Exception as e:
                print(f"[SERVER] ADVERTENCIA: No se pudo cargar el audio '{audio_path}'. Grabando por 10s. Error: {e}")
                audio_filename = None
        else:
            print(f"[SERVER] ADVERTENCIA: No se encontró el archivo de audio '{audio_path}'. Grabando por 10s.")
            audio_filename = None

    output_dir = os.path.join(FRAMES_OUTPUT_DIR, session_id)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[SERVER] Iniciando grabación de {duration_sec:.2f}s para la sesión '{session_id}'")
    if audio_filename:
        mixer.music.play()

    start_time = time.time()
    frame_count = 0
    while time.time() - start_time < duration_sec:
        success, frame = camera_state['capture'].read()
        if not success: break
        
        frame_path = os.path.join(output_dir, f"frame_{frame_count:04d}.png")
        cv2.imwrite(frame_path, frame)
        frame_count += 1
        time.sleep(0.05)

    if audio_filename:
        mixer.music.stop()
        mixer.quit()

    print(f"[SERVER] Grabación finalizada. Se guardaron {frame_count} frames.")
    
    # Crear un archivo de señal al finalizar
    try:
        os.makedirs(SHARED_SIGNALS_DIR, exist_ok=True)
        signal_file_path = os.path.join(SHARED_SIGNALS_DIR, f"{session_id}.finished")
        with open(signal_file_path, 'w') as f:
            f.write(datetime.now().isoformat())
        print(f"[SERVER] Creado archivo de señal en: {signal_file_path}")
    except Exception as e:
        print(f"[SERVER] ❌ Error al crear el archivo de señal: {e}")

# ===============================================================
# --- RUTAS DE LA API (ENDPOINTS) ---
# ===============================================================

@app.route('/')
def index():
    return "Servidor de Cámara para Tesis"

@app.route('/snapshot')
def snapshot():
    if camera_state['capture'] is not None and camera_state['capture'].isOpened():
        success, frame = camera_state['capture'].read()
        if success:
            ret, buffer = cv2.imencode('.jpg', frame)
            return Response(buffer.tobytes(), mimetype='image/jpeg')
    return Response(status=204)

@app.route('/start_camera')
def start_camera():
    if camera_state['capture'] is None:
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera_state['capture'] = cap
            print("[SERVER] Cámara iniciada con éxito usando DSHOW.")
            return "OK"
        else:
            print("[SERVER] ERROR: No se pudo abrir ninguna cámara.")
            if cap: cap.release()
            return "Error: Camera not found", 500
    return "Already started"

@app.route('/stop_camera')
def stop_camera():
    if camera_state['capture'] is not None:
        camera_state['capture'].release()
        camera_state['capture'] = None
        print("[SERVER] Cámara detenida.")
        return "OK"
    return "Already stopped"

@app.route('/record_start')
def record_start():
    session_id = request.args.get('session_id', f"rec_{datetime.now().strftime('%H%M%S')}")
    audio_filename = request.args.get('audio_filename', None)
    
    record_thread = threading.Thread(target=record_frames_thread, args=(session_id, audio_filename))
    record_thread.start()
    return f"OK, iniciando grabación para la sesión {session_id}"

# ===============================================================
# --- PUNTO DE ENTRADA DEL SERVIDOR ---
# ===============================================================
if __name__ == '__main__':
    print("Iniciando servidor Flask para la cámara...")
    app.run(host='0.0.0.0', port=5000, threaded=True)