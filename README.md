Project Outline:  
This project aim to develop a system for the lerobot so101 arm to follow the hand movements like a wireless VR Remote. 

Project Idea & Implementation: 

The following components can be used for seamless teleoperation:
1.  Raspberry Pi camera module 3
2. Raspberry Pi 5
3. ArUco (Augmented Reality University of Cordoba) marker Cube od size 5cm*5cm*5cm
4. 10-axis HiWonder IMU(Inertial Measurement Unit)
5. LeRobot Robot Arm SO101

There are three distinct methods in which this can be done and implemented:
1. Using ROS2 (Robot Operating System)
2. Hand tracking using Raspberry Pi 5
3. ArUco marker cube and Raspberry Pi 5

METHOD: 1. ROS2

For using ROS 2, Ubuntu Operating system is required. Any stable version can be used. Either dual boot or WSL (Windows Sub-system for Linux) can be used, for which the installation guide can be found here. After installing WSL or dual booting your system, required version of ROS2 can be downloaded, whose installation guide can be found here.  

After installing WSL, the webcamera should be integrated with the WSL for video feed. Install usbipd-win on windows powershell using following command:
 
winget install --interactive --exact dorssel.usbipd-win 

Now, enter the following command to list all the devices: 

usbipd list 

Here, the camera used in the USB2.0 HD UVC WebCam from the laptop. Before attaching any device to the WSL, keep the WSL running in another terminal. To attach the camera to the WSL, run the following command: 

usbipd attach --wsl --busid <BUSID> 

Attach the port, to which lerobot is connected, to the WSL in similar way.  

After installing all the required softwares and tools, proceed to install the libraries required, whose process is given below.  Then after installing ROS2 open the virtual environment that you create (The virtual environment will be created while following the installation guide for ROS2) and install the following libraries: 

pip install catkin_pkg empy==3.3.4 lark 
pip install mediapipe opencv-python numpy scipy transforms3d 
pip install rclpy geometry-msgs tf2-ros 
sudo apt install ros-jazzy-pymoveit2 
sudo apt install ros-jazzy-tf2-ros-py 
sudo apt install ros-jazzy-tf2-ros 
sudo apt install ros-jazzy-geometry-msgs 
sudo apt install ros-jazzy-rclpy 
sudo apt install ros-jazzy-moveit-py ros-jazzy-moveit-ros-planning-interface rosjazzy-moveit-configs-utils 
sudo apt update 

Then build workspace by running the following command, note that the directory where the virtual environment was saved might be different than the directory used here, hence change the directory accordingly.  
 
# While installing packages below, if the package fails then use the command 
attached here to remove the broken packages. 
 
Cmd: rm -rf build/pymoveit2 install/pymoveit2 log/ 
 
# Installation of packages 
cd ~/lerobot_ws  
colcon build --symlink-install --packages-select pymoveit2 
 
To control the robot arm, save the code in a python file named “moveit-bridge.py”. Note that the name of the file can be changed. 

Now the setup is completed and the environment and code is ready to run. Run the command below to give permission and kill unnecessary background processes in order to run the code. 
 
# kill all other process 
#kill all python  
killall -9 python3 
 
#give permission 
sudo chmod 777 /dev/video0 
 
# If you have video1, run this too: 
sudo chmod 777 /dev/video1 
sudo usermod -a -G dialout $USER 
sudo usermod -a -G video $USER 
# Stop the ROS 2 background daemon 
ros2 daemon stop 
# Kill any lingering controller_manager or spawner processes 
pkill -9 -f controller_manager 
pkill -9 -f spawner 
pkill -9 -f ros2 

#access to acm0 port 
sudo chmod a+rw /dev/ttyACM0 

#launch physical driver in terminal 1 to start the motors  
ros2 launch lerobot_controller so101_controller.launch.py use_sim_time:=false 

#run camera teleop in terminal 2 for the teleoperation to detect the hand movements 
python3 camera-teleop.py 

#run bridge teleop in terminal 3 to get values from camera and move the robot to desired 
locations 
python3 moveit-bridge.py  # change name here if needed 

Make sure to run all these three codes in separate terminals parallelly.

METHOD: 2. Hand Tracking using Raspberry Pi 5

To use Raspberry Pi to connect and control robot arm like lerobot it is necessary to install the required python version on the Raspberry Pi. The main idea in this method is to control the robot arm using camera and palm tracking lightweight library (media pipe). Media pipe tracks the palm and dynamically calculates the x, y and z axis and updates the coordinates, while the IMU connected to Raspberry tells the orientation of the palm. 

First download any version of Raspberry Pi OS and setup the board. Then create a virtual environment for required python version. Lerobot requires any version of python 3.12.x. This document describes the steps to download python v3.12.13 in particular. 

Run the commands below to install and setup python v3.12.13: 

sudo apt update 
sudo apt install -y make build-essential libssl-dev zlib1g-dev \libbz2-dev 
libreadline-dev libsqlite3-dev wget curl llvm \ libncurses5-dev 
libncursesw5-dev xz-utils tk-dev libAi-dev liblzma-dev python3-openssl git 
curl https://pyenv.run | bash 
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc 
echo 'command -v pyenv >/dev/null || export 
PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc 
echo 'eval "$(pyenv init -)"' >> ~/.bashrc 
exec "$SHELL" 
pyenv install 3.12.13 

The below command sets the mentioned python as the default version in that directory. Hence create a new folder for the project. 
Set path as per the requirement and run the command below: 

cd /path/to/your/project/folder 
pyenv local 3.12.13 

Then create the virtual environment by running the command below: 

python3 -m venv myenv 

The virtual environment can be named anything, replace myenv with the name otherwise the default name of the environment will be myenv. After creating the virtual environment, activate the virtual environment by running the command below: 

source pathTo_myenv/bin/activate 

To confirm whether the virtual environment is active or not, the system name can be checked as it changes to the name of the virtual environment.  
After activating the environment install all the required packages and libraries by following the steps below:

sudo apt update 
sudo apt install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev 

By executing the above command, it will send you out of the virtual environment, now activate your environment again and install all the libraries using the following command.
Generally, pip install will automatically install the required version of the library, but in case if any installation for any of the libraries below fails then check the compatible version of that library with python 3.12.13 and install that specific version. 

pip install opencv-contrib-python 
python -c "import cv2; print(f'OpenCV Version: {cv2.__version__}')" 
pip install flask 
pip install mediapipe 
pip install numpy 
sudo apt update 
sudo apt install python3-picamera2 libcap-dev -y 
sudo apt install cmake 
sudo apt update && sudo apt upgrade -y 

Mediapipe requires camera and since camera cannot be accessed directly, the live feed from the camera can be streamed on local host and be accessed through the browser. In order to do these extra libraries are required. To install these libraries, follow the steps below: 

To detect the camera, we need to make changes in the configuration files, to do that run the command below and paste the changes mentioned. 

command: sudo nano /boot/firmware/config.txt 

Changes to be made in the file are below, copy paste them at the bottom of the configuration file -- 

Changes 

# Enable the IMX708 (Camera Module 3) 
camera_auto_detect=1 
dtoverlay=imx708  
# Enable I2C and SPI buses for sensors/servo drivers 
dtparam=i2c_arm=on 
dtparam=i2c_vc=on 
dtparam=spi=on 
# Allocate Memory for High-Res Camera Frames (Critical Fix for CMA BuAer Error) 
dtoverlay=vc4-kms-v3d, cma-512 

After pasting, press ctrl+o then enter then ctrl+x to save and exit. After saving and exiting reboot the board by running the following command: 

reboot 

After making changes in the configuration file, permissions are required to read from the camera through I2C and/or other protocols. To grant permissions run the following commands.

echo 'SUBSYSTEM=="dma_heap", GROUP="video", MODE="0660"' | sudo tee /etc/udev/rules.d/99-raspberrypi-dma-heap.rules 
sudo udevadm control --reload-rules && sudo udevadm trigger  

After this, user permission is required to get that run the command below: 

sudo usermod -aG video, render, i2c $USER 

Now the camera needs to be connected to I2C module in order to get the feed from the camera, run the following commands: 

echo "i2c-dev" | sudo tee -a /etc/modules 
echo "i2c-bcm2835" | sudo tee -a /etc/modules 

After giving permissions, we need libraries to access the camera, to download the libraries follow the steps below: 

sudo apt update && sudo apt upgrade -y 
sudo apt install -y libcamera-tools libcamera-v4l2 
sudo apt install -y gstreamer1.0-libcamera gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad python3-gst-1.0 
sudo apt install -y python3-opencv 
sudo apt install -y i2c-tools 
sudo apt install -y v4l2loopback-utils 

Libcamera might throw some unwanted and unexpected error stating that it cannot open shared object file when libcamerify demanded v0.7 but you have v0.5.2, symbolic links are required to resolve this issue, follow the commands below: 

sudo ln -sf /usr/lib/aarch64-linux-gnu/libcamera.so.0.5.2 /usr/lib/aarch64-linuxgnu/libcamera.so.0.7 
sudo ln -sf /usr/lib/aarch64-linux-gnu/libcamera-base.so.0.5.2 /usr/lib/aarch64linux-gnu/libcamera-base.so.0.7 
sudo ldconfig 
 
To stream from the camera, it requires an additional tool called g-stream to install follow command below: 
 
echo 'export GST_PLUGIN_PATH=/usr/lib/aarch64-linux-gnu/gstreamer-1.0' >> ~/.bashrc 
source ~/.bashrc 
 
pip install Flask 
 
After this to run any code, one can use the following format: 
 
libcamerify python3 codeName.py 
 
This way the camera uses resources from the library and streams directly. Use the camera-livestream.py code to test the live feed from the camera.

To find the IP address of Raspberry Pi, connect the board to an external monitor and by hovering the cursor on the wifi symbol on the top right corner you can find the IP address, or the code below can be run in the terminal of the Raspberry Pi to find the IP address: 

Cmd: hostname -I 

Wherever the code shows yourPi_IpAddress replace it with the IP address of the Raspberry Pi that is being used.  To check if the stream is working go to the website mentioned and reload the website multiple times to troubleshoot till the feed is live.  The code for testing and readding values from the IMU. Before running the imu-data-stream.py code, lerobot needs to be calibrated, for which the documentation can be found here.

After testing the camera and imu, Hand tracking can now be done using the given two codes. It is advised to calibrate the robot before testing the code. If lerobot is already calibrated before imu code, then this step can be skipped. The code for hand tracking is provided.

METHOD: 3. ArUco Marker Codes: 

This section aims to move the Lerobot according to the movements of the ArUco marker cube (a 3D-printed cube with ArUco markers on 5 sides). These codes for ArUco marker cube are generated using python codes which are provided in this section. 

Calibration of camera is required in order to identify the ArUco markers. For calibration, use the ChArUco (chessboard ArUco) board which can be generated by python codes. The ChArUco-board-generator.py can be used to generate the calibration board. he ArUco codes for the cube are generated by the marker-generator.py. The camera can be calibrated using the camera-calibration.py.
 
Install the following libraries before starting: 

pip install opencv-contrib-python numpy Flask pyserial 


Enter the IP address of your Raspberry Pi instead of YourPi_Ipaddress.     
                          
After running camera-calibration.py in the terminal, the live streaming site will be active. The website waits for 20 frames to be clicked. Click 20 pictures at different angles and from different distances. Remember to keep the ChArUco board on a still, flat surface like cardboard. Finish the calibration by clicking 20 different frames and click on the Finish & Calibrate button. A new file named “camera_matrix.npz” will be created in the same directory as the camera-calibration python file. 

Run marker-generator.py in the Python terminal, and it can be seen that the ArUco codes generated and saved in the same way as the marker-generating code. Paste this generated ArUco code on a 3D-printed cube or geometrically perfect cube of size 5cm*5cm*5cm. Remove the sixth side and attach the five sides on the cube.  

Save ArUco-marker-teleoperation.py in the same directory as the camera-calibration code. After running ArUco-marker-teleoperation.py code, the live stream turns active on the site. As the cube with the ArUco marker is moved, the Lerobot starts moving like a puppet. Ensure to check and update the port to which the Lerobot is connected (ACM0 for this code). 
