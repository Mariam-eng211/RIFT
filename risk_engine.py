class RiftRiskEngine:
    def __init__(self):
        # Define baseline values recorded during system startup
        self.baseline_moisture = 0.0   # %
        self.baseline_tilt = 0.0       # degrees (set to flat resting position)
        self.baseline_distance = 50.0  # cm

    def calculate_risk(self, current_moisture, current_tilt, current_distance, yolo_confidence=0.0):
        # 1. Calculate anomalies/deviations from baseline
        moisture_diff = max(0.0, current_moisture - self.baseline_moisture)
        moisture_score = min(100.0, (moisture_diff / 50.0) * 100.0) 

        # Measure absolute change from our 0-degree baseline
        tilt_diff = abs(current_tilt - self.baseline_tilt)
        tilt_score = min(100.0, (tilt_diff / 15.0) * 100.0) # Max out if tilted past 15 degrees

        # Displacement: if distance decreases significantly from baseline
        distance_diff = max(0.0, self.baseline_distance - current_distance)
        displacement_score = min(100.0, (distance_diff / 10.0) * 100.0) 

        # YOLO score comes directly as a percentage/confidence (0.0 to 1.0 -> 0 to 100)
        vision_score = yolo_confidence * 100.0

        # 2. RIFT Fusion Weights (Moisture: 25%, Tilt: 25%, Displacement: 30%, Vision: 20%)
        total_risk = (
            (moisture_score * 0.25) +
            (tilt_score * 0.25) +
            (displacement_score * 0.30) +
            (vision_score * 0.20)
        )

        # 3. Determine Risk State
        if total_risk >= 70.0:
            status = "🔴 INVESTIGATE (HIGH RISK - DEPLOY ROVER)"
        elif total_risk >= 40.0:
            status = "🟡 MONITOR (WATCH)"
        else:
            status = "🟢 NORMAL"

        return round(total_risk, 1), status