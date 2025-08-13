#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <MAX30105.h>
#include "spo2_algorithm.h"
#include <NTPClient.h>
#include <WiFiUdp.h>

// Incluimos el archivo de configuración con los datos sensibles
#include "config.h"

// =================================================================
// --- CONFIGURACIÓN DE RED Y HORA ---
// =================================================================
// IP estática deseada
IPAddress staticIP(192, 168, 1, 136);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

const int MQTT_PORT = 1883;
const char* MQTT_TOPIC = "tesis/biomedidas";
const char* MQTT_CONTROL_TOPIC = "tesis/control"; // Nuevo tópico para los comandos
// Desplazamiento UTC en segundos.
// UTC+2 para Madrid (CEST) = 2 * 3600 = 7200
const long UTC_OFFSET_SECONDS = 7200;
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", UTC_OFFSET_SECONDS);
// =================================================================
// --- CONFIGURACIÓN DE SENSORES Y PINES (CORREGIDO PARA ESP32) ---
// =================================================================
const int I2C_SDA_PIN = 21;
const int I2C_SCL_PIN = 22;
const int GSR_PIN = 36;
// --- Configuración Sensor de Temperatura (TMP102) ---
const int TEMP_I2C_ADDRESS = 0x48;
const byte TEMP_REGISTER = 0x00;
const byte TEMP_CONFIG_REGISTER = 0x01;

// --- Configuración Sensor de Pulso y Oximetría (MAX30105) ---
MAX30105 particleSensor;
const int SAMPLES_BUFFER_SIZE = 100; // 2 segundos de datos a 50Hz
uint32_t irBuffer[SAMPLES_BUFFER_SIZE];
uint32_t redBuffer[SAMPLES_BUFFER_SIZE];
int bufferIndex = 0;
// --- Estabilización de Lecturas ---
const int HR_HISTORY_SIZE = 4;
float hrHistory[HR_HISTORY_SIZE];
int hrHistoryIndex = 0;
int validHrReadings = 0;
unsigned long lastReadingTime = 0;

// =================================================================
// --- CLIENTES DE RED ---
// =================================================================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
bool isProgramRunning = false; // Flag para controlar la ejecución

// =================================================================
// --- FUNCIONES AUXILIARES ---
// =================================================================

// Función de callback para manejar los mensajes MQTT
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Mensaje recibido en el tema [");
  Serial.print(topic);
  Serial.print("]: ");
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  if (String(topic) == MQTT_CONTROL_TOPIC) {
    if (message.indexOf("start") != -1) {
      Serial.println("Comando 'start' recibido. Iniciando programa...");
      isProgramRunning = true;
    } else if (message.indexOf("stop") != -1) {
      Serial.println("Comando 'stop' recibido. Deteniendo programa...");
      isProgramRunning = false;
    }
  }
}

void setup_wifi() {
    delay(10);
    Serial.print("\nConfigurando IP estática...");
    if (!WiFi.config(staticIP, gateway, subnet)) {
      Serial.println("Fallo al configurar la IP estática");
    }
    Serial.print("\nConectando a WiFi...");
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println(" ¡Conectado!");
    Serial.print("Dirección IP: ");
    Serial.println(WiFi.localIP());
}

void reconnect_mqtt() {
    while (!mqttClient.connected()) {
        Serial.print("Intentando conexión MQTT...");
        String clientId = "ESP32-BioTesis-" + String(random(0xffff), HEX);
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println(" ¡Conectado!");
            // Suscribirse al tópico de control aquí
            mqttClient.subscribe(MQTT_CONTROL_TOPIC);
        } else {
            Serial.print(" falló, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" | Reintentando en 5 segundos...");
            delay(5000);
        }
    }
}

bool getStableTemperature(float &temperature) {
    const int MAX_RETRIES = 5;
    const float MIN_VALID_TEMP = 20.0, MAX_VALID_TEMP = 45.0;
    for (int i = 0; i < MAX_RETRIES; i++) {
        Wire.beginTransmission(TEMP_I2C_ADDRESS);
        Wire.write(TEMP_REGISTER);
        if (Wire.endTransmission() != 0) {
            delay(20);
            continue;
        }
        
        Wire.requestFrom(TEMP_I2C_ADDRESS, 2);
        if (Wire.available() == 2) {
            uint8_t msb = Wire.read();
            uint8_t lsb = Wire.read();
            int16_t rawTemp = ((msb << 8) | lsb) >> 4;
            float tempC = rawTemp * 0.0625;
            if (tempC > MIN_VALID_TEMP && tempC < MAX_VALID_TEMP) {
                temperature = tempC;
                return true;
            }
        }
        delay(50);
    }
    return false;
}

float getAverageHr(float newHr) {
    hrHistory[hrHistoryIndex] = newHr;
    hrHistoryIndex = (hrHistoryIndex + 1) % HR_HISTORY_SIZE;
    if (validHrReadings < HR_HISTORY_SIZE) {
        validHrReadings++;
    }

    float totalHr = 0;
    for (int i = 0; i < validHrReadings; i++) {
        totalHr += hrHistory[i];
    }
    return totalHr / validHrReadings;
}

void processAndPublishData() {
    // Definimos las variables con valores predeterminados para el JSON
    int32_t spo2 = -1;
    int32_t heartRate = -1;
    float temperatura = -1.0;
    int gsrValue = analogRead(GSR_PIN);
    // Proceso de SpO2 y Ritmo Cardíaco
    uint32_t irBufferCopy[SAMPLES_BUFFER_SIZE];
    uint32_t redBufferCopy[SAMPLES_BUFFER_SIZE];
    memcpy(irBufferCopy, irBuffer, sizeof(irBuffer));
    memcpy(redBufferCopy, redBuffer, sizeof(redBuffer));
    int32_t spo2_calc;
    int8_t validSPO2;
    int32_t heartRate_calc;
    int8_t validHeartRate;

    maxim_heart_rate_and_oxygen_saturation(irBufferCopy, SAMPLES_BUFFER_SIZE, redBufferCopy, &spo2_calc, &validSPO2, &heartRate_calc, &validHeartRate);
    // Validación y asignación de valores
    if (validHeartRate == 1 && heartRate_calc > 40 && heartRate_calc < 200) {
        heartRate = getAverageHr(heartRate_calc);
    }
    if (validSPO2 == 1 && spo2_calc >= 90) { // SpO2 > 90% es un rango válido
        spo2 = spo2_calc;
    }
    
    // Proceso de Temperatura
    getStableTemperature(temperatura);
    // Creación del documento JSON
    timeClient.update();
    unsigned long epochTime = timeClient.getEpochTime();
    
    StaticJsonDocument<256> doc;
    doc["timestamp"] = epochTime;
    doc["gsr"] = gsrValue;
    
    // Asignación condicional de valores al JSON
    if (temperatura != -1.0) {
        doc["temp"] = String(temperatura, 2);
    } else {
        doc["temp"] = "ND";
    }

    if (heartRate != -1) {
        doc["hr"] = String(heartRate, 1);
    } else {
        doc["hr"] = "ND";
    }

    if (spo2 != -1) {
        doc["spo2"] = spo2;
    } else {
        doc["spo2"] = "ND";
    }

    char payload[256];
    serializeJson(doc, payload);
    
    Serial.print("\nPublicando datos: ");
    Serial.println(payload);
    mqttClient.publish(MQTT_TOPIC, payload);
}


// =================================================================
// --- SETUP ---
// =================================================================
void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n--- Sistema de Bioseñales v2.1 (ESP32) ---");

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
    Wire.setClock(100000L);
    if (!particleSensor.begin(Wire, I2C_SPEED_STANDARD)) {
        Serial.println("Error: MAX30105 no encontrado. Revisa las conexiones I2C.");
        while (1);
    }
    Serial.println("-> Sensor MAX30105 inicializado.");
    
    particleSensor.setup(60, 4, 2, 400, 411, 4096);
    particleSensor.setPulseAmplitudeRed(0x0A);
    particleSensor.setPulseAmplitudeIR(0x0A);

    pinMode(GSR_PIN, INPUT);
    Serial.println("-> Sensores configurados.");

    setup_wifi();
    mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
    mqttClient.setCallback(callback); // Establecer la función de callback
    timeClient.begin();
    Serial.println("-> Red y NTP configurados.");
    
    Serial.println("=========================================");
    Serial.println("Coloca el dedo sobre el sensor...");
}


// =================================================================
// --- LOOP ---
// =================================================================
void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        setup_wifi();
    }
    if (!mqttClient.connected()) {
        reconnect_mqtt();
    }
    mqttClient.loop();
    
    if (isProgramRunning) {
        particleSensor.check();

        while (particleSensor.available()) {
            irBuffer[bufferIndex] = particleSensor.getIR();
            redBuffer[bufferIndex] = particleSensor.getRed();
            particleSensor.nextSample();
            
            bufferIndex++;
            if (bufferIndex >= SAMPLES_BUFFER_SIZE) {
                processAndPublishData();
                bufferIndex = 0;
            }
        }
    }
}