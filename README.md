# LeRobot SO101 Teleoperation System using Raspberry Pi 5, ROS2, Hand Tracking, and ArUco Markers

## Project Outline

This project aims to develop a system for the **LeRobot SO101 robotic arm** to follow hand movements like a wireless VR remote. The system enables seamless teleoperation using computer vision, IMU orientation tracking, and marker-based motion tracking.

---

# Project Idea & Implementation

The following components are used for teleoperation:

## Hardware Components

1. Raspberry Pi Camera Module 3  
2. Raspberry Pi 5  
3. ArUco Marker Cube (5 cm × 5 cm × 5 cm)  
4. 10-axis HiWonder IMU (Inertial Measurement Unit)  
5. LeRobot SO101 Robot Arm  

---

# Available Methods

Three different approaches can be implemented:

1. ROS2-based Teleoperation  
2. Hand Tracking using Raspberry Pi 5  
3. ArUco Marker Cube Tracking using Raspberry Pi 5  

---

# METHOD 1: ROS2 TELEOPERATION

## Overview

This method uses:

- ROS2
- MoveIt2
- MediaPipe hand tracking
- Webcam feed
- Ubuntu via dual boot or WSL

Ubuntu installation guide for WSL:

https://documentation.ubuntu.com/wsl/latest/howto/install-ubuntu-wsl2/

ROS2 installation guide for LeRobot:

https://github.com/ycheng517/lerobot-ros

---

# Step 1: Install WSL and Attach Devices

Install usbipd-win using Windows PowerShell:

```bash
winget install --interactive --exact dorssel.usbipd-win
```

List all devices:

```bash
usbipd list
```

Attach webcam to WSL:

```bash
usbipd attach --wsl --busid <BUSID>
```

Attach the LeRobot serial port similarly.

---

# Step 2: Install Required Python Libraries

Activate the virtual environment created during ROS2 setup and install:

```bash
pip install catkin_pkg empy==3.3.4 lark

pip install mediapipe opencv-python numpy scipy transforms3d

pip install rclpy geometry-msgs tf2-ros

sudo apt install ros-jazzy-pymoveit2

sudo apt install ros-jazzy-tf2-ros-py

sudo apt install ros-jazzy-tf2-ros

sudo apt install ros-jazzy-geometry-msgs

sudo apt install ros-jazzy-rclpy

sudo apt install ros-jazzy-moveit-py \
ros-jazzy-moveit-ros-planning-interface \
ros-jazzy-moveit-configs-utils

sudo apt update
```

---

# Step 3: Build Workspace

If package installation fails:

```bash
rm -rf build/pymoveit2 install/pymoveit2 log/
```

Build workspace:

```bash
cd ~/lerobot_ws

colcon build --symlink-install --packages-select pymoveit2
```

---

# Step 4: Runtime Permissions and Cleanup

```bash
killall -9 python3

sudo chmod 777 /dev/video0

sudo chmod 777 /dev/video1

sudo usermod -a -G dialout $USER

sudo usermod -a -G video $USER

ros2 daemon stop

pkill -9 -f controller_manager

pkill -9 -f spawner

pkill -9 -f ros2

sudo chmod a+rw /dev/ttyACM0
```

---

# Step 5: Launch ROS2 Teleoperation

## Terminal 1: Start Motor Driver

```bash
ros2 launch lerobot_controller so101_controller.launch.py use_sim_time:=false
```

## Terminal 2: Camera Teleoperation

```bash
python3 camera-teleop.py
```

## Terminal 3: MoveIt Bridge

```bash
python3 moveit-bridge.py
```

Run all three terminals simultaneously.

---

# METHOD 2: HAND TRACKING USING RASPBERRY PI 5

# Overview

This method uses:

- Raspberry Pi 5
- MediaPipe
- Raspberry Pi Camera Module 3
- IMU orientation tracking

MediaPipe tracks hand landmarks and estimates x, y, z coordinates. The IMU provides orientation data.

---

# Step 1: Install Python 3.12.13 using pyenv

```bash
sudo apt update

sudo apt install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev \
liblzma-dev python3-openssl git

curl https://pyenv.run | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc

echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc

echo 'eval "$(pyenv init -)"' >> ~/.bashrc

exec "$SHELL"

pyenv install 3.12.13
```

---

# Step 2: Create Project Environment

```bash
cd /path/to/project/folder

pyenv local 3.12.13

python3 -m venv myenv
```

Activate environment:

```bash
source pathTo_myenv/bin/activate
```

---

# Step 3: Install Core Libraries

```bash
sudo apt update

sudo apt install -y libgl1-mesa-glx libglib2.0-0 \
libsm6 libxext6 libxrender-dev
```

Reactivate the environment and install:

```bash
pip install opencv-contrib-python

python -c "import cv2; print(f'OpenCV Version: {cv2.__version__}')"

pip install flask

pip install mediapipe

pip install numpy

sudo apt update

sudo apt install python3-picamera2 libcap-dev -y

sudo apt install cmake

sudo apt update && sudo apt upgrade -y
```

---

# Step 4: Configure Raspberry Pi Camera

Open configuration file:

```bash
sudo nano /boot/firmware/config.txt
```

Add the following at the bottom:

```bash
# Enable IMX708 Camera Module 3
camera_auto_detect=1
dtoverlay=imx708

# Enable I2C and SPI
dtparam=i2c_arm=on
dtparam=i2c_vc=on
dtparam=spi=on

# Allocate Camera Memory
dtoverlay=vc4-kms-v3d,cma-512
```

Save and reboot:

```bash
reboot
```

---

# Step 5: Add Camera Permissions

```bash
echo 'SUBSYSTEM=="dma_heap", GROUP="video", MODE="0660"' | \
sudo tee /etc/udev/rules.d/99-raspberrypi-dma-heap.rules

sudo udevadm control --reload-rules && sudo udevadm trigger
```

Add user permissions:

```bash
sudo usermod -aG video,render,i2c $USER
```

Enable I2C modules:

```bash
echo "i2c-dev" | sudo tee -a /etc/modules

echo "i2c-bcm2835" | sudo tee -a /etc/modules
```

---

# Step 6: Install Camera Libraries

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y libcamera-tools libcamera-v4l2

sudo apt install -y \
gstreamer1.0-libcamera \
gstreamer1.0-plugins-base \
gstreamer1.0-plugins-good \
gstreamer1.0-plugins-bad \
python3-gst-1.0

sudo apt install -y python3-opencv

sudo apt install -y i2c-tools

sudo apt install -y v4l2loopback-utils
```

---

# Step 7: Fix Libcamera Version Errors

```bash
sudo ln -sf /usr/lib/aarch64-linux-gnu/libcamera.so.0.5.2 \
/usr/lib/aarch64-linux-gnu/libcamera.so.0.7

sudo ln -sf /usr/lib/aarch64-linux-gnu/libcamera-base.so.0.5.2 \
/usr/lib/aarch64-linux-gnu/libcamera-base.so.0.7

sudo ldconfig
```

---

# Step 8: Configure GStreamer

```bash
echo 'export GST_PLUGIN_PATH=/usr/lib/aarch64-linux-gnu/gstreamer-1.0' >> ~/.bashrc

source ~/.bashrc

pip install Flask
```

---

# Step 9: Run Camera Scripts

Use this format:

```bash
libcamerify python3 codeName.py
```

Test camera stream:

```bash
libcamerify python3 camera-livestream.py
```

---

# Step 10: Find Raspberry Pi IP Address

```bash
hostname -I
```

Replace:

```text
yourPi_IpAddress
```

with the actual Raspberry Pi IP address.

---

# Step 11: IMU and Hand Tracking

Before running IMU scripts, calibrate the LeRobot arm:

https://huggingface.co/docs/lerobot/so101?example=Linux

Run:

```bash
python3 imu-data-stream.py
```

Then run the hand tracking scripts.

It is recommended to recalibrate the robot before testing.

---

# METHOD 3: ArUco Marker Cube Teleoperation

# Overview

This method uses a 3D cube with ArUco markers attached to five sides.

The robot arm follows the cube motion like a puppet.

---

# Required Libraries

```bash
pip install opencv-contrib-python numpy Flask pyserial
```

---

# Step 1: Generate ChArUco Calibration Board

Use:

```text
ChArUco-board-generator.py
```

This generates the calibration board used for camera calibration.

---

# Step 2: Camera Calibration

Run:

```bash
python3 camera-calibration.py
```

Open the live stream website.

Capture 20 frames from different angles and distances.

Keep the ChArUco board flat and stationary.

After capturing:

- Click "Finish & Calibrate"
- A file named `camera_matrix.npz` will be generated

This file stores camera calibration parameters.

---

# Step 3: Generate ArUco Marker Cube

Run:

```bash
python3 marker-generator.py
```

Generated marker images will be saved automatically.

Print and attach them to a perfectly aligned 5 cm cube.

Leave one face open if needed.

---

# Step 4: Run ArUco Teleoperation

Ensure:

- `camera_matrix.npz` exists
- Correct ACM port is selected

Run:

```bash
python3 ArUco-marker-teleoperation.py
```

The robot arm will now track cube movement in real time.

---

# Recommended Project Structure

```text
project-folder/
│
├── camera-teleop.py
├── moveit-bridge.py
├── camera-livestream.py
├── imu-data-stream.py
├── camera-calibration.py
├── marker-generator.py
├── ArUco-marker-teleoperation.py
├── camera_matrix.npz
└── generated_markers/
```

---

# Final Notes

## Recommended Workflow

### ROS2 Method
Best for:
- Full robotics stack
- MoveIt integration
- Precise control
- Multi-node systems

### Hand Tracking Method
Best for:
- Lightweight setup
- Portable teleoperation
- Real-time hand interaction

### ArUco Method
Best for:
- Stable pose estimation
- Low computational overhead
- Reliable spatial tracking

---

# Important Recommendations

1. Calibrate the robot before every major test session.  
2. Use adequate lighting for MediaPipe and ArUco detection.  
3. Keep camera latency low for smoother teleoperation.  
4. Ensure ACM port names are correct before launching scripts.  
5. Use a powered USB hub if multiple devices are connected to Raspberry Pi.  

---

# Expected Output

The LeRobot SO101 arm should:

- Follow hand position and orientation
- Replicate cube movement in real time
- Support wireless teleoperation
- Operate using camera and IMU fusion
- Work with ROS2 or standalone Raspberry Pi pipelines
