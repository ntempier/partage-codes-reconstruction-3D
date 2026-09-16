#!/bin/bash

# Dossier d'images d'entrée (slices non recalées)
INDIR="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/2d_raw_nifti_slices"

# Dossier de sortie pour les images recalées avec ANTs
OUTDIR="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/ants"

mkdir -p "$OUTDIR"

# On copie la première coupe comme point de départ (ref initiale)
cp "${INDIR}/0001.nii" "${OUTDIR}/0001.nii"

# Boucle sur les couples (i, i+1)
# On va jusqu'à 324 pour recaler la 325e
for i in $(seq -f %04g 1 324); do
    
    j=$(printf "%04d" $((10#$i + 1)))   # prochain index (zéro-pad sur 4 chiffres)
    
    ref="${OUTDIR}/${i}.nii"           # référence (déjà recalée)
    mov="${INDIR}/${j}.nii"            # moving (pas encore recalée)
    outprefix="${OUTDIR}/reg_${i}to${j}_"  # préfixe pour fichiers de transfo
    
    # Registration : rigid + affine
    antsRegistration \
      --dimensionality 2 \
      --float 1 \
      --output [${outprefix},${outprefix}Warped.nii.gz,${outprefix}InverseWarped.nii.gz] \
      --interpolation Linear \
      --use-histogram-matching 0 \
      --winsorize-image-intensities [0.005,0.995] \
      --initial-moving-transform [${ref},${mov},1] \
      --transform Rigid[0.1] \
        --metric Mattes[${ref},${mov},1,32,Regular,0.3] \
        --convergence [100x50,1e-6,10] \
        --shrink-factors 4x2 \
        --smoothing-sigmas 2x1vox \
      --transform Affine[0.1] \
        --metric Mattes[${ref},${mov},1,32,Regular,0.3] \
        --convergence [100x50,1e-6,10] \
        --shrink-factors 4x2 \
        --smoothing-sigmas 2x1vox \
      --verbose

    # Application de la transformation pour obtenir l'image recalée j
    antsApplyTransforms \
      --dimensionality 2 \
      --input ${mov} \
      --reference-image ${ref} \
      --transform ${outprefix}0GenericAffine.mat \
      --interpolation Linear \
      --output ${OUTDIR}/${j}.nii

    # On a maintenant ${j}.nii dans OUTDIR, qui servira de ref pour l'itération suivante
done




#!/bin/bash

INDIR="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/2d_raw_nifti_slices"
OUTDIR="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/blockmatching"

mkdir -p "$OUTDIR"

# Copie de la première coupe
cp "${INDIR}/0001.nii" "${OUTDIR}/0001.nii"

for i in $(seq -f %04g 1 324); do
    
    j=$(printf "%04d" $((10#$i + 1)))
    
    ref="${OUTDIR}/${i}.nii"
    mov="${INDIR}/${j}.nii"
    
    # Fichiers de sortie intermédiaires
    rigid_res="${OUTDIR}/rigid_${i}to${j}.nii"
    rigid_trsf="${OUTDIR}/rigid_${i}to${j}.trsf"
    
    affine_res="${OUTDIR}/${j}.nii"       # version finale affine
    affine_trsf="${OUTDIR}/affine_${i}to${j}.trsf"

    # --- 1) Rigid ---
    blockmatching \
      -ref "$ref" \
      -flo "$mov" \
      -res "$rigid_res" \
      -res-trsf "$rigid_trsf" \
      -trsf-type rigid \
      -pyramid-lowest-level 0 \
      -pyramid-highest-level 3 \
      -block-size 8 8 1 \
      -block-spacing 8 8 1 \
      -similarity cc \
      -max-iteration 5 \
      -parallel

    # --- 2) Affine (on part de la transfo rigide comme init) ---
    blockmatching \
      -ref "$ref" \
      -flo "$rigid_res" \
      -res "$affine_res" \
      -res-trsf "$affine_trsf" \
      -trsf-type affine \
      -init-trsf "$rigid_trsf" \
      -pyramid-lowest-level 0 \
      -pyramid-highest-level 3 \
      -block-size 8 8 1 \
      -block-spacing 8 8 1 \
      -similarity cc \
      -max-iteration 5 \
      -parallel

    # "$affine_res" = ${OUTDIR}/${j}.nii est l'image recalée finale
    # On l'utilisera comme référence pour la prochaine itération
done


