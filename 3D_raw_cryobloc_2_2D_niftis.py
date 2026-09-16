import nibabel as nib
import numpy as np
import os

# Fichier NIfTI d'entrée
input_file = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/Cryobloc_highres_raw.nii.gz"

# Dossier de sortie pour les coupes
output_dir = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/2d_raw_nifti_slices"
os.makedirs(output_dir, exist_ok=True)

# Chargement de l'image
img = nib.load(input_file)
data = img.get_fdata()  # data.shape = (3900, 3100, 325)
affine = img.affine.copy()

# Pas de coupe le long de l'axe Z (3ᵉ colonne de la matrice d'affine)
z_step = affine[:3, 2]

for i in range(data.shape[2]):
    # Extraction de la coupe i (2D)
    print(f"Extraction de la coupe {i}...")
    slice_2d = data[:, :, i]
    # On la remet en 3D (3900, 3100, 1)
    slice_3d = slice_2d[..., np.newaxis]

    # Copie de l'affine d'origine
    slice_affine = affine.copy()
    # On translate l'origine en Z de i * z_step pour respecter
    # la position réelle de la coupe dans l'espace
    slice_affine[:3, 3] += i * z_step

    # Sauvegarde sous forme de NIfTI
    out_path = os.path.join(output_dir, f"slice_{i:04d}.nii.gz")
    nib.save(nib.Nifti1Image(slice_3d, slice_affine), out_path)

