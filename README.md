# Sistema de Captura y Análisis Emocional v3.0

Este repositorio contiene un sistema completo para capturar, sincronizar y analizar datos biométricos y emociones basadas en música. El sistema integra un ESP32 con sensores biométricos, scripts Python y Bash para control, y utilidades para procesamiento en Windows y Linux.

---

## Tabla de Contenidos

- [Descripción general](#descripción-general)
- [Estructura de archivos](#estructura-de-archivos)
- [Requisitos](#requisitos)
- [Funcionamiento general](#funcionamiento-general)
    - [1. ESP32: Adquisición de datos biométricos](#1-esp32-adquisición-de-datos-biométricos)
    - [2. Receptor y Control de Grabación (Python)](#2-receptor-y-control-de-grabación-python)
    - [3. Script de Coordinación (Bash)](#3-script-de-coordinación-bash)
    - [4. Captura de frames y sincronización con audio (Windows/Python)](#4-captura-de-frames-y-sincronización-con-audio-windowspython)
- [Flujo de trabajo](#flujo-de-trabajo)
- [Notas adicionales](#notas-adicionales)
- [Créditos](#créditos)

---

## Descripción general

El sistema permite:

- Capturar datos biométricos (temperatura, ritmo cardíaco, SpO2, GSR) en tiempo real con ESP32 y sensores.
- Sincronizar comandos de inicio/fin de grabación a través de MQTT.
- Ejecutar scripts que controlan la grabación de biométricas, frames de vídeo y audio de música generada.
- Almacenar y estructurar los datos para su posterior análisis emocional.

## Estructura de archivos

- `final_ESP32.ino` — Código para ESP32. Lee sensores, publica datos vía MQTT.
- `receptor_controlado.py` — Script Python receptor para guardar datos biométricos en CSV, controlado por comandos MQTT.
- `script_global.sh` — Script Bash que automatiza la ejecución de todo el flujo experimental, controla la grabación y análisis.
- `capture_10s.py` — Script Python para Windows: sincroniza la reproducción de audio y la captura de frames de vídeo.
- (Otros scripts, como `analizar_emocion.py`, pueden ser referenciados pero no están incluidos aquí.)

## Requisitos

- **Hardware:** ESP32, Sensor MAX30105, Sensor TMP102 o similar, sensor GSR, cámara USB.
- **Software:**
    - Python 3.x (Linux y/o Windows)
    - Bibliotecas Python: `paho-mqtt`, `opencv-python`, `wave`
    - MQTT Broker (`mosquitto` recomendado)
    - Arduino IDE y dependencias (para ESP32)
    - Bash y utilidades GNU/Linux
    - PowerShell (en Windows)

## Funcionamiento general

### 1. ESP32: Adquisición de datos biométricos

- Lee datos de sensores (pulso, SpO2, temperatura, GSR).
- Publica datos formateados en JSON por MQTT en el tópico `tesis/biomedidas`.

### 2. Receptor y Control de Grabación (Python)

- `receptor_controlado.py` se suscribe a dos tópicos:
    - `tesis/biomedidas`: recibe datos biométricos.
    - `tesis/control`: recibe comandos JSON (`start/stop`).
- Al recibir `start`, comienza una nueva grabación en CSV. Al recibir `stop`, finaliza y cierra el archivo.

### 3. Script de Coordinación (Bash)

- `script_global.sh` automatiza el proceso:
    1. Inicia el receptor de biométricas.
    2. Monitorea un directorio de archivos de música.
    3. Por cada archivo nuevo:
        - Envía comando `start` (MQTT) para iniciar grabación biométrica.
        - Llama a `capture_10s.py` en Windows (vía PowerShell) para reproducir audio y capturar frames de la cámara.
        - Envía comando `stop` (MQTT) para finalizar grabación biométrica.
        - Ejecuta el análisis emocional sobre los frames capturados.

### 4. Captura de frames y sincronización con audio (Windows/Python)

- `capture_10s.py` recibe la ruta de salida, audio y el índice de cámara.
- Estima duración del audio, inicia reproducción y captura de frames sincronizada.

## Flujo de trabajo

1. **Preparar todo el hardware**: sensores conectados al ESP32, cámara lista, broker MQTT en funcionamiento.
2. **Cargar y ejecutar `final_ESP32.ino` en el ESP32.**
3. **Ejecutar `script_global.sh` en Linux**: este script lanzará el receptor, analizará nuevos archivos de música y coordinará todo el flujo automáticamente.
4. **En Windows, asegúrate de tener `capture_10s.py` y los archivos de audio y scripts necesarios.**
5. **El sistema manejará la grabación, sincronización y análisis de los datos biométricos y visuales.**

## Notas adicionales

- **Configuración**: Modifica las rutas en los scripts para adaptarlas a tu entorno.
- **MQTT Broker**: Asegúrate de que el broker esté activo y accesible para todos los dispositivos.
- **Permisos**: Algunos scripts requieren permisos de ejecución y acceso a dispositivos.

## Créditos

- Inspirado y desarrollado por [alvsanch](https://github.com/alvsanch).
- Basado en múltiples recursos de la comunidad para integración de sensores, MQTT y análisis emocional.

---

¡Para cualquier duda, revisa los comentarios en cada script y abre un issue!
