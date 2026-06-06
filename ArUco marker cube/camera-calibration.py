import cv2 
import numpy as np 
import time 
from flask import Flask, render_template_string, Response, jsonify 
 
app = Flask(__name__) 
 
class CalibrationStreamer: 
    def __init__(self): 
        print("\n[STREAM] Initializing IMX708 Camera Module 3...") 
 
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2) 
 
        if not self.cap.isOpened(): 
            raise RuntimeError("[STREAM] CRITICAL ERROR: Camera failed to open.") 
 
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640) 
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) 
        time.sleep(1.0) 
 
        # --- OPENCV 4.7+ MODERN CHARUCO SETUP --- 
        self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50) 
        self.board = cv2.aruco.CharucoBoard((5, 7), 0.038, 0.019, self.dictionary) 
 
        # In newer OpenCV, we use a dedicated CharucoDetector object 
        self.charuco_detector = cv2.aruco.CharucoDetector(self.board) 
 
        self.all_corners = [] 
        self.all_ids = [] 
        self.image_size = None 
 
        self.trigger_capture = False 
        self.flash_frames = 0 
 
        print("[STREAM] Camera Ready. Waiting for browser connection...") 
 
    def generate_frames(self): 
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8) 
        cv2.putText(blank_frame, "CAMERA SIGNAL LOST", (80, 240), 
cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3) 
        ret, blank_buAer = cv2.imencode('.jpg', blank_frame) 
        blank_bytes = blank_buAer.tobytes() 
 
        while True: 
            try: 
                success, frame = self.cap.read() 
 
                if not success or frame is None: 
                    yield (b'--frame\r\n' 
                           b'Content-Type: image/jpeg\r\n\r\n' + blank_bytes + b'\r\n') 
                    time.sleep(0.5) 
                    continue 
 
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) 
                if self.image_size is None: 
                    self.image_size = gray.shape[::-1] 
 
                # --- OPENCV 4.7+ DETECTION --- 
                # The detector handles both markers and charuco corners automatically 
                c_corners, c_ids, m_corners, m_ids = 
self.charuco_detector.detectBoard(gray) 
 
                latest_charuco_corners = None 
                latest_charuco_ids = None 
 
                # If it sees any markers, draw them 
                if m_ids is not None and len(m_ids) > 0: 
                    cv2.aruco.drawDetectedMarkers(frame, m_corners, m_ids) 
 
                    # If it successfully interpolated the checkerboard corners, draw them 
                    if c_ids is not None and len(c_ids) > 0: 
                        cv2.aruco.drawDetectedCornersCharuco(frame, c_corners, c_ids) 
                        latest_charuco_corners = c_corners 
                        latest_charuco_ids = c_ids 
 
                # Handle Web Buttons 
                if self.trigger_capture: 
                    self.trigger_capture = False 
                    if latest_charuco_corners is not None and len(latest_charuco_corners) 
> 6: 
                        self.all_corners.append(latest_charuco_corners) 
                        self.all_ids.append(latest_charuco_ids) 
                        self.flash_frames = 5 
                        print(f"[SUCCESS] Captured! Total frames: {len(self.all_corners)}") 
                    else: 
                        self.flash_frames = -5 
                        print("[FAILED] Board not visible enough.") 
 
                # Flashes 
                if self.flash_frames > 0: 
                    cv2.rectangle(frame, (0, 0), (640, 480), (0, 255, 0), 15) 
                    self.flash_frames -= 1 
                elif self.flash_frames < 0: 
                    cv2.rectangle(frame, (0, 0), (640, 480), (0, 0, 255), 15) 
                    self.flash_frames += 1 
 
                cv2.putText(frame, f"Captures Saved: {len(self.all_corners)}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2) 
 
                ret, buAer = cv2.imencode('.jpg', frame) 
                if not ret: continue 
 
                frame_bytes = buAer.tobytes() 
                yield (b'--frame\r\n' 
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n') 
 
            except Exception as e: 
                print(f"[ERROR CAUGHT] {e}") 
                time.sleep(0.1) 
                continue 
 
    def calculate_matrix(self): 
        if len(self.all_corners) < 5: 
            return {"status": "error", "msg": "Not enough frames. Need at least 15."} 
        try: 
            # --- OPENCV 4.7+ CALIBRATION MATH --- 
            obj_points = [] 
            img_points = [] 
 
            # We must map the 2D image points to the 3D board object points 
            for corners, ids in zip(self.all_corners, self.all_ids): 
                objp, imgp = self.board.matchImagePoints(corners, ids) 
                if objp is not None and len(objp) >= 4: 
                    obj_points.append(objp) 
                    img_points.append(imgp) 
 
            # Calculate the matrix using standard camera calibration 
            ret, cameraMatrix, distCoeAs, rvecs, tvecs = cv2.calibrateCamera( 
                obj_points, img_points, self.image_size, None, None 
            ) 
 
            np.savez('camera_matrix.npz', camMatrix=cameraMatrix, 
distCoef=distCoeAs) 
            print("\n================ CALIBRATION SUCCESS 
================") 
            print("cameraMatrix = np.array(\n" + repr(cameraMatrix) + "\n)") 
            print("distCoeAs = np.array(\n" + repr(distCoeAs) + "\n)") 
            print("=======================================================
\n") 
            return {"status": "success", "msg": "Calibration Complete! Check Pi 
Terminal for matrix."} 
        except Exception as e: 
            return {"status": "error", "msg": f"Math failed: {str(e)}"} 
 
streamer = CalibrationStreamer() 
 
# --- WEB DASHBOARD HTML --- 
HTML_TEMPLATE = """ 
<!DOCTYPE html> 
<html> 
<head> 
    <title>Web Calibration</title> 
    <style> 
        body { background-color: #1a1a1a; color: #00A66; text-align: center; font
family: monospace; margin: 0; padding: 20px; } 
        img { border: 3px solid #333; border-radius: 10px; margin-top: 20px; box
shadow: 0 4px 15px rgba(0,255,102,0.2); max-width: 90%; background-color: 
#000; min-width: 640px; min-height: 480px; } 
        .btn { padding: 15px 30px; margin: 10px; font-size: 18px; font-weight: bold; 
cursor: pointer; border: none; border-radius: 5px; } 
        .btn-cap { background-color: #00A66; color: #000; } 
        .btn-cap:active { background-color: #00cc55; } 
        .btn-cal { background-color: #A0055; color: #Af; } 
        #status { margin-top: 20px; font-size: 18px; color: #Af; } 
    </style> 
</head> 
<body> 
    <h2>Pi Camera Web Calibration Tool</h2> 
    <img src="/video_feed" width="640" height="480"><br> 
 
    <div> 
        <button class="btn btn-cap" onclick="capture()"> Capture Frame</button> 
        <button class="btn btn-cal" onclick="calibrate()"> Finish & 
Calibrate</button> 
    </div> 
    <div id="status">Waiting for captures... Aim for ~20 frames at diAerent 
angles.</div> 
 
    <script> 
        function capture() { 
            fetch('/capture').then(response => response.json()); 
        } 
        function calibrate() { 
            document.getElementById('status').innerText = "Calculating Matrix... 
Please wait."; 
            fetch('/calibrate').then(response => response.json()).then(data => { 
                document.getElementById('status').innerText = data.msg; 
                document.getElementById('status').style.color = data.status === 
"success" ? "#00A66" : "#A0000"; 
            }); 
        } 
    </script> 
</body> 
</html> 
""" 
 
@app.route('/') 
def index(): 
    return render_template_string(HTML_TEMPLATE) 
 
@app.route('/video_feed') 
def video_feed(): 
    return Response(streamer.generate_frames(), mimetype='multipart/x-mixed
replace; boundary=frame') 
 
@app.route('/capture') 
def capture(): 
    streamer.trigger_capture = True 
    return jsonify({"status": "requested"}) 
 
@app.route('/calibrate') 
def run_calibration(): 
    return jsonify(streamer.calculate_matrix()) 
 
if __name__ == "__main__": 
    print("\n=======================================================") 
    print("Starting Web Calibration Stream...") 
    print("http://YourPi_Ipaddress:5000") 
    print("=======================================================\n") 
    app.run(host='YourPi_Ipaddress', port=5000, threaded=True) 
