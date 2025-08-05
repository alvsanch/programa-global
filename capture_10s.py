import argparse
import os
import time
from datetime import datetime
import cv2
import threading
import subprocess
import wave

# Función para reproducir audio en Windows
def reproducir_audio(audio_path):
    print(f"DEBUG: Reproduciendo audio en Windows: {audio_path}")
    try:
        # 'start' es un comando de Windows para abrir un archivo con su aplicación predeterminada
        subprocess.Popen(['start', '', audio_path], shell=True)
    except Exception as e:
        print(f"ERROR al reproducir audio en Windows: {e}")

# Función para estimar la duración del audio (para archivos WAV)
def estimar_duracion(audio_path):
    try:
        # Usamos wave para WAVs. Si se usan otros formatos, considerar pyDub o ffprobe (requiere ffmpeg)
        with wave.open(audio_path, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception as e:
        print(f"ERROR al obtener duración del audio: {e}. Asumiendo 10.0 segundos por defecto.")
        return 10.0  # Asumir duración por defecto si falla la estimación

def capturar_frames(output_dir, fps, duracion, camera_index=0): # <--- AÑADIDO: camera_index
    print(f"DEBUG: Intentando activar cámara con índice: {camera_index}") # <--- CAMBIADO
    cap = cv2.VideoCapture(camera_index) # <--- CAMBIADO: Usar el índice de la cámara

    if not cap.isOpened():
        print(f"ERROR: No se pudo abrir la cámara con índice {camera_index}.")
        print("Asegúrate de que la cámara esté conectada y no esté siendo usada por otra aplicación.")
        print("Podrías probar otros índices (0, 1, 2, etc.) para tu cámara USB.")
        return 0 # Devuelve 0 frames si no se puede abrir la cámara

    print(f"DEBUG: Cámara {camera_index} activada correctamente.") # <--- CAMBIADO
    start_time = time.time()
    frame_count = 0

    while time.time() - start_time < duracion:
        ret, frame = cap.read()
        if not ret:
            print("ADVERTENCIA: No se pudo leer el frame de la cámara. Reintentando...") # <--- AÑADIDO
            time.sleep(0.1) # Pequeña espera antes de reintentar # <--- AÑADIDO
            continue
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]
        frame_name = f"frame_{frame_count:04d}_{timestamp}.jpg"
        frame_path = os.path.join(output_dir, frame_name)
        
        try: # <--- AÑADIDO: Manejo de errores al guardar
            cv2.imwrite(frame_path, frame)
            # print(f"DEBUG: Frame guardado: {frame_path}") # Comentado para evitar spam excesivo
            frame_count += 1
        except Exception as e: # <--- AÑADIDO
            print(f"ERROR al guardar el frame {frame_name}: {e}") # <--- AÑADIDO

        # Esperar para mantener el FPS deseado
        time_elapsed_per_frame = time.time() - start_time - (frame_count -1) * (1 / fps) # <--- AÑADIDO
        sleep_duration = (1 / fps) - time_elapsed_per_frame # <--- AÑADIDO
        if sleep_duration > 0: # <--- AÑADIDO
            time.sleep(sleep_duration) # <--- CAMBIADO: Antes era 1/fps directamente

    cap.release()
    print(f"DEBUG: Captura finalizada. Total de frames: {frame_count}")
    return frame_count # <--- CAMBIADO: Devuelve el número de frames capturados

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, help='Ruta de salida de frames')
    parser.add_argument('--audio', required=True, help='Ruta del archivo de audio')
    parser.add_argument('--camera_index', type=int, default=0, # <--- AÑADIDO: Nuevo argumento para el índice de la cámara
                        help='Índice de la cámara a usar (0 para la predeterminada, 1 para la primera USB, etc.)')
    args = parser.parse_args()

    # Crear carpeta única con timestamp dentro de output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    subfolder = os.path.join(args.output, timestamp)
    os.makedirs(subfolder, exist_ok=True)
    print(f"DEBUG: Carpeta de salida creada: {subfolder}")

    # Obtener duración estimada del audio
    duracion = estimar_duracion(args.audio)
    print(f"DEBUG: Duración estimada del audio: {duracion:.2f} segundos")

    # Iniciar audio en un hilo (se ejecuta en Windows)
    audio_thread = threading.Thread(target=reproduzir_audio, args=(args.audio,))
    audio_thread.start()
    print("DEBUG: Hilo de audio iniciado.")

    # Capturar frames con el índice de cámara especificado
    frames_captured = capturar_frames(subfolder, fps=10, duracion=duracion, camera_index=args.camera_index) # <--- CAMBIADO

    # Esperar a que el hilo de audio termine (si no ha terminado ya)
    audio_thread.join()
    print("DEBUG: Hilo de audio finalizado.")

    if frames_captured == 0: # <--- AÑADIDO
        print("ADVERTENCIA: No se capturaron frames. Esto podría causar problemas en el análisis emocional.") # <--- AÑADIDO

if __name__ == "__main__":
    main()