#!/usr/bin/env bash

###############################################################################
# Chemins d'entrées / sorties
###############################################################################
IMAGE_3D="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/create_HD_cryoblock/Cryobloc_highres_raw.nii"
OUT_DIR="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/create_HD_cryoblock/recale_slice_by_slice2"

# Création des dossiers de sortie
mkdir -p "${OUT_DIR}"
mkdir -p "${OUT_DIR}/slices"
mkdir -p "${OUT_DIR}/ascending/transfos"
mkdir -p "${OUT_DIR}/ascending/slices"
mkdir -p "${OUT_DIR}/descending/transfos"
mkdir -p "${OUT_DIR}/descending/slices"
mkdir -p "${OUT_DIR}/final_3D"

###############################################################################
# 1) Extraction des coupes 2D en NIfTI (une par Z)
#    Dimensions z = 325 => indices de 0 à 324
###############################################################################
echo "=== Extraction des coupes 2D ==="
NZ=325
for ((z=0; z<${NZ}; z++)); do
  out_slice="${OUT_DIR}/slices/slice_${z}.nii"
  echo "Extrais la coupe z=${z} -> ${out_slice}"
  mrconvert "${IMAGE_3D}" -coord 2 ${z} "${out_slice}" -force -nthreads 70
done

###############################################################################
# Fonction utilitaire : recalage rigide puis affine 2D avec blockmatching
#
# Paramètres :
#   $1 = image de référence (2D)
#   $2 = image flottante (2D)
#   $3 = préfixe de sortie (chemin complet sans extension)
#
# Produit :
#   ${3}_rigid.nii  et ${3}_rigid.trsf  : recalage rigide
#   ${3}_affine.nii et ${3}_affine.trsf : recalage affine
###############################################################################
register_rigid_affine_2D () {
  local REF2D="$1"
  local FLO2D="$2"
  local OUT_PREFIX="$3"

  # 1) Recalage rigide
  blockmatching \
    -reference "${REF2D}" \
    -floating  "${FLO2D}" \
    -result    "${OUT_PREFIX}_rigid.nii" \
    -res-trsf  "${OUT_PREFIX}_rigid.trsf" \
    -transformation-type rigid2D \
    -normalisation \
    -pyramid-lowest-level 0 \
    -pyramid-highest-level 3 \
    -verbose -parallel

  # 2) Recalage affine (en prenant la transfo rigide comme init)
  blockmatching \
    -reference "${REF2D}" \
    -floating  "${FLO2D}" \
    -initial-transformation "${OUT_PREFIX}_rigid.trsf" \
    -result    "${OUT_PREFIX}_affine.nii" \
    -res-trsf  "${OUT_PREFIX}_affine.trsf" \
    -transformation-type affine2D \
    -normalisation \
    -pyramid-lowest-level 0 \
    -pyramid-highest-level 3 \
    -verbose -parallel
}

###############################################################################
# 2) Recalage ASCENDANT
#    - Slice_0 sert de référence (pas de recalage)
#    - Pour z=1 à 324 :
#         ref = slice_{z-1} ALIGNEE (ou, pour z=1, slice_0 brute)
#         flo = slice_z brute
#      => recalage rigide puis affine
#      => le résultat (après affine) sert de référence pour la suite
###############################################################################
echo "=== Recalage ASCENDANT (0 -> 1 -> 2 -> ... ) ==="
cp "${OUT_DIR}/slices/slice_0.nii" "${OUT_DIR}/ascending/slices/slice_0_aligned.nii"
for ((z=1; z<${NZ}; z++)); do
  REF="${OUT_DIR}/ascending/slices/slice_$((z-1))_aligned.nii"
  FLO="${OUT_DIR}/slices/slice_${z}.nii"
  OUT_PREFIX="${OUT_DIR}/ascending/transfos/slice_${z}"
  echo "   -> Recalage ascendant slice_${z} sur slice_$((z-1))_aligned"
  register_rigid_affine_2D "${REF}" "${FLO}" "${OUT_PREFIX}"
  cp "${OUT_PREFIX}_affine.nii" "${OUT_DIR}/ascending/slices/slice_${z}_aligned.nii"
done

###############################################################################
# 3) Recalage DESCENDANT
#    - On part de la dernière coupe alignée issue de l'ascendant.
#    - Pour z=323 à 0 :
#         ref = slice_{z+1} ALIGNEE
#         flo = slice_z ALIGNEE (issue de l'ascendant)
#      => recalage rigide puis affine
###############################################################################
echo "=== Recalage DESCENDANT (324 -> 323 -> ... -> 0) ==="
cp "${OUT_DIR}/ascending/slices/slice_$((NZ-1))_aligned.nii" \
   "${OUT_DIR}/descending/slices/slice_$((NZ-1))_aligned.nii"
for ((z=${NZ}-2; z>=0; z--)); do
  REF="${OUT_DIR}/descending/slices/slice_$((z+1))_aligned.nii"
  FLO="${OUT_DIR}/ascending/slices/slice_${z}_aligned.nii"
  OUT_PREFIX="${OUT_DIR}/descending/transfos/slice_${z}"
  echo "   -> Recalage descendant slice_${z} sur slice_$((z+1))_aligned"
  register_rigid_affine_2D "${REF}" "${FLO}" "${OUT_PREFIX}"
  cp "${OUT_PREFIX}_affine.nii" "${OUT_DIR}/descending/slices/slice_${z}_aligned.nii"
done

###############################################################################
# 4) Regrid sur une image de référence
#
# Afin de garantir que toutes les slices ont exactement la même grille,
# on reprojete (regrid) les slices descendantes sur la géométrie de la slice_0 brute.
# Pour cela, on utilise flirt avec une transformation identité.
###############################################################################
REF_IMAGE="${OUT_DIR}/slices/slice_0.nii"
IDENTITY="${OUT_DIR}/identity.mat"
cat <<EOF > "${IDENTITY}"
1 0 0 0
0 1 0 0
0 0 1 0
0 0 0 1
EOF

echo "=== Regridding des slices descendantes sur la référence ${REF_IMAGE} ==="
for slice in "${OUT_DIR}/descending/slices/"*aligned.nii; do
  base=$(basename "${slice}" .nii)
  out_regrid="${OUT_DIR}/descending/slices/${base}_regrid.nii"
  flirt -applyxfm -init "${IDENTITY}" -in "${slice}" -ref "${REF_IMAGE}" -out "${out_regrid}" -interp sinc
  mv "${out_regrid}" "${slice}"
done

###############################################################################
# 5) Reconstruction du volume 3D final
#    On rassemble les slices descendantes (regridées) dans l'ordre z=0..324.
###############################################################################
echo "=== Reconstruction du volume 3D final ==="
aligned_slices=($(ls -1v "${OUT_DIR}/descending/slices/"*aligned.nii))
fslmerge -z "${OUT_DIR}/final_3D/final_circular.nii" "${aligned_slices[@]}"

echo "Volume final reconstruit : ${OUT_DIR}/final_3D/final_circular.nii"
echo "Terminé."