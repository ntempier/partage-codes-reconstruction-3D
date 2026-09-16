#!/bin/bash

# Répertoire source et destination
INPUT_DIR="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/not_replaced_blocks_3Dslicer"
OUTPUT_DIR="${INPUT_DIR}/resampled"

# Créer le dossier de sortie s'il n'existe pas
mkdir -p "$OUTPUT_DIR"

# Liste des fichiers à traiter
FILES=(
    "0_65.nii"
    "67_287.nii"
    "288_290.nii"
    "291_301.nii"
    "302_325.nii"
    "H5H_cryobloc_bmreg_croped.nii"
)

# Boucle sur chaque fichier
for FILE in "${FILES[@]}"; do
    INPUT_FILE="${INPUT_DIR}/${FILE}"
    OUTPUT_FILE="${OUTPUT_DIR}/${FILE%.nii}_resampled.nii"

    # Vérifier si le fichier existe
    if [[ ! -f "$INPUT_FILE" ]]; then
        echo "WARNING: $INPUT_FILE not found, skipping."
        continue
    fi

    # Récupérer la profondeur (axe Z) actuelle de l'image
    Z_SIZE=$(mrinfo "$INPUT_FILE" | grep "Dimensions" | awk '{print $6}')

    echo "Processing $INPUT_FILE -> $OUTPUT_FILE with size 1140 x 876 x $Z_SIZE"

    # Application de mrgrid pour le rééchantillonnage avec la bonne profondeur
    mrgrid "$INPUT_FILE" regrid -size 1140,876,$Z_SIZE -force "$OUTPUT_FILE" -nthreads 75
done

echo "Resampling complete!"


mrgrid /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/H5H_cryobloc_bmreg_croped.nii regrid -size 1140,876,325 -force /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/not_replaced_blocks_3Dslicer/resampled/H5H_cryobloc_bmreg_croped.nii -nthreads 75
mrgrid /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/not_replaced_blocks_3Dslicer/H5H_cryobloc_bmreg_croped_slice66.nii regrid -size 1140,876,1 -force /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/not_replaced_blocks_3Dslicer/resampled/66_resampled.nii -nthreads 2


