import cv2 
import time 
import math 
import mediapipe as mp 
from flask import Flask, render_template_string, Response 
 
# Initialize the web server 
app = Flask(__name__) 
 
class RobotStreamer: 
    def __init__(self): 
        print("[STREAM] Initializing IMX708 Camera...") 
        # Using V4L2 bridge setup for Raspberry Pi 5 
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2) 
         
        if not self.cap.isOpened(): 
            raise RuntimeError("[STREAM] CRITICAL: Camera failed to open. Did you 
use libcamerify?") 
             
        # 640x480 is optimal for low-latency streaming and tracking 
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640) 
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) 
         
        # Initialize MediaPipe Hands with resource-friendly settings 
        self.mp_hands = mp.solutions.hands 
        self.hands = self.mp_hands.Hands( 
            static_image_mode=False, 
            max_num_hands=1,          # Tracking 1 hand reduces CPU overhead 
            model_complexity=0,       # 0 = Light/Fast (Optimized for 2GB Pi) 
            min_detection_confidence=0.5, 
            min_tracking_confidence=0.5 
        ) 
        self.mp_draw = mp.solutions.drawing_utils 
         
        print("[STREAM] Camera & 3D Tracking Engine Ready.") 
 
    def generate_frames(self): 
        """Captures frames, processes hand tracking, encodes to JPEG, and yields to 
network.""" 
        while True: 
            success, frame = self.cap.read() 
            if not success: 
                print("[STREAM] Frame dropped. Retrying...") 
                time.sleep(0.1) 
                continue 
             
            # MediaPipe requires RGB images 
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) 
            results = self.hands.process(rgb_frame) 
             
            if results.multi_hand_landmarks: 
                for hand_landmarks in results.multi_hand_landmarks: 
                    h, w, _ = frame.shape 
                     
                    # 1. Get Wrist coordinates (X, Y) 
                    wrist = hand_landmarks.landmark[0] 
                    cx, cy = int(wrist.x * w), int(wrist.y * h) 
                     
                    # 2. Calculate Depth Proxy (Z) 
                    # Measure pixel distance between Wrist (0) and Middle Finger Knuckle  
                    m_knuckle = hand_landmarks.landmark[9] 
                    mx, my = int(m_knuckle.x * w), int(m_knuckle.y * h) 
                     
                    # Distance formula: sqrt((x2-x1)^2 + (y2-y1)^2) 
                    pixel_dist = math.sqrt((mx - cx)**2 + (my - cy)**2) 
                    z_depth = int(pixel_dist)  
                     
                    # Print 3D Coordinates to Terminal for your robot logic 
                    print(f"[3D TRACKING] Wrist -> X: {cx} | Y: {cy} | Z-Depth: {z_depth}") 
                     
                    # Draw skeletal framework on the frame 
                    self.mp_draw.draw_landmarks( 
                        frame,  
                        hand_landmarks,  
                        self.mp_hands.HAND_CONNECTIONS, 
                        self.mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2, 
circle_radius=2), 
                        self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2) 
                    ) 
                     
                    # Overlay 3D coordinates text near the wrist point 
                    cv2.putText(frame, f"X:{cx} Y:{cy} Z:{z_depth}", (cx + 12, cy - 12), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2) 
 
            # Heads Up Display (HUD) 
            cv2.putText(frame, "LeRobot 3D Tracking Mode", (10, 30),  
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2) 
            cv2.putText(frame, f"Time: {time.strftime('%H:%M:%S')}", (10, 460),  
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1) 
 
            # Compress the processed frame into a JPEG 
            ret, buAer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80]) 
            frame_bytes = buAer.tobytes() 
 
            # Yield the frame in standard multipart format 
            yield (b'--frame\r\n' 
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n') 
 
# Create a global instance of our camera/tracker engine 
streamer = RobotStreamer() 
 
# Basic HTML template 
HTML_TEMPLATE = """ 
<!DOCTYPE html> 
<html> 
<head> 
    <title>LeRobot 3D Vision</title> 
    <style> 
        body { background-color: #1c1c1c; color: #00A00; text-align: center; font
family: monospace; } 
        img { border: 3px solid #333; border-radius: 8px; margin-top: 20px; box
shadow: 0 4px 15px rgba(0,255,0,0.2); } 
    </style> 
</head> 
<body> 
    <h2>IMX708 3D Tracking Feed</h2> 
    <img src="{{ url_for('video_feed') }}" width="640" height="480"> 
    <p>3D Matrix Active | Check terminal for live coordinates</p> 
</body> 
</html> 
""" 
 
@app.route('/') 
def index(): 
    """Serves the main HTML page.""" 
    return render_template_string(HTML_TEMPLATE) 
 
@app.route('/video_feed') 
def video_feed(): 
    """Serves the continuous tracked JPEG stream.""" 
    return Response(streamer.generate_frames(), mimetype='multipart/x-mixed
replace; boundary=frame') 
 
if __name__ == "__main__": 
    print("\n=======================================================") 
    print("Starting Web Stream with 3D Spatial Tracking...") 
    print("To view, open a web browser on your computer and go to:") 
    print("http://192.168.0.30:5000") 
    print("=======================================================\n") 
     
    app.run(host='192.168.0.30', port=5000, threaded=True)
