import nibabel as nib
import numpy as np
import glob
import os

# Chemin vers le dossier contenant tous les .nii.gz de slice_xxxx.nii.gz
slices_path = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/2d_raw_nifti_slices_replaced"

# Récupère et trie par ordre numérique tous les fichiers slice_XXXX.nii.gz
slice_files = sorted(glob.glob(os.path.join(slices_path, "slice_*.nii.gz")))

# On charge le premier fichier pour récupérer l'affine et vérifier la taille
first_img = nib.load(slice_files[0])
first_data = first_img.get_fdata()  # Dimensions attendues: (3900, 3100, 1)
affine = first_img.affine

# On lit et on empile toutes les tranches
all_slices = []
for f in slice_files:
    data = nib.load(f).get_fdata()  # data shape = (3900, 3100, 1)
    # On enlève la dimension 1 inutile (dernier axe), sinon on peut stacker sur axis=2
    all_slices.append(np.squeeze(data))

# On empile le long du 3e axe (z)
volume_3d = np.stack(all_slices, axis=-1)

# On crée et on enregistre le nouveau NIfTI 3D
out_img = nib.Nifti1Image(volume_3d, affine)
nib.save(out_img, "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/volume_3D.nii.gz")
