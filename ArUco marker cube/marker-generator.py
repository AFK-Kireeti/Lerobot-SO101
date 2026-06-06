import cv2 
import os 
import numpy as np 
 
def generate_cube_markers(): 
    # Setup directory 
    output_dir = "cube_markers" 
    os.makedirs(output_dir, exist_ok=True) 
     
    # Use the EXACT same dictionary as your Puppet Master script 
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50) 
     
    # High resolution for crisp printing 
    pixel_size = 600  
     
    print(f"Generating 6 markers for your 3.5cm cube...") 
     
    for marker_id in range(6): 
        # Generate the marker image (OpenCV 4.7+ syntax) 
        marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, 
pixel_size) 
         
        # Add a white border so you have room to cut/tape it to the cube 
        bordered_img = cv2.copyMakeBorder( 
            marker_img, 50, 50, 50, 50,  
            cv2.BORDER_CONSTANT, value=[255, 255, 255] 
        ) 
         
        filename = f"{output_dir}/marker_id_{marker_id}.png" 
        cv2.imwrite(filename, bordered_img) 
        print(f"Saved: {filename}") 
if _name_ == "_main_": 
generate_cube_markers() 
print("Done! Print these, but ENSURE your printer scaling is set to 100% (Actual 
Size).") 
print("Resize them in Word/Docs so the black square is exactly 35mm (3.5cm) 
wide before printing.")
