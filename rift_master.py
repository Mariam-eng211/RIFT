import cv2
import requests
from ultralytics import YOLO

# Initialize YOLO model (swap 'yolov8n.pt' for your custom 'best.pt' if trained on cracks/rocks)
model = YOLO('yolov8n.pt') 
cap = cv2.VideoCapture(0)

DASHBOARD_URL = "http://127.0.0.1:8080/vision_alert"
print("[RIFT VISION] Online. Scanning for hazards...")

while True:
    ret, frame = cap.read()
    if not ret: break

    results = model(frame, stream=True)
    
    for r in results:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf > 0.6: 
                name = model.names[int(box.cls[0])]
                
                # Send alert to the web dashboard
                try:
                    requests.post(DASHBOARD_URL, json={"detected": name, "confidence": conf}, timeout=1)
                    print(f"⚠️ Sent Alert: {name} detected ({conf:.2f})")
                except requests.exceptions.RequestException:
                    pass 
                
                # Draw local bounding box
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    cv2.imshow("RIFT Rover Camera Feed", frame)
    if cv2.waitKey(1) == ord('q'): break

cap.release()
cv2.destroyAllWindows()