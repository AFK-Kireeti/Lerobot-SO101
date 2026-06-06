import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import serial
import time

class UltimateSerialPuppet(Node):
    def __init__(self):
        super().__init__('ultimate_serial_puppet')
        self.get_logger().info(' Opening serial port to metal arm...')
        try:
            self.s = serial.Serial('/dev/ttyACM0', 1000000, timeout=1)
            self.get_logger().info(' Serial connected at 1,000,000 baud!')
        except Exception as e:
            self.get_logger().error(f' Serial failed: {e}')
            return
            
        self.sub = self.create_subscription(PoseStamped, '/fingertip_target', self.pose_callback, 10)
        self.get_logger().info(' PUPPET MODE ARMED: Move your hand to control the metal!')

    def write_position(self, motor_id, position):
        pos_int = int(max(0, min(4095, position)))
        low_byte = pos_int & 0xFF
        high_byte = (pos_int >> 8) & 0xFF
        packet = [0xFF, 0xFF, motor_id, 5, 3, 0x2A, low_byte, high_byte]
        checksum = (~(sum(packet[2:]) & 0xFF)) & 0xFF
        self.s.write(bytearray(packet) + bytearray([checksum]))

    def pose_callback(self, msg):
        dx = msg.pose.position.x
        dy = msg.pose.position.y
        dz = msg.pose.position.z
        hand_pitch = msg.pose.orientation.x
        hand_twist = msg.pose.orientation.y
        gripper_ratio = msg.pose.orientation.z

        base_pos = 2048 - int(dx * 1500)
        shoulder_pos = 2048 + int(dy * 1500)
        elbow_pos = 2048 - int(dz * 2000)
        wrist_pitch = 2048 + int(hand_pitch * 800)
        wrist_twist = 2048 + int(hand_twist * 800)
        gripper_pos = 2048 - int(gripper_ratio * 1000)

        self.write_position(1, base_pos)
        self.write_position(2, shoulder_pos)
        self.write_position(3, elbow_pos)
        self.write_position(4, wrist_pitch)
        self.write_position(5, wrist_twist)
        self.write_position(6, gripper_pos)
        self.s.flush()

def main(args=None):
    rclpy.init(args=args)
    node = UltimateSerialPuppet()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(node, 's') and node.s.is_open:
            node.s.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
