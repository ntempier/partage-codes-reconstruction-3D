
# Input folder
input_folder="/Users/nicolas.tempier/Desktop/These/photos_cryotome_H5H/101CANON"

# Output folder
output_folder="/Volumes/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/renamed_pictures"

# Create the output folder if it doesn't exist
mkdir -p "$output_folder"

# Counter for renaming
counter=1

# Loop through all files in the input folder
for file in "$input_folder"/*.JPG; do
    # Construct the new file name
    new_name=$(printf "%04d.JPG" "$counter") # 4-digit zero-padded numbering
    mv "$file" "$output_folder/$new_name"
    ((counter++))
done

echo "Renaming completed. Files are stored in $output_folder."