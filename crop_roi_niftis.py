import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Paramètres de crop définis par rapport au centre (demi‑dimensions en mm)
crop_dx_phys = 2000.0  # distance en mm du centre à la bordure en x
crop_dy_phys = 2400.0  # distance en mm du centre à la bordure en y

# Dossier contenant les images recalées (blockmatching)
aligned_dir = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/2d_aligned_nifti_slices_blockmatching"

# Fichiers à afficher (exemple)
files_to_display = ["0005.nii", "0100.nii", "0270.nii"]

fig, axes = plt.subplots(nrows=3, ncols=2, figsize=(10, 15))

for idx, fname in enumerate(files_to_display):
    path = os.path.join(aligned_dir, fname)
    img = nib.load(path)
    data = img.get_fdata()
    # Suppression d'une éventuelle dimension singleton
    if data.ndim == 3 and data.shape[2] == 1:
         data = np.squeeze(data, axis=2)
    affine = img.affine

    # Récupération de la taille en voxels (attention : nibabel renvoie shape=(nY, nX))
    ny, nx = data.shape
    # Calcul du centre en voxels (en considérant l'image comme 2D)
    center_vox = np.array([nx/2, ny/2, 0, 1])
    # Conversion du centre en coordonnées physiques
    center_phys = affine.dot(center_vox)
    cx, cy = center_phys[0], center_phys[1]
    
    # Définition de la région de crop en coordonnées physiques
    x_min_phys = cx - crop_dx_phys
    x_max_phys = cx + crop_dx_phys
    y_min_phys = cy - crop_dy_phys
    y_max_phys = cy + crop_dy_phys

    # Conversion en indices voxels (on fixe z=0)
    inv_affine = np.linalg.inv(affine)
    corner_min = np.array([x_min_phys, y_min_phys, 0, 1])
    corner_max = np.array([x_max_phys, y_max_phys, 0, 1])
    voxel_min = inv_affine.dot(corner_min)[:2]
    voxel_max = inv_affine.dot(corner_max)[:2]
    
    i_min = int(np.floor(min(voxel_min[0], voxel_max[0])))
    i_max = int(np.ceil(max(voxel_min[0], voxel_max[0])))
    j_min = int(np.floor(min(voxel_min[1], voxel_max[1])))
    j_max = int(np.ceil(max(voxel_min[1], voxel_max[1])))
    
    # Extraction du crop
    cropped = data[j_min:j_max, i_min:i_max]
    
    # Affichage : colonne de gauche = image originale avec rectangle, colonne de droite = image cropée
    ax_orig = axes[idx, 0]
    ax_crop = axes[idx, 1]
    
    ax_orig.imshow(data, cmap="gray")
    ax_orig.set_title(f"Original {fname}")
    rect = patches.Rectangle((i_min, j_min), i_max - i_min, j_max - j_min,
                             linewidth=2, edgecolor='r', facecolor='none')
    ax_orig.add_patch(rect)
    
    ax_crop.imshow(cropped, cmap="gray")
    ax_crop.set_title(f"Cropped {fname}\nIndices: i[{i_min}:{i_max}], j[{j_min}:{j_max}]")
    
    ax_orig.axis("off")
    ax_crop.axis("off")

plt.tight_layout()
plt.show()
