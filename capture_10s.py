import cv2
import os
import argparse
import time
from pygame import mixer
from mutagen.wave import WAVE
import warnings

# Ignorar las advertencias de pygame sobre el API obsoleto
warnings.filterwarnings("ignore", category=UserWarning)

def capture_video_with_audio(output_folder, audio_path, camera_index, delay_s, session_id):
    # Definir la ruta del archivo de señal en la carpeta compartida de Windows
    shared_data_dir = "C:\\Users\\alvar\\Desktop\\DOCTORADO\\PROGRAMAS\\shared_data"
    signal_dir = os.path.join(shared_data_dir, session_id)
    signal_file = os.path.join(signal_dir, "start_signal.txt")
    
    # Si el índice de la cámara es None, buscar uno automáticamente
    if camera_index is None:
        print("DEBUG: Buscando índice de cámara disponible...")
        found_camera = False
        # Empezar la búsqueda desde el índice 1 para priorizar la cámara USB
        for i in range(1, 10):
            cap_test = cv2.VideoCapture(i)
            if cap_test.isOpened():
                camera_index = i
                print(f"DEBUG: Cámara encontrada en el índice: {camera_index}")
                cap_test.release()
                found_camera = True
                break
            cap_test.release()
        
        # Si no se encuentra ninguna cámara aparte de la 0, usar la 0
        if not found_camera:
            print("ADVERTENCIA: No se encontró ninguna cámara USB. Se usará la cámara por defecto (índice 0).")
            camera_index = 0

    # --- Validación y obtención de duración ---
    if not os.path.exists(audio_path):
        print(f"ERROR: El archivo de audio no existe en '{audio_path}'")
        return

    try:
        audio_file = WAVE(audio_path)
        audio_duration = audio_file.info.length
        print(f"DEBUG: Duración real del audio detectada: {audio_duration:.2f} segundos")
    except Exception as e:
        print(f"ERROR al obtener duración con mutagen: {e}. Asumiendo 10.0 segundos.")
        audio_duration = 10.0

    # --- Inicialización ---
    mixer.init()
    mixer.music.load(audio_path)
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"ERROR: No se puede abrir la cámara con índice {camera_index}")
        mixer.quit()
        return

    # --- Configurar la resolución y FPS de la cámara ---
    # Se establece una resolución de 1280x720 (HD) y se intenta 30 FPS
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # --- Pre-captura para estabilización ---
    print(f"DEBUG: Pre-captura iniciada para estabilizar la cámara. Esperando {delay_s} segundos...")
    pre_capture_start = time.time()
    while time.time() - pre_capture_start < delay_s:
        ret, frame = cap.read()
        if not ret:
            print("ERROR: No se pudo capturar el frame durante la pre-captura.")
            break
        cv2.imshow('Pre-captura (no grabando)', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cv2.destroyAllWindows()
    print("DEBUG: Pre-captura finalizada. Cámara estabilizada.")

    # --- Creación de carpetas ---
    session_folder_name = time.strftime("%Y-%m-%d_%H-%M-%S")
    session_path = os.path.join(output_folder, session_folder_name)
    os.makedirs(session_path, exist_ok=True)
    print(f"DEBUG: Guardando frames en: {session_path}")

    # --- Crear el archivo de señal para el script de Bash ---
    print("DEBUG: Enviando señal de inicio a WSL2...")
    # Asegurarse de que el directorio de la señal existe
    os.makedirs(signal_dir, exist_ok=True)
    with open(signal_file, 'w') as f:
        f.write("start")

    # --- Captura real ---
    print("DEBUG: Iniciando reproducción y captura...")
    mixer.music.play()

    start_time = time.time()
    frame_count = 0

    while time.time() - start_time < audio_duration:
        ret, frame = cap.read()

        if not ret:
            print("ERROR: No se pudo capturar el frame.")
            break
        
        cv2.putText(frame, "GRABANDO", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.imshow('Captura en Progreso', frame)

        # Guardamos el frame en formato PNG con alta calidad
        frame_filename = os.path.join(session_path, f"frame_{frame_count:04d}.png")
        cv2.imwrite(frame_filename, frame, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        frame_count += 1

        if cv2.waitKey(1) & 0xFF == ord('q'):
            mixer.music.stop()
            break

    print(f"DEBUG: Bucle de captura finalizado. Se capturaron {frame_count} frames.")
    if frame_count == 0:
        print("ADVERTENCIA: No se capturaron frames.")

    # --- Limpieza ---
    cap.release()
    cv2.destroyAllWindows()
    # Usamos un timeout para evitar que el script se quede colgado
    timeout_start = time.time()
    while mixer.music.get_busy() and time.time() - timeout_start < 5:
        time.sleep(0.1)
    mixer.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Captura vídeo mientras reproduce un audio.")
    parser.add_argument("--output", required=True, help="Carpeta base donde se guardarán los frames.")
    parser.add_argument("--audio", required=True, help="Ruta al archivo de audio a reproducir.")
    parser.add_argument("--camera_index", type=int, default=None, help="Índice de la cámara a usar. Si no se especifica, se buscará automáticamente.")
    parser.add_argument("--delay", type=int, default=3, help="Tiempo de pre-captura en segundos para estabilizar la cámara.")
    parser.add_argument("--session_id", required=True, help="ID de la sesión para el comando MQTT.")
    args = parser.parse_args()
    capture_video_with_audio(args.output, args.audio, args.camera_index, args.delay, args.session_id)