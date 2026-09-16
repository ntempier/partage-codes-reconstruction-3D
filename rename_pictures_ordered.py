import os
import shutil

# Dossier source contenant les images
input_folder = "/Users/nicolas.tempier/Desktop/These/photos_cryotome_H5H/101CANON"

# Dossier de destination
output_folder = "/Volumes/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/renamed_pictures"

# Crée le dossier de destination s'il n'existe pas
os.makedirs(output_folder, exist_ok=True)

# Récupérer et trier les fichiers du dossier source
files = sorted([f for f in os.listdir(input_folder) if f.lower().endswith(".jpg")])

# Renommer et copier les fichiers
for idx, file in enumerate(files, start=1):
    # Nouveau nom : 4 chiffres, zéro-padded
    new_name = f"{idx:04d}.JPG"
    
    # Chemins complets
    src_path = os.path.join(input_folder, file)
    dest_path = os.path.join(output_folder, new_name)
    
    # Copier et renommer sans métadonnées
    shutil.copy(src_path, dest_path)

print(f"Renommage terminé. Les fichiers sont stockés dans : {output_folder}")