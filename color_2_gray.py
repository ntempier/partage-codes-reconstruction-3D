import os
from PIL import Image

input_folder = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/renamed_pictures/"
output_folder = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/renamed_pictures_gray/"

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

for filename in os.listdir(input_folder):
    if filename.endswith(".JPG") and not filename.startswith("._"):
        img_path = os.path.join(input_folder, filename)
        img = Image.open(img_path).convert("L")
        output_path = os.path.join(output_folder, filename)
        img.save(output_path)

print("Conversion to grayscale completed.")