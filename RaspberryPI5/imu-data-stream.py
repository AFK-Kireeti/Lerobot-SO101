import serial 
import struct 
import sys 
import time 
 
# Configuration 
SERIAL_PORT = '/dev/ttyUSB0' 
BAUD_RATE = 9600  
 
# Data storage to keep track of the "current" values 
imu_data = { 
    "accel": [0.0, 0.0, 0.0], 
    "gyro":  [0.0, 0.0, 0.0], 
    "mag":   [0.0, 0.0, 0.0], 
    "baro":  {"pres": 0, "alt": 0.0} 
} 
 
def decode_packet(data): 
    if len(data) < 11: return 
    flag = data[1] 
    payload = struct.unpack('<hhhh', data[2:10]) 
     
    if flag == 0x51: # Accelerometer 
        imu_data["accel"] = [p / 32768.0 * 16 for p in payload[:3]] 
    elif flag == 0x52: # Gyroscope 
        imu_data["gyro"] = [p / 32768.0 * 2000 for p in payload[:3]] 
    elif flag == 0x54: # Magnetometer 
        imu_data["mag"] = [payload[0], payload[1], payload[2]] 
    elif flag == 0x56: # Barometer 
        p_raw = struct.unpack('<i', data[2:6])[0] 
        h_raw = struct.unpack('<i', data[6:10])[0] 
        imu_data["baro"] = {"pres": p_raw, "alt": h_raw / 100.0} 
 
def print_dashboard(): 
    # Move cursor to top left and clear screen from that point 
    sys.stdout.write("\033[H")  
     
    output = [ 
        "=== IMU SENSOR MONITOR (USB0) ===", 
        f"ACCEL (g):  X: {imu_data['accel'][0]:>7.3f} | Y: {imu_data['accel'][1]:>7.3f} | 
Z: {imu_data['accel'][2]:>7.3f}", 
        f"GYRO (Â°/s): X: {imu_data['gyro'][0]:>7.2f} | Y: {imu_data['gyro'][1]:>7.2f} | Z: 
{imu_data['gyro'][2]:>7.2f}", 
        f"MAG (raw):  X: {imu_data['mag'][0]:>7d} | Y: {imu_data['mag'][1]:>7d} | Z: 
{imu_data['mag'][2]:>7d}", 
        f"BARO:       Pres: {imu_data['baro']['pres']:>7d} Pa | Alt: 
{imu_data['baro']['alt']:>7.2f} m", 
        "=================================", 
        "Press Ctrl+C to Exit" 
    ] 
     
    sys.stdout.write("\n".join(output) + "\n") 
    sys.stdout.flush() 
 
def main(): 
    try: 
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1) 
        # Clear screen once at the start 
        sys.stdout.write("\033[2J")  
         
        buAer = bytearray() 
        last_update = time.time() 
         
        while True: 
            if ser.in_waiting > 0: 
                buAer.extend(ser.read(ser.in_waiting)) 
                 
                while len(buAer) >= 11: 
                    if buAer[0] == 0x55: 
                        decode_packet(buAer[:11]) 
                        del buAer[:11] 
                    else: 
                        buAer.pop(0) 
             
            # Update the display roughly 10 times per second 
            if time.time() - last_update > 0.1: 
                print_dashboard() 
                last_update = time.time() 
                         
    except serial.SerialException as e: 
        print(f"\nError: {e}") 
    except KeyboardInterrupt: 
        print("\nExiting...") 
    finally: 
        if 'ser' in locals(): ser.close() 
 
if __name__ == "__main__": 
    main() 
