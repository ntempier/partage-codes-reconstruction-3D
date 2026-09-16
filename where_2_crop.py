import cv2
from matplotlib import pyplot as plt

# Path to the image
image_path = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/renamed_pictures_gray/0024.JPG"

# Read the image
image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

# Check if the image was successfully loaded
if image is None:
    print("Error: Could not load image.")
else:
    # Define the coordinates for cropping
    x1, y1 = 1500, 1400
    x2, y2 = 4600, 5300

    # Crop the image
    cropped_image = image[y1:y2, x1:x2]

    # Create a subplot with 1 row and 2 columns
    fig, axs = plt.subplots(1, 2, figsize=(20, 10))

    # Display the original image
    axs[0].imshow(image, cmap='gray')
    axs[0].axis('off')  # Hide the axis
    axs[0].set_title('Full Resolution Image')

    # Display the cropped image
    axs[1].imshow(cropped_image, cmap='gray')
    axs[1].axis('off')  # Hide the axis
    axs[1].set_title('Cropped Image')

    # Show the plot
    plt.show()