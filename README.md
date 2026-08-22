# RIFT: Autonomous Environmental Hazard Telemetry & Response System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![ESP32](https://img.shields.io/badge/ESP32-Arduino-orange)](https://www.espressif.com/)
[![YOLOv8](https://img.shields.io/badge/Ultralytics-YOLOv8-green)](https://github.com/ultralytics/ultralytics)

**RIFT** is an end-to-end IoT and robotics framework designed to monitor, analyze, and autonomously respond to environmental instability (such as slope erosion, shifts, and moisture saturation). The system bridges physical sensor telemetry, computer vision inference, cloud MQTT messaging, and an interactive web command center.

---

##  System Architecture
[ ESP32 Rover ] ---> (MQTT Broker: HiveMQ) ---> [ FastAPI Backend ] ---> [ Web UI Dashboard ]
^                                                ^
|--- (Ultrasonic / MPU6050 / Soil Sensor)        |--- [ RiftRiskEngine ]
|--- [ YOLOv8 Vision Node ]

---

### Key Components:
1. **Edge Firmware (`firmware/rift_master.ino`)**: Runs on an ESP32 microcontroller, reading real-time tilt data from an MPU6050 accelerometer, soil moisture via analog pins, and obstacle distance via an HC-SR04 ultrasonic sensor. It publishes live metrics over MQTT and executes autonomous motor avoidance routines via an L298N driver.
2. **Multi-Indicator Fusion Engine (`backend/risk_engine.py`)**: Computes a composite risk score using a weighted matrix:
   - **Soil Moisture**: 25%
   - **Tilt / Incline Deviation**: 25%
   - **Physical Displacement**: 30%
   - **Computer Vision Confidence (YOLOv8)**: 20%
3. **Telemetry Dashboard (`backend/main.py`)**: A FastAPI backend featuring WebSockets for live data streaming, Leaflet.js GPS tracking, and automated threshold triggers.
4. **Vision Node (`vision/vision_node.py`)**: Executes real-time custom YOLOv8 object detection (`best.pt`) on video feeds, streaming hazard confidence scores directly to the backend risk engine.

---

##  Tech Stack
* **Microcontrollers & Hardware:** ESP32, L298N Motor Driver, MPU6050 IMU, HC-SR04 Ultrasonic Sensor, Soil Moisture Sensor.
* **Backend & Comm Protocol:** Python, FastAPI, WebSockets, Paho MQTT, HiveMQ.
* **Computer Vision & AI:** PyTorch, Ultralytics YOLOv8, OpenCV, MediaPipe.
* **Frontend:** HTML5, CSS3, JavaScript, Leaflet.js mapping.

---

##  Quick Start

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Mariam-eng11/RIFT-System.git](https://github.com/YOUR-USERNAME/RIFT-System.git)
   cd RIFT-System

2. **Install backend dependencies:**
    pip install fastapi uvicorn paho-mqtt ultralytics opencv-python pydantic
    python backend/main.py
    python vision/vision_node.py
