import os
import nibabel as nib
import numpy as np
from PIL import Image

# Répertoires d'entrée et de sortie
input_dir = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/renamed_pictures_gray"
output_dir = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/2d_raw_nifti_slices"
os.makedirs(output_dir, exist_ok=True)

# Liste des fichiers .JPG triés par nom
files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith('.jpg')])
for file in files:
    print(f"Converting {file} to NIfTI...")
    img_path = os.path.join(input_dir, file)
    # Chargement et conversion en niveau de gris
    img = Image.open(img_path).convert('L')
    data = np.array(img)
    # On passe en 3D (hauteur, largeur, 1)
    data = np.expand_dims(data, axis=-1)
    # Affine identité (à adapter si nécessaire)
    affine = np.eye(4)
    nii_img = nib.Nifti1Image(data, affine)
    base = os.path.splitext(file)[0]
    nib.save(nii_img, os.path.join(output_dir, base + ".nii"))
