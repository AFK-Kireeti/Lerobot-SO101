import cv2 
import time 
import math 
import serial 
import threading 
import os 
import sys 
import numpy as np 
from flask import Flask, render_template_string, Response, url_for 
# --- CONFIGURATION --- 
SERVO_PORT = '/dev/ttyACM0' #check for robot port before running 
BAUD_SERVO = 1000000 
WEB_HOST = 'YourPi_Ipaddress' 
WEB_PORT = 5000 
# DIRECTION INVERSIONS 
SHOULDER_DIR = 1 
ELBOW_DIR = 1 
BASE_DIR = 1       # RESTORED: Back to 1 so physical robot directions are 
untouched 
# SCALING MULTIPLIERS 
TRANS_SCALE = 3500 
ROT_SCALE = 8 
app = Flask(__name__) 
# ========================================== 
# 1-EURO FILTER MATH (Jitter Elimination) 
# ========================================== 
def smoothing_factor(t_e, cutoA): 
    r = 2 * math.pi * cutoA * t_e 
    return r / (r + 1) 
 
def exponential_smoothing(a, x, x_prev): 
    return a * x + (1 - a) * x_prev 
 
class OneEuroFilter: 
    def __init__(self, t0, x0, dx0=0.0, min_cutoA=0.1, beta=1.0, d_cutoA=1.0): 
        self.min_cutoA = min_cutoA 
        self.beta = beta 
        self.d_cutoA = d_cutoA 
        self.x_prev = x0 
        self.dx_prev = dx0 
        self.t_prev = t0 
 
    def __call__(self, t, x): 
        t_e = t - self.t_prev 
        if t_e <= 0: return x 
        a_d = smoothing_factor(t_e, self.d_cutoA) 
        dx = (x - self.x_prev) / t_e 
        dx_hat = exponential_smoothing(a_d, dx, self.dx_prev) 
        cutoA = self.min_cutoA + self.beta * abs(dx_hat) 
        a = smoothing_factor(t_e, cutoA) 
        x_hat = exponential_smoothing(a, x, self.x_prev) 
        self.x_prev = x_hat 
        self.dx_prev = dx_hat 
        self.t_prev = t 
        return x_hat 
 
# ========================================== 
# MAIN ROBOT SYSTEM WITH INTEGRATED ARUCO TRACKING 
# ========================================== 
class BoundedRobotSystem: 
    def __init__(self): 
        print("[LEROBOT BRIDGE] Starting Origin-Lock Engine...") 
 
        if not os.path.exists('camera_matrix.npz'): 
            print("\n[CRITICAL] 'camera_matrix.npz' not found! Please run calibration 
first.") 
            sys.exit(1) 
 
        calib_data = np.load('camera_matrix.npz') 
        self.cam_matrix = calib_data['camMatrix'] 
        self.dist_coeAs = calib_data['distCoef'] 
 
        self.frame = np.zeros((480, 820, 3), dtype=np.uint8) 
        cv2.putText(self.frame, "INITIALIZING CAMERA...", (50, 240), 
cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2) 
 
        self.running = True 
 
        self.motor_limits = { 
            1: {"min": 1110, "max": 3164}, 
            2: {"min": 55,   "max": 3175}, 
            3: {"min": 28,   "max": 4078}, 
            4: {"min": 1839, "max": 2055}, 
            5: {"min": 1031, "max": 1038}, 
            6: {"min": 2029, "max": 3495} 
        } 
 
        self.current_action = np.array([2048, 2048, 2048, 2048, 1035, 2029], 
dtype=np.int32) 
        self.motor_steps = {i: 2048 for i in range(1, 7)} 
        self.motor_steps[5] = 1035 
        self.motor_steps[6] = 2029 
 
        self.MARKER_SIZE = 0.035 
        half_size = self.MARKER_SIZE / 2.0 
        self.marker_3d_edges = np.array([ 
            [-half_size,  half_size, 0], 
            [ half_size,  half_size, 0], 
            [ half_size, -half_size, 0], 
            [-half_size, -half_size, 0] 
        ], dtype=np.float32) 
 
        self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50) 
        self.parameters = cv2.aruco.DetectorParameters() 
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters) 
 
        self.ser_servo = None 
 
    def configure_servo_safety(self): 
        if self.ser_servo is None or not self.ser_servo.is_open: return 
        print("[SAFETY] Enforcing half-speed velocity limit (500) to protect arm 
links...") 
        try: 
            for motor_id in range(1, 7): 
                reg_speed, speed_limit = 0x2E, 500 
                sp_h, sp_l = (speed_limit >> 8) & 0xFF, speed_limit & 0xFF 
                packet = bytearray([0xFF, 0xFF, motor_id, 5, 0x03, reg_speed, sp_l, sp_h]) 
                packet.append(~(sum(packet[2:]) & 0xFF) & 0xFF) 
                self.ser_servo.write(packet) 
                time.sleep(0.02) 
        except Exception: 
            pass 
 
    def send_feetech_packet(self, servo_id, target_position): 
        if self.ser_servo is None or not self.ser_servo.is_open: return 
        try: 
            target_position = max(self.motor_limits[servo_id]['min'], 
min(self.motor_limits[servo_id]['max'], int(target_position))) 
            pos_h, pos_l = (target_position >> 8) & 0xFF, target_position & 0xFF 
            packet = bytearray([0xFF, 0xFF, servo_id, 5, 0x03, 0x2A, pos_l, pos_h]) 
            packet.append(~(sum(packet[2:]) & 0xFF) & 0xFF) 
            self.ser_servo.write(packet) 
        except Exception: 
            pass 
 
    def servo_bus_writer(self): 
        initialized_safety = False 
        while self.running: 
            start_time = time.time() 
            try: 
                if self.ser_servo is None or not self.ser_servo.is_open: 
                    self.ser_servo = serial.Serial(SERVO_PORT, BAUD_SERVO, 
timeout=0.05) 
                    initialized_safety = False 
 
                if not initialized_safety: 
                    self.configure_servo_safety() 
                    initialized_safety = True 
 
                for idx in range(6): 
                    self.send_feetech_packet(idx + 1, self.current_action[idx]) 
                    time.sleep(0.001) 
 
                if self.ser_servo: self.ser_servo.flush() 
            except: 
                self.ser_servo = None 
                time.sleep(1) 
 
            elapsed = time.time() - start_time 
            time.sleep(max(0.001, 0.02 - elapsed)) 
 
    def vision_engine(self): 
        print("[STREAM] Initializing Camera...") 
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2) 
 
        if not cap.isOpened(): 
            print("[STREAM] CRITICAL: Camera failed to open.") 
            return 
 
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640) 
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) 
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
 
        cube_origin = None 
        filters = [] 
        gripper_state = 2029 
        status_text = "WAITING FOR CUBE" 
 
        while self.running: 
            try: 
                success, raw = cap.read() 
                if not success or raw is None: 
                    time.sleep(0.01) 
                    continue 
 
                # Note: 'raw' stays raw/un-flipped here so math coordinates don't break 
                h, w, _ = raw.shape 
                gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY) 
                current_time = time.time() 
 
                corners, ids, rejected = self.detector.detectMarkers(gray) 
 
                if ids is not None: 
                    status_text = f"LOCKED: ID {ids[0][0]}" 
                    cv2.aruco.drawDetectedMarkers(raw, corners, ids) 
 
                    marker_corners = corners[0][0] 
 
                    ret, rvec, tvec = cv2.solvePnP( 
                        self.marker_3d_edges, 
                        marker_corners, 
                        self.cam_matrix, 
                        self.dist_coeAs, 
                        flags=cv2.SOLVEPNP_IPPE_SQUARE 
                    ) 
 
                    if ret: 
                        cv2.drawFrameAxes(raw, self.cam_matrix, self.dist_coeAs, rvec, tvec, 
self.MARKER_SIZE) 
 
                        x = tvec[0][0] 
                        y = tvec[1][0] 
                        z = tvec[2][0] 
 
                        rmat, _ = cv2.Rodrigues(rvec) 
                        euler, _, _, _, _, _ = cv2.RQDecomp3x3(rmat) 
                        pitch, yaw, roll = euler[0], euler[1], euler[2] 
 
                        if cube_origin is None: 
                            cube_origin = {'x': x, 'y': y, 'z': z, 'pitch': pitch, 'yaw': yaw, 'roll': roll} 
                            filters = [OneEuroFilter(current_time, 0.0, min_cutoA=0.1, 
beta=1.0) for _ in range(6)] 
                            print(f" Space Origin Synchronized around ID: {ids[0][0]}") 
 
                        dx = x - cube_origin['x'] 
                        dy = y - cube_origin['y'] 
                        dz = z - cube_origin['z'] 
                        dpitch = pitch - cube_origin['pitch'] 
                        dyaw = yaw - cube_origin['yaw'] 
                        droll = roll - cube_origin['roll'] 
 
                        raw_targets = [dx, dy, dz, dpitch, dyaw, droll] 
                        filtered_state = [filters[i](current_time, raw_targets[i]) for i in range(6)] 
                        f_dx, f_dy, f_dz, f_dpitch, f_dyaw, f_droll = filtered_state 
 
                        if f_droll > 15.0: 
                            gripper_state = 2029 
                        elif f_droll < -15.0: 
                            gripper_state = 3495 
 
                        base_pos     = 2048 - int(f_dx * TRANS_SCALE * BASE_DIR) 
                        shoulder_pos = 2048 + int(f_dy * TRANS_SCALE * SHOULDER_DIR) 
                        elbow_pos    = 2048 - int(f_dz * TRANS_SCALE * ELBOW_DIR) 
                        wrist_pitch  = 2048 + int(f_dpitch * ROT_SCALE) 
                        wrist_twist  = 1035 + int(f_dyaw * ROT_SCALE) 
 
                        hud_text = f"ID: {ids[0][0]} | Z: {z*100:.1f}cm | GRIP: {'OPEN' if 
gripper_state == 2029 else 'CLOSED'}" 
                        pixel_center = (int(marker_corners[0][0]), int(marker_corners[0][1] - 
15)) 
                        cv2.putText(raw, hud_text, pixel_center, 
cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3) 
                        cv2.putText(raw, hud_text, pixel_center, 
cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1) 
 
                        m = self.motor_limits 
                        m1 = np.clip(base_pos, m[1]['min'], m[1]['max']) 
                        m2 = np.clip(shoulder_pos, m[2]['min'], m[2]['max']) 
                        m3 = np.clip(elbow_pos, m[3]['min'], m[3]['max']) 
                        m4 = np.clip(wrist_pitch, m[4]['min'], m[4]['max']) 
                        m5 = np.clip(wrist_twist, m[5]['min'], m[5]['max']) 
                        m6 = np.clip(gripper_state, m[6]['min'], m[6]['max']) 
 
                        self.current_action = np.array([m1, m2, m3, m4, m5, m6], 
dtype=np.int32) 
                else: 
                    if cube_origin is not None: 
                        print(" Tracking Link Interrupted. Purging spatial baseline cache...") 
                        cube_origin = None 
                        status_text = "CUBE LOST" 
 
                for idx in range(6): 
                    self.motor_steps[idx + 1] = self.current_action[idx] 
 
                # CHANGED: Flip the raw visualization frame ONLY right before 
outputting to the stream 
                display_frame = cv2.flip(raw, 1) 
 
                sidebar = np.zeros((h, 180, 3), dtype=np.uint8) 
                color = (0, 255, 0) if cube_origin else (0, 0, 255) 
                cv2.putText(sidebar, status_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 
0.45, color, 1) 
 
                for i in range(1, 7): 
                    cv2.putText(sidebar, f"Joint {i}: {self.motor_steps[i]}", (10, 80 + i*35), 
cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1) 
 
                self.frame = np.hstack((display_frame, sidebar)).copy() 
 
            except Exception as e: 
                print(f"[ENGINE GLITCH]: {e}") 
                continue 
 
    def generate_stream(self): 
        while self.running: 
            if self.frame is not None: 
                ret, buAer = cv2.imencode('.jpg', self.frame) 
                if ret: 
                    frame_bytes = buAer.tobytes() 
                    yield (b'--frame\r\n' 
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n') 
            time.sleep(0.01) 
 
robot = BoundedRobotSystem() 
 
# --- WEB DASHBOARD --- 
HTML_TEMPLATE = """ 
<!DOCTYPE html> 
<html> 
<head> 
    <title>SO-101 ARUCO TELEOP CENTER</title> 
    <style> 
        body { background-color: #0a0a0a; color: #00A66; text-align: center; font
family: monospace; margin: 0; padding: 20px; } 
        img { border: 2px solid #222; width: 85%; max-width: 960px; background: 
#000; box-shadow: 0px 0px 20px rgba(0,255,102,0.1); margin-top: 20px; } 
    </style> 
</head> 
<body> 
    <h2>SO-101 ARUCO CUBE WORKSPACE TELEOP (MIRRORED LIVE 
STREAM)</h2> 
    <img src="{{ url_for('video_feed') }}"> 
    <p>X/Y/Z = Spatial Control | Pitch/Yaw = Wrist adjustments | Roll Cube past 15° 
Left/Right to Close/Open Jaws</p> 
</body> 
</html> 
""" 
 
@app.route('/') 
def index(): 
    return render_template_string(HTML_TEMPLATE) 
 
@app.route('/video_feed') 
def video_feed(): 
    return Response(robot.generate_stream(), mimetype='multipart/x-mixed
replace; boundary=frame') 
 
if __name__ == "__main__": 
    print("\n=======================================================") 
    print("Starting Integrated ArUco 3D Robot Teleop Stream...") 
    print(f"Target UI Connection Link: http://{WEB_HOST}:{WEB_PORT}") 
    print("=======================================================\n") 
 
    threading.Thread(target=robot.vision_engine, daemon=True).start() 
    threading.Thread(target=robot.servo_bus_writer, daemon=True).start() 
 
    app.run(host=WEB_HOST, port=WEB_PORT, threaded=True, debug=False, 
use_reloader=False)
