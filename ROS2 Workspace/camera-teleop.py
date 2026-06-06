import rclpy 
from rclpy.node import Node 
from geometry_msgs.msg import PoseStamped 
import cv2 
import mediapipe as mp 
import math 
import threading 
import time 
 
ANCHOR_X = 0.001 
ANCHOR_Y = -0.232 
ANCHOR_Z = 0.367 
 
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
# THREADED CAMERA (Lag Elimination) 
# ========================================== 
class CameraThread: 
    def __init__(self, src=0): 
        self.cap = cv2.VideoCapture(src, cv2.CAP_V4L2) 
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG')) 
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320) 
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240) 
        self.cap.set(cv2.CAP_PROP_FPS, 15) 
 
        self.ret, self.frame = self.cap.read() 
        self.running = True 
        self.thread = threading.Thread(target=self.update, daemon=True) 
        self.thread.start() 
 
    def update(self): 
        while self.running: 
            ret, frame = self.cap.read() 
            if ret: 
                self.ret, self.frame = ret, frame 
            else: 
                time.sleep(0.1) 
            time.sleep(0.01) 
 
    def read(self): 
        if self.frame is not None: return self.ret, self.frame.copy() 
        return self.ret, self.frame 
 
    def release(self): 
        self.running = False 
        self.thread.join() 
        self.cap.release() 
 
# ========================================== 
# MAIN NODE 
# ========================================== 
class HandTrackerPuppet(Node): 
    def __init__(self): 
        super().__init__('hand_tracker_puppet') 
        self.publisher_ = self.create_publisher(PoseStamped, '/fingertip_target', 10) 
 
        self.mp_hands = mp.solutions.hands 
        self.hands = self.mp_hands.Hands(max_num_hands=1, 
model_complexity=1, min_detection_confidence=0.7, 
min_tracking_confidence=0.7) 
        self.mp_draw = mp.solutions.drawing_utils 
 
        self.cam_thread = CameraThread(0) 
        if not self.cam_thread.cap.isOpened(): 
            self.get_logger().error(" Cannot open camera.") 
            return 
 
        self.hand_origin = None 
        self.filters = [] 
 
        self.timer = self.create_timer(1.0 / 30, self.timer_callback) 
 
    def timer_callback(self): 
        ret, frame = self.cam_thread.read() 
        if not ret or frame is None: return 
 
        frame = cv2.flip(frame, 1) 
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) 
        result = self.hands.process(rgb_frame) 
        current_time = time.time() 
 
        cv2.putText(frame, "PHYSICAL RIG ACTIVE", (10, 20), 
cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2) 
 
        if result.multi_hand_landmarks: 
            hand = result.multi_hand_landmarks[0] 
            self.mp_draw.draw_landmarks(frame, hand, 
self.mp_hands.HAND_CONNECTIONS) 
 
            tip = hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP] 
            mcp = 
hand.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_MCP] 
            wrist = hand.landmark[self.mp_hands.HandLandmark.WRIST] 
            thumb = hand.landmark[self.mp_hands.HandLandmark.THUMB_TIP] 
 
            if self.hand_origin is None: 
                self.hand_origin = {'x': tip.x, 'y': tip.y, 'z': tip.z} 
                self.filters = [OneEuroFilter(current_time, 0.0, min_cutoA=0.1, beta=1.0) 
for _ in range(6)] 
                self.get_logger().info(' Hand locked! Tracking started.') 
 
            raw_dx = tip.x - self.hand_origin['x'] 
            raw_dy = tip.y - self.hand_origin['y'] 
            raw_dz = tip.z - self.hand_origin['z'] 
 
            target_pitch = math.atan2(-(tip.y - mcp.y), abs(tip.x - mcp.x)) 
            target_twist = math.atan2((mcp.x - wrist.x), -(mcp.y - wrist.y)) 
 
            palm_size = math.hypot(wrist.x - mcp.x, wrist.y - mcp.y) 
            pinch_dist = math.hypot(thumb.x - tip.x, thumb.y - tip.y) 
            gripper_ratio = ((pinch_dist / (palm_size + 0.0001)) - 0.3) / 0.9 
            raw_grip = max(0.0, min(1.0, gripper_ratio)) 
 
            raw_targets = [raw_dx, raw_dy, raw_dz, target_pitch, target_twist, raw_grip] 
            filtered_state = [0.0] * 6 
 
            for i in range(6): 
                filtered_state[i] = self.filters[i](current_time, raw_targets[i]) 
 
            self.publish_pose(filtered_state) 
 
            grip_percent = int(filtered_state[5]*100) 
            color = (0, 255, 0) if grip_percent > 10 else (0, 0, 255) 
            cv2.putText(frame, f"Gripper: {grip_percent}%", (10, 45), 
cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2) 
 
        else: 
            if self.hand_origin is not None: 
                self.get_logger().info(' Hand lost. Origin reset.') 
                self.hand_origin = None 
                self.filters = [] 
 
        cv2.imshow('Ubuntu Real-World Puppet', frame) 
        cv2.waitKey(1) 
 
    def publish_pose(self, state): 
        msg = PoseStamped() 
        msg.header.stamp = self.get_clock().now().to_msg() 
        msg.header.frame_id = 'base' 
        msg.pose.position.x = state[0] 
        msg.pose.position.y = state[1] 
        msg.pose.position.z = state[2] 
        msg.pose.orientation.x = state[3] 
        msg.pose.orientation.y = state[4] 
        msg.pose.orientation.z = state[5] 
        msg.pose.orientation.w = 1.0 
        self.publisher_.publish(msg) 
 
def main(args=None): 
    rclpy.init(args=args) 
    node = HandTrackerPuppet() 
    try: rclpy.spin(node) 
    except KeyboardInterrupt: pass 
    finally: 
        if hasattr(node, 'cam_thread'): 
            node.cam_thread.release() 
        cv2.destroyAllWindows() 
        node.destroy_node() 
        rclpy.shutdown() 
 
if __name__ == '__main__': 
    main()
