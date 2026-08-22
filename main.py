import asyncio
import json
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import paho.mqtt.client as mqtt
import uvicorn
from risk_engine import RiftRiskEngine

app = FastAPI(title="RIFT Terminal")
risk_engine = RiftRiskEngine()

latest_data = {
    "moisture": 0.0, "tilt": 0.0, "distance": 50.0,
    "risk_score": 0.0, "status": "🟢 NORMAL",
    "gps": {"lat": 42.8157, "lng": 74.6341, "heading": "NNE"},
    "last_detection": {"name": "None", "confidence": 0.0}
}
current_lat, current_lng = 42.8157, 74.6341
connected_clients = set()
server_loop = None

@app.on_event("startup")
async def startup_event():
    global server_loop
    server_loop = asyncio.get_running_loop()

# --- MQTT SETUP ---
MQTT_BROKER = "broker.hivemq.com"
client_id = f"rift-dash-{random.randint(1000, 9999)}"

try: 
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
except AttributeError: 
    mqtt_client = mqtt.Client(client_id)

def on_connect(client, userdata, flags, rc, *args):
    print(f"Connected to HiveMQ! Status code: {rc}")
    client.subscribe("rift/telemetry")

async def broadcast_data():
    if connected_clients:
        msg = json.dumps(latest_data)
        to_remove = set()
        for client in connected_clients:
            try:
                await client.send_text(msg)
            except Exception:
                to_remove.add(client)
        connected_clients.difference_update(to_remove)

def on_message(client, userdata, msg):
    global latest_data, current_lat, current_lng, server_loop
    try:
        raw_data = msg.payload.decode("utf-8")
        parts = raw_data.split(",")
        if len(parts) >= 3:
            moisture = float(parts[0])
            tilt = float(parts[1])
            distance = float(parts[2])
            
            latest_data["moisture"] = moisture
            latest_data["tilt"] = tilt
            latest_data["distance"] = distance
            
            # Compute risk incorporating current vision confidence
            vision_conf = latest_data["last_detection"]["confidence"]
            risk_score, status_text = risk_engine.calculate_risk(
                current_moisture=moisture, 
                current_tilt=tilt, 
                current_distance=distance, 
                yolo_confidence=vision_conf
            )
            
            latest_data["risk_score"] = risk_score
            latest_data["status"] = status_text
            
            # Autonomous trigger if risk breaches critical threshold
            if risk_score >= 70.0:
                print("🚨 HIGH RISK DETECTED! Automatically publishing DEPLOY command...")
                mqtt_client.publish("rift/commands", "DEPLOY")

            if "NORMAL" in status_text: 
                current_lat += 0.00002 
            
            latest_data["gps"] = {"lat": round(current_lat, 6), "lng": round(current_lng, 6), "heading": "NNE"}

            if server_loop and server_loop.is_running():
                asyncio.run_coroutine_threadsafe(broadcast_data(), server_loop)
                
    except Exception as e: 
        print(f"Parse Error: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>RIFT // Telemetry Terminal</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root { --bg: #0b0f12; --panel: #13181d; --border: #212c36; --text: #c0cbd6; --mono: 'Courier New', Courier, monospace; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg); color: var(--text); font-family: sans-serif; padding: 15px; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 15px; }
        .panel { background: var(--panel); border: 1px solid var(--border); padding: 15px; border-radius: 4px; }
        .val { font-family: var(--mono); font-size: 1.8rem; font-weight: bold; color: #fff; }
        .badge { padding: 3px 8px; border-radius: 2px; font-size: 0.75rem; font-weight: bold; font-family: var(--mono); }
        .NORMAL, .STABLE { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }
        .CAUTION { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid #f59e0b; }
        .CRITICAL, .INVESTIGATE, .HAZARD { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }
        #map { height: 240px; width: 100%; filter: brightness(0.6) invert(1) contrast(3) hue-rotate(200deg); margin-top: 10px; }
        .btn-row { display: flex; gap: 12px; }
        button { flex: 1; padding: 12px; font-weight: bold; font-family: var(--mono); cursor: pointer; border: none; border-radius: 4px; }
        .btn-green { background: #10b981; color: #000; }
        .btn-red { background: #ef4444; color: #fff; }
    </style>
</head>
<body>
    <div class="grid">
        <div class="panel">
            <div style="color: #64748b; font-size: 0.7rem; margin-bottom: 5px;">COMPOSITE RISK</div>
            <div id="risk" class="val">0.0%</div>
            <div style="margin-top: 8px;"><span id="status" class="badge NORMAL">🟢 NORMAL</span></div>
        </div>
        <div class="panel">
            <div style="color: #64748b; font-size: 0.7rem; margin-bottom: 5px;">METRICS</div>
            <div style="display: flex; justify-content: space-between;">
                <div><div style="font-size: 0.65rem; color: #64748b;">TILT</div><span id="tilt" class="val">0.0°</span></div>
                <div><div style="font-size: 0.65rem; color: #64748b;">MOISTURE</div><span id="moist" class="val">0.0%</span></div>
            </div>
        </div>
        <div class="panel">
            <div style="color: #64748b; font-size: 0.7rem; margin-bottom: 5px;">SPATIAL & VISION</div>
            <div style="display: flex; justify-content: space-between;">
                <div><div style="font-size: 0.65rem; color: #64748b;">OBSTACLE</div><span id="dist" class="val">50.0 cm</span></div>
                <div><div style="font-size: 0.65rem; color: #64748b;">YOLO TARGET</div><div id="vision" style="font-family: var(--mono); color: #f59e0b; margin-top: 5px;">None (0.00)</div></div>
            </div>
        </div>
        <div class="panel" style="grid-column: span 3;">
            <div style="color: #64748b; font-size: 0.7rem;">LIVE TRACKING</div>
            <div id="map"></div>
        </div>
    </div>
    <div class="panel btn-row">
        <button class="btn-green" onclick="sendCmd('DEPLOY')">DEPLOY ROVER</button>
        <button class="btn-red" onclick="sendCmd('STOP')">EMERGENCY STOP</button>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([42.8157, 74.6341], 17);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        const marker = L.circleMarker([42.8157, 74.6341], { radius: 6, color: '#f59e0b', fillOpacity: 1 }).addTo(map);

        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        
        ws.onmessage = e => {
            const d = JSON.parse(e.data);
            document.getElementById('risk').innerText = d.risk_score + '%';
            document.getElementById('tilt').innerText = d.tilt + '°';
            document.getElementById('moist').innerText = d.moisture + '%';
            document.getElementById('dist').innerText = d.distance + ' cm';
            document.getElementById('gps').innerText = d.gps.lat + ', ' + d.gps.lng;
            document.getElementById('vision').innerText = d.last_detection.name + ' (' + d.last_detection.confidence.toFixed(2) + ')';
            
            const badge = document.getElementById('status');
            badge.innerText = d.status;
            badge.className = 'badge ' + (d.status.includes('INVESTIGATE') || d.status.includes('CRITICAL') || d.status.includes('HAZARD') ? 'CRITICAL' : d.status.includes('MONITOR') ? 'CAUTION' : 'NORMAL');

            marker.setLatLng([d.gps.lat, d.gps.lng]);
        };
        const sendCmd = cmd => fetch('/command', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({command: cmd}) });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_dash(): return HTML_CONTENT

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: connected_clients.remove(websocket)

@app.post("/command")
async def handle_cmd(payload: dict):
    mqtt_client.publish("rift/commands", payload.get("command"))
    return {"status": "sent"}

@app.post("/vision_alert")
async def handle_vision_alert(payload: dict):
    global latest_data, server_loop
    detected_name = payload.get("detected", "Unknown")
    confidence = float(payload.get("confidence", 0.0))
    
    latest_data["last_detection"] = {"name": detected_name, "confidence": confidence}
    
    risk_score, status_text = risk_engine.calculate_risk(
        current_moisture=latest_data["moisture"],
        current_tilt=latest_data["tilt"],
        current_distance=latest_data["distance"],
        yolo_confidence=confidence
    )
    latest_data["risk_score"] = risk_score
    latest_data["status"] = status_text

    if risk_score >= 70.0:
        mqtt_client.publish("rift/commands", "DEPLOY")

    if server_loop and server_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_data(), server_loop)
        
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)