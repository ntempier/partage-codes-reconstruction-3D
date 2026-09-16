import os
import nibabel as nib
import numpy as np

# Répertoire des slices crop et chemin de sortie pour le volume 3D
input_dir = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/2d_cropped_nifti_slices_blockmatching"
output_file = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/3d_block_blockmatched.nii"

# Liste triée des fichiers
files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith('.nii')])
slices = []
affine = None

for file in files:
    nii_path = os.path.join(input_dir, file)
    nii = nib.load(nii_path)
    data = nii.get_fdata()
    # Si les slices sont en 3D avec une dimension singleton, on la compresse
    if data.ndim == 3 and data.shape[2] == 1:
        data = np.squeeze(data, axis=2)
    slices.append(data)
    if affine is None:
        affine = nii.affine

# Empilement des slices le long de l'axe z
volume = np.stack(slices, axis=-1)
new_nii = nib.Nifti1Image(volume, affine)
nib.save(new_nii, output_file)
