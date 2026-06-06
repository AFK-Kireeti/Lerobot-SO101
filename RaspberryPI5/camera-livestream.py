import cv2 
import time 
from flask import Flask, render_template_string, Response 
 
# Initialize the web server 
app = Flask(__name__) 
 
class RobotStreamer: 
    def __init__(self): 
        print("[STREAM] Initializing IMX708 Camera...") 
        # Using the exact same reliable V4L2 bridge setup 
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2) 
         
        if not self.cap.isOpened(): 
            raise RuntimeError("[STREAM] CRITICAL: Camera failed to open. Did you 
use libcamerify?") 
             
        # 640x480 is the sweet spot for network streaming without lag 
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640) 
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) 
         
        print("[STREAM] Camera Ready. Waiting for browser connection...") 
 
    def generate_frames(self): 
        """Captures frames, encodes them to JPEG, and yields them to the 
network.""" 
        while True: 
            success, frame = self.cap.read() 
            if not success: 
                print("[STREAM] Frame dropped. Retrying...") 
                time.sleep(0.1) 
                continue 
             
            # Add a HUD (Heads Up Display) for your robot 
            cv2.putText(frame, "LeRobot 5-Axis Live Stream", (10, 30),  
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2) 
            cv2.putText(frame, f"Time: {time.strftime('%H:%M:%S')}", (10, 460),  
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1) 
 
            # Compress the OpenCV frame into a JPEG for web transmission 
            ret, buAer = cv2.imencode('.jpg', frame) 
            frame_bytes = buAer.tobytes() 
 
            # Yield the frame in the standard multipart streaming format 
            yield (b'--frame\r\n' 
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n') 
 
# Create a global instance of our camera 
streamer = RobotStreamer() 
 
# Basic HTML page to hold the video stream 
HTML_TEMPLATE = """ 
<!DOCTYPE html> 
<html> 
<head> 
    <title>LeRobot Vision</title> 
    <style> 
        body { background-color: #222; color: white; text-align: center; font-family: 
sans-serif; } 
        img { border: 3px solid #444; border-radius: 10px; margin-top: 20px; box
shadow: 0 4px 8px rgba(0,0,0,0.5); } 
    </style> 
</head> 
<body> 
    <h2>IMX708 Camera Stream</h2> 
    <img src="{{ url_for('video_feed') }}" width="640" height="480"> 
    <p>Live feed from Raspberry Pi 5</p> 
</body> 
</html> 
""" 
 
@app.route('/') 
def index(): 
    """Serves the main HTML page.""" 
    return render_template_string(HTML_TEMPLATE) 
 
@app.route('/video_feed') 
def video_feed(): 
    """Serves the continuous JPEG stream.""" 
    return Response(streamer.generate_frames(), mimetype='multipart/x-mixed
replace; boundary=frame') 
 
if __name__ == "__main__": 
    print("\n=======================================================") 
    print("Starting Web Stream...") 
    print("To view, open a web browser on your computer and go to:") 
    print("http://<YOUR_PI_IP_ADDRESS>:5000") 
    print("=======================================================\n") 
    # Host on 0.0.0.0 so other devices on the network can see it change to 
raspberry ip 
    app.run(host='192.168.0.30', port=5000, threaded=True) 
# Run by going to website http://yourPi_IPaddress:5000
