import nibabel as nib
import numpy as np

# Liste des chemins vers vos deux images
paths = [
    "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/replaced_block/croped/standardized/fil_freaking_hole/combined_image.nii",
    "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/replaced_block/croped/standardized/fil_freaking_hole/combined_image_Copy.nii"
]

# Charge la première image de référence
ref_img = nib.load(paths[0])
ref_data = ref_img.get_fdata(dtype=np.float32)
affine = ref_img.affine
header = ref_img.header

# Charge les deux volumes
data_list = [ref_data]
for path in paths[1:]:
    data_list.append(nib.load(path).get_fdata(dtype=np.float32))

# Vérifie que les deux volumes ont la même shape (optionnel)
for i, dat in enumerate(data_list):
    if dat.shape != ref_data.shape:
        raise ValueError(f"L'image #{i} n'a pas la même shape que la référence.")

# Somme voxel par voxel
combined_data = np.zeros_like(ref_data, dtype=np.float32)
for dat in data_list:
    combined_data += dat

# ----- Étape : on évite d'avoir des coupes entièrement vides -----
nz = combined_data.shape[2]

# 1) On fait un premier passage de z=0 à z=nz-1 :
#    - Si on trouve une coupe vide, on la remplace par la dernière coupe non-vide rencontrée.
last_non_empty_slice = None

for z in range(nz):
    slice_sum = np.sum(combined_data[:, :, z])
    if slice_sum != 0:
        last_non_empty_slice = z
    else:
        # si la coupe est vide mais qu'on a déjà une coupe non-vide avant
        if last_non_empty_slice is not None:
            combined_data[:, :, z] = combined_data[:, :, last_non_empty_slice]

# 2) On fait un second passage de z=nz-1 à 0 :
#    - Pour traiter le cas où les premières coupes (en bas) pourraient être vides
next_non_empty_slice = None

for z in range(nz - 1, -1, -1):
    slice_sum = np.sum(combined_data[:, :, z])
    if slice_sum != 0:
        next_non_empty_slice = z
    else:
        # si la coupe est vide mais qu'on a déjà une coupe non-vide après
        if next_non_empty_slice is not None:
            combined_data[:, :, z] = combined_data[:, :, next_non_empty_slice]

# Impression de la somme par coupe (optionnel, pour contrôle)
for z in range(nz):
    print(f"Slice z={z}, sum={np.sum(combined_data[:, :, z])}")

# Sauvegarde du résultat
combined_img = nib.Nifti1Image(combined_data, affine, header)
out_path = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/replaced_block/croped/standardized/fil_freaking_hole/combined_image_merged.nii"
nib.save(combined_img, out_path)



