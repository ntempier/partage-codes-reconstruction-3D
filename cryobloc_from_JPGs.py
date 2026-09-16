import os
import numpy as np
from PIL import Image
import nibabel as nib

def create_nifti_from_jpgs(input_folder, output_nifti, quality="full"):
    """
    Convertit une série d'images JPG en un volume NIfTI 3D.
    
    Paramètres :
    - input_folder : str, chemin du dossier contenant les images JPG
    - output_nifti : str, chemin du fichier NIfTI de sortie
    - quality : str, "low" pour une qualité réduite, "full" pour la pleine résolution
    """
    # Vérification du dossier d'entrée
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Le dossier spécifié n'existe pas : {input_folder}")
    
    # Liste des fichiers triés par ordre numérique
    file_list = sorted([f for f in os.listdir(input_folder) if f.endswith(".JPG") and not f.startswith("._")])
    if not file_list:
        raise ValueError("Aucune image JPG trouvée dans le dossier spécifié.")
    
    # Détermine la taille cible des images en prenant la première image
    first_image_path = os.path.join(input_folder, file_list[0])
    with Image.open(first_image_path) as first_img:
        full_size = first_img.size  # (largeur, hauteur)
    
    # Définition de la taille selon la qualité
    if quality == "low":
        target_size = (full_size[0] // 3, full_size[1] // 3)  # Réduction de 3
    else:
        target_size = full_size  # Pleine résolution
    
    # Liste pour stocker les coupes 2D
    slices = []
    
    # Chargement et traitement des images
    for filename in file_list:
        img_path = os.path.join(input_folder, filename)
        img = Image.open(img_path).convert("L")
        img_resized = img.resize(target_size)
        img_array = np.array(img_resized, dtype=np.uint8)
        slices.append(img_array)
        print(f"Image traitée : {filename}")
    
    # Empilement des coupes en un volume 3D
    volume_3d = np.stack(slices, axis=-1)
    
    # Matrice affine pour une résolution isotrope de 1 mm
    affine = np.eye(4)
    
    # Création de l'objet NIfTI
    nifti_img = nib.Nifti1Image(volume_3d, affine)
    
    # Sauvegarde du fichier NIfTI
    nib.save(nifti_img, output_nifti)
    print(f"Bloc 3D enregistré dans {output_nifti}")

# Exemple d'utilisation
create_nifti_from_jpgs("/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/2d_aligned_nifti_slices_blockmatching", "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/Cryobloc_lowres_blockmatched.nii.gz", quality="low")
