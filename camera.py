import cv2
import threading
import time
import os
import numpy as np
from ultralytics import YOLO
from datetime import datetime

class VideoCamera:
    def __init__(self, model_path='model/best.pt', source=0):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        self.lock = threading.Lock()
        
        # Load YOLO model
        try:
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
            else:
                self.model = YOLO('yolov8n.pt')
        except Exception as e:
            print(f"AI Engine Error: {e}")
            self.model = None
            
        self.is_running = True
        self.frame = None
        self.last_detection_time = 0
        self.detection_interval = 0.05  # Faster processing (20fps target)
        self.violations = []
        
        # Start background thread for reading frames
        self.thread = threading.Thread(target=self._update, args=())
        self.thread.daemon = True
        self.thread.start()

    def _update(self):
        while self.is_running:
            success, frame = self.cap.read()
            if success:
                # Frame skipping logic to maintain real-time performance
                if time.time() - self.last_detection_time > self.detection_interval:
                    if self.model:
                        results = self.model(frame, verbose=False)
                        annotated = self._process_frame(frame, results)
                    else:
                        annotated = self._draw_hud(frame)
                    
                    self.last_detection_time = time.time()
                    with self.lock:
                        self.frame = annotated
                else:
                    # Update just the HUD for compliance/telemetry on intermediate frames
                    with self.lock:
                        self.frame = self._draw_hud(frame)
            else:
                # Reconnection attempt or No Signal fallback
                self.cap.release()
                time.sleep(2)
                self.cap = cv2.VideoCapture(self.source)
                with self.lock:
                    self.frame = self._create_no_signal_frame()

    def _create_no_signal_frame(self):
        # Professional "No Signal" display
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(frame, "!!! NO SIGNAL: VISION CORE OFFLINE !!!", (350, 360), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.rectangle(frame, (100, 100), (1180, 620), (0, 0, 150), 2)
        return frame

    def _draw_hud(self, frame):
        h, w = frame.shape[:2]
        hud = frame.copy()
        
        # Professional Corner Brackets
        c_len = 50
        color = (248, 189, 56) # Sky Blue vision in BGR
        # Top-Left
        cv2.line(hud, (10, 10), (10+c_len, 10), color, 1)
        cv2.line(hud, (10, 10), (10, 10+c_len), color, 1)
        # Top-Right
        cv2.line(hud, (w-10, 10), (w-10-c_len, 10), color, 1)
        cv2.line(hud, (w-10, 10), (w-10, 10+c_len), color, 1)
        
        # HUD Telemetry Text
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        cv2.putText(hud, f"VISION_CORE: RUNNING | {timestamp}", (20, h-20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Scanline simulation (subtle grey lines)
        for i in range(0, h, 20):
            cv2.line(hud, (0, i), (w, i), (50, 50, 50), 1)
            
        return hud

    def _process_frame(self, frame, results):
        annotated_frame = self._draw_hud(frame)
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                conf = box.conf[0]
                cls = int(box.cls[0])
                label = self.model.names[cls]
                
                # Violation logic
                if label in ['no_helmet', 'no_vest', 'No_Helmet', 'No_Vest']:
                    color = (0, 0, 255) # Warning Red
                    self._handle_violation(label, frame)
                else:
                    color = (248, 189, 56) # Safe Sky Blue
                
                # Modern Bounding Boxes
                cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 1)
                cv2.rectangle(annotated_frame, (int(x1), int(y1)-15), (int(x1)+100, int(y1)), color, -1)
                cv2.putText(annotated_frame, f'{label.upper()}', (int(x1)+5, int(y1)-5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                            
        return annotated_frame

    def _handle_violation(self, label, frame):
        now = time.time()
        if not hasattr(self, 'last_violation_time'):
            self.last_violation_time = {}
            
        if now - self.last_violation_time.get(label, 0) > 8: # Increased cooldown for performance
            self.last_violation_time[label] = now
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"violation_{label}_{timestamp}.jpg"
            save_path = os.path.join('static/uploads', filename)
            
            # Save in separate thread to avoid blocking vision loop
            threading.Thread(target=cv2.imwrite, args=(save_path, frame)).start()
            
            self.violations.append({
                'type': label,
                'snapshot': filename,
                'time': datetime.now()
            })

    def get_frame(self):
        with self.lock:
            if self.frame is not None:
                ret, jpeg = cv2.imencode('.jpg', self.frame)
                return jpeg.tobytes()
        return None

    def stop(self):
        self.is_running = False
        self.cap.release()
