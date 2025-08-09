Sistema de Análisis de Emociones y Bioseñales en Respuesta a Música Generativa

Este proyecto forma parte de mi tesis doctoral, donde investigo la correlación entre las respuestas fisiológicas y emocionales de una persona y los estímulos musicales generados por un modelo de inteligencia artificial.

El sistema completo se ejecuta en un entorno híbrido de Windows 11 con WSL2 y utiliza un dispositivo ESP32 para la captura de datos biométricos.

⚙️ Componentes del Sistema
El proyecto se compone de varios scripts que trabajan de forma sincronizada:

Componente	Entorno de Ejecución	Descripción
script_global.sh	WSL2 (Bash)	Es el orquestador principal. Monitorea la carpeta de música generada, coordina el inicio y final de la grabación de vídeo y biomedidas, y lanza el análisis de emociones.
capture_10s.py	Windows 11 (Python)	Controla la cámara y la reproducción del audio. Inicia una pre-captura para estabilizar el enfoque, graba los frames a 30 FPS en alta calidad (PNG) y crea un archivo de señal para sincronizarse con WSL2.
receptor_controlado.py	WSL2 (Python)	Un cliente MQTT que se ejecuta en segundo plano. Recibe los comandos START y STOP y los datos biométricos del ESP32, guardando la información en un archivo CSV.
analizar_emocion.py	WSL2 (Python)	Procesa los frames de vídeo capturados por la cámara y utiliza DeepFace para detectar y clasificar las emociones faciales del sujeto de prueba.
final_ESP32.ino	Arduino (ESP32)	El firmware del ESP32. Utiliza sensores para medir la bioseñal (ritmo cardíaco, SpO2, respuesta galvánica de la piel) y publica los datos vía MQTT.

Exportar a Hojas de cálculo
🚀 Flujo de Trabajo
El proceso de captura y análisis se automatiza por completo de la siguiente manera:

Generación de música: El modelo generativo ace-step (no incluido en este repositorio) produce un archivo de audio (.wav) en una carpeta específica de WSL2.

Detección y Sincronización: script_global.sh detecta el nuevo archivo y lanza capture_10s.py en Windows. El script de Windows inicia la cámara y, tras un breve periodo de estabilización, crea un archivo de señal.

Grabación Sincronizada: script_global.sh detecta el archivo de señal, envía el comando START por MQTT al receptor_controlado.py y a la vez, capture_10s.py comienza a grabar frames y reproducir la música.

Finalización: Al terminar la música, el script de Bash envía el comando STOP a través de MQTT, deteniendo la grabación de biomedidas.

Análisis: Finalmente, analizar_emocion.py procesa los frames de vídeo capturados, generando un archivo CSV con el análisis emocional para su posterior correlación con los datos biométricos.

🛠️ Requisitos del Sistema
Sistema operativo: Windows 11

Entorno de virtualización: WSL2

Hardware: PC con al menos 32 GB de RAM y una RTX 4050 o superior.

Dispositivos: ESP32 con los sensores correspondientes y una cámara USB.

Software:

Python 3.12 (en ambos entornos)

Docker Desktop (para el broker MQTT)

IDE de Arduino

Librerías de Python: paho-mqtt, pygame, mutagen, deepface, opencv-python, pandas.
