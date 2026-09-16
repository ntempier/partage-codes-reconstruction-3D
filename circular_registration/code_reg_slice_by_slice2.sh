#!/usr/bin/env bash

###############################################################################
# Chemins d'entrée / sorties
###############################################################################
IMAGE_3D="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/create_HD_cryoblock/Cryobloc_highres_raw.nii"
OUT_DIR="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/create_HD_cryoblock/recale_slice_by_slice_no_mrtransform"

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
###############################################################################
echo "=== Extraction des coupes 2D ==="
NZ=325  # indices de 0 à 324
for ((z=0; z<${NZ}; z++)); do
  out_slice="${OUT_DIR}/slices/slice_${z}.nii"
  echo "Extraction de la coupe z=${z} -> ${out_slice}"
  mrconvert "${IMAGE_3D}" -coord 2 ${z} "${out_slice}" -force -nthreads 70
done

###############################################################################
# Fonction de recalage rigide puis affine 2D en utilisant les outputs de blockmatching
# Paramètres :
#   $1 = image de référence (2D)
#   $2 = image flottante (2D)
#   $3 = préfixe de sortie (chemin complet sans extension)
#
# Produit :
#   ${3}_rigid.nii et ${3}_rigid.trsf
#   ${3}_affine.nii et ${3}_affine.trsf
###############################################################################
register_rigid_affine_2D () {
  local REF2D="$1"
  local FLO2D="$2"
  local OUT_PREFIX="$3"

  # 1) Recalage rigide
  blockmatching \
    -reference "${REF2D}" \
    -floating "${FLO2D}" \
    -result "${OUT_PREFIX}_rigid.nii" \
    -res-trsf "${OUT_PREFIX}_rigid.trsf" \
    -transformation-type rigid2D \
    -normalisation \
    -pyramid-lowest-level 0 \
    -pyramid-highest-level 3 \
    -verbose -parallel

  # 2) Recalage affine avec composition de la transformation initiale
  blockmatching \
    -reference "${REF2D}" \
    -floating "${FLO2D}" \
    -initial-transformation "${OUT_PREFIX}_rigid.trsf" \
    -result "${OUT_PREFIX}_affine.nii" \
    -res-trsf "${OUT_PREFIX}_affine.trsf" \
    -transformation-type affine2D \
    -composition-with-initial \
    -normalisation \
    -pyramid-lowest-level 0 \
    -pyramid-highest-level 3 \
    -verbose -parallel
}

###############################################################################
# 2) Recalage ASCENDANT
#    On considère slice_0 comme référence (pas de recalage nécessaire)
###############################################################################
echo "=== Recalage ASCENDANT (0 -> 1 -> 2 -> ... ) ==="
cp "${OUT_DIR}/slices/slice_0.nii" "${OUT_DIR}/ascending/slices/slice_0_aligned.nii"

for ((z=1; z<${NZ}; z++)); do
  REF="${OUT_DIR}/ascending/slices/slice_$((z-1))_aligned.nii"
  FLO="${OUT_DIR}/slices/slice_${z}.nii"
  OUT_PREFIX="${OUT_DIR}/ascending/transfos/slice_${z}"
  echo "   -> Recalage ascendant : slice_${z} sur slice_$((z-1))_aligned"
  register_rigid_affine_2D "${REF}" "${FLO}" "${OUT_PREFIX}"
  cp "${OUT_PREFIX}_affine.nii" "${OUT_DIR}/ascending/slices/slice_${z}_aligned.nii"
done

###############################################################################
# 3) Recalage DESCENDANT
#    On part de la dernière coupe alignée issue de l'ascendant.
###############################################################################
echo "=== Recalage DESCENDANT (324 -> 323 -> ... -> 0) ==="
cp "${OUT_DIR}/ascending/slices/slice_$((NZ-1))_aligned.nii" "${OUT_DIR}/descending/slices/slice_$((NZ-1))_aligned.nii"

for ((z=${NZ}-2; z>=0; z--)); do
  REF="${OUT_DIR}/descending/slices/slice_$((z+1))_aligned.nii"
  FLO="${OUT_DIR}/ascending/slices/slice_${z}_aligned.nii"
  OUT_PREFIX="${OUT_DIR}/descending/transfos/slice_${z}"
  echo "   -> Recalage descendant : slice_${z} sur slice_$((z+1))_aligned"
  register_rigid_affine_2D "${REF}" "${FLO}" "${OUT_PREFIX}"
  cp "${OUT_PREFIX}_affine.nii" "${OUT_DIR}/descending/slices/slice_${z}_aligned.nii"
done

###############################################################################
# 4) Reconstruction du volume 3D final
#    Les slices recalées issues du recalage descendant sont empilées en Z.
###############################################################################
echo "=== Reconstruction du volume 3D final ==="
aligned_slices=($(ls -1v "${OUT_DIR}/descending/slices/"*aligned.nii))
fslmerge -z "${OUT_DIR}/final_3D/final_circular.nii" "${aligned_slices[@]}"

echo "Volume final reconstruit : ${OUT_DIR}/final_3D/final_circular.nii"
echo "Terminé."