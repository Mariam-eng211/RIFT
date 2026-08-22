import cv2
import requests
from ultralytics import YOLO

# Load custom trained YOLOv8 model weights
print("Loading RIFT custom YOLO model (best.pt)...")
model = YOLO('best.pt') 

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

DASHBOARD_URL = "http://127.0.0.1:8080/vision_alert"
print("[RIFT VISION] Online. Scanning for environmental hazards...")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: 
        print("Error: Failed to grab frame.")
        break

    results = model(frame, stream=True)
    
    for r in results:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf > 0.6: 
                name = model.names[int(box.cls[0])]
                
                # Send live alert to FastAPI backend risk system
                try:
                    requests.post(DASHBOARD_URL, json={"detected": name, "confidence": conf}, timeout=0.5)
                    print(f"⚠️ Sent Alert: {name} detected ({conf:.2f})")
                except requests.exceptions.RequestException:
                    pass 
                
                # Draw local tracking bounding box
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, f"{name} {conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    cv2.imshow("RIFT Rover Camera Feed - YOLOv8", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

cap.release()
cv2.destroyAllWindows()