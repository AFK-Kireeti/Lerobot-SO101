import cv2 
def generate_charuco_board(): 
    # 1. Define the board properties 
    squares_x = 5  # Number of squares in the X direction 
    squares_y = 7  # Number of squares in the Y direction 
     
    # These physical measurements don't matter for generating the image,  
    # but you will need these exact numbers for your calibration script later. 
    square_length = 0.04  # 40mm squares 
    marker_length = 0.03  # 30mm markers 
     
    # Use a standard 5x5 dictionary for the board (doesn't conflict with your 4x4 
cube) 
    board_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100) 
     
    # 2. Create the ChArUco board object (OpenCV 4.7+ syntax) 
    board = cv2.aruco.CharucoBoard( 
        (squares_x, squares_y),  
        square_length,  
        marker_length,  
        board_dict 
    ) 
     
    # 3. Generate the image  
    # (Width, Height) in pixels. Keep the ratio matching your X/Y squares to avoid 
stretching. 
    image_size = (1000, 1400)  
    board_image = board.generateImage(image_size) 
     
    # 4. Save it 
    cv2.imwrite("charuco_calibration_board.png", board_image) 
    print("Saved 'charuco_calibration_board.png'.") 
    print("Print this on thick, matte A4 paper. Do not let the paper bend or warp 
during calibration!") 
 
if _name_ == "_main_": 
    generate_charuco_board() 
