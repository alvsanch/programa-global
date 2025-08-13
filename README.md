Tesis: Emociones a través de la Música y Bioseñales

Este repositorio contiene el código de la tesis doctoral que tiene como objetivo principal la traducción de bioseñales y expresiones faciales a emociones, utilizando estas emociones para guiar la generación de música a través de un modelo ace-step optimizado. El proyecto integra hardware (ESP32 con sensores) y software (servidores, scripts de control, y una interfaz Gradio) en un ecosistema de Windows 11 con WSL2.

🛠️ Tecnologías y Módulos Principales
El flujo de trabajo completo se orquesta a través de varios módulos interconectados.

1. 🎵 Generación Musical (ACE-Step)
Descripción: Un modelo generativo de música (ace-step) que se ajusta (fine-tuning) para producir piezas musicales que evocan estados emocionales específicos.

Archivos Clave:

run_acestep.sh: Script de bash para lanzar de forma segura la GUI de ace-step dentro de un entorno virtual de WSL2.

2. ❤️ Recopilación de Bioseñales (ESP32)
Descripción: Un microcontrolador ESP32 equipado con sensores para capturar datos fisiológicos en tiempo real, como ritmo cardíaco (HR), oximetría de pulso (SpO2), respuesta galvánica de la piel (GSR) y temperatura.

Archivos Clave:

final_ESP32.ino: Código Arduino para el ESP32. Se conecta a un bróker MQTT, recopila datos de los sensores (MAX30105 y TMP102) y los publica. También es capaz de recibir comandos de start y stop a través de un tópico de control MQTT.

receptor_controlado.py: Script de Python que se ejecuta en WSL2 y se suscribe a los tópicos MQTT. Recibe las bioseñales y los comandos, guardando los datos en un archivo CSV por sesión.

3. 📸 Captura y Análisis de Emociones Faciales
Descripción: Durante la reproducción de la música generada, se captura el vídeo del usuario. Los frames de este vídeo se analizan con DeepFace para detectar la emoción dominante.

Archivos Clave:

camera_server.py: Servidor Flask en Windows 11 que gestiona la cámara web. Proporciona endpoints para iniciar/detener la cámara y grabar frames de vídeo, opcionalmente sincronizado con un archivo de audio.

capture_10s.py: Un script de Python para Windows que graba vídeo sincronizado con un audio WAV y guarda los frames en una carpeta específica.

analizar_emocion.py: Script de Python que utiliza la biblioteca DeepFace para procesar una carpeta de frames y generar un archivo CSV con la emoción dominante y las puntuaciones de cada emoción por frame.

4. 🚀 Orquestación y Flujo de Trabajo
El proyecto utiliza una combinación de scripts y una interfaz gráfica para gestionar todo el proceso de forma manual o automática.

Archivos Clave:

iniciar_tesis.bat: Archivo de batch para Windows que lanza el servidor de cámara y la interfaz de WSL2 de forma unificada.

start_all.sh: Script de bash que se ejecuta en WSL2. Inicia el receptor de bioseñales en segundo plano y la interfaz gráfica de Gradio en primer plano.

app_tesis.py: Interfaz de usuario completa desarrollada con Gradio. Permite controlar todos los módulos:

Flujo principal: Gestiona la creación de sesiones, la grabación sincronizada y el análisis de datos.

Análisis facial: Controla la cámara y la grabación manual o en modo automático (monitorizando la salida de ace-step).

Biomedidas: Permite el control manual del dispositivo ESP32 y la visualización de los datos recopilados.

script_global.sh: Un script de bash más robusto que ofrece un modo manual y un modo de monitorización para automatizar el ciclo de generación musical, grabación de bioseñales y análisis facial.

⚙️ Configuración y Requisitos
El entorno está diseñado para ejecutarse en Windows 11 con WSL2.

Sistema Operativo: Windows 11.

Entorno WSL2: Se requiere una distribución de Linux, como Ubuntu, para ejecutar los scripts de bash y las aplicaciones de Python.

Hardware: Se utiliza un ordenador con GPU (como una RTX 4050 con 32 GB de RAM), una cámara web y un microcontrolador ESP32 con sensores.

Dependencias de Software: Python 3, pip, venv, Docker o Mosquitto (para el bróker MQTT), inotify-tools (para la monitorización de archivos), y varias bibliotecas de Python como flask, opencv-python, deepface, gradio, paho-mqtt, pandas, plotly, mutagen, pygame y watchdog.
