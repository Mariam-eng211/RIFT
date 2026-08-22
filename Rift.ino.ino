#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <WiFi.h>
#include <PubSubClient.h>

// --- Wi-Fi & MQTT CONFIGURATION ---
const char* ssid = "Mariam";          
const char* password = "japozundu1";   
const char* mqtt_server = "broker.hivemq.com"; 

WiFiClient espClient;
PubSubClient client(espClient);
Adafruit_MPU6050 mpu;

// Motor & Sensor Pins
const int enA = 13, in1 = 12, in2 = 14, in3 = 25, in4 = 26, enB = 27;
const int trigPin = 5, echoPin = 18;
const int soilPin = 34;
const int RAW_DRY = 4095, RAW_WET = 1400; 

bool roverDeployed = false;

void stopRover() {
  digitalWrite(in1, LOW);  digitalWrite(in2, LOW);
  digitalWrite(in3, LOW);  digitalWrite(in4, LOW);
}

void moveForward() {
  digitalWrite(in1, HIGH); digitalWrite(in2, LOW);
  digitalWrite(in3, HIGH); digitalWrite(in4, LOW);
}

void moveBackward() {
  digitalWrite(in1, LOW);  digitalWrite(in2, HIGH);
  digitalWrite(in3, LOW);  digitalWrite(in4, HIGH);
}

void turnRight() {
  digitalWrite(in1, HIGH); digitalWrite(in2, LOW);
  digitalWrite(in3, LOW);  digitalWrite(in4, HIGH);
}

// --- MQTT COMMAND HANDLER ---
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String command = "";
  for (unsigned int i = 0; i < length; i++) command += (char)payload[i];
  command.trim();

  Serial.print("Received MQTT Command: ");
  Serial.println(command);

  if (command == "DEPLOY") {
    Serial.println("ACK: DEPLOY RECEIVED -> ROVER UNLOCKED");
    roverDeployed = true;
  } else if (command == "STOP") {
    Serial.println("ACK: EMERGENCY STOP RECEIVED");
    roverDeployed = false;
    stopRover(); 
  }
}

void setupWifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nWiFi connected.");
}

void reconnectMqtt() {
  while (!client.connected()) {
    String clientId = "RIFTRover-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("Connected to MQTT Broker!");
      client.subscribe("rift/commands");
    } else {
      Serial.print("MQTT connection failed, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

float getDistance() {
  digitalWrite(trigPin, LOW); delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 30000); 
  return (duration == 0) ? 400.0 : duration * 0.034 / 2;
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22); 
  Wire.beginTransmission(0x68); Wire.write(0x6B); Wire.write(0); Wire.endTransmission(true);

  pinMode(enA, OUTPUT); pinMode(enB, OUTPUT);
  pinMode(in1, OUTPUT); pinMode(in2, OUTPUT);
  pinMode(in3, OUTPUT); pinMode(in4, OUTPUT);
  pinMode(trigPin, OUTPUT); pinMode(echoPin, INPUT); pinMode(soilPin, INPUT);

  // INCREASED MOTOR SPEED TO MAX (255) TO OVERCOME FRICTION
  analogWrite(enA, 255); 
  analogWrite(enB, 255);
  stopRover();

  mpu.begin(0x68);
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);

  setupWifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(mqttCallback);
}

void loop() {
  if (!client.connected()) reconnectMqtt();
  client.loop();

  // 1. Read & Transmit Telemetry
  int rawSoil = analogRead(soilPin);
  int moisturePercent = map(constrain(rawSoil, RAW_WET, RAW_DRY), RAW_DRY, RAW_WET, 0, 100);

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  float tilt = atan2(a.acceleration.y, sqrt(a.acceleration.x * a.acceleration.x + a.acceleration.z * a.acceleration.z)) * 180.0 / PI;
  float distance = getDistance();

  String payload = String(moisturePercent) + "," + String(tilt) + "," + String(distance);
  client.publish("rift/telemetry", payload.c_str());

  // 2. Rover Actuation
  if (roverDeployed) {
    if (distance < 20.0) {
      stopRover(); delay(200);
      moveBackward(); delay(500);
      turnRight(); delay(700);
      stopRover();
    } else {
      moveForward();
    }
  } else {
    stopRover();
  }
  delay(100); 
}