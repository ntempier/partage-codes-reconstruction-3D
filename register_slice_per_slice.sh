#!/usr/bin/env bash

# Dossier contenant les slices 3D (chaque volume fait 3900x3100x1).
input_dir="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/2d_raw_nifti_slices"

# Dossier où l'on stocke les résultats de recalage.
output_dir="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/register_slices_per_slices"
mkdir -p "${output_dir}"

# Nombre total de coupes - 1 (ex: 325 coupes => de 0 à 324 => dernier index = 324)
# Ajustez si nécessaire :
nb_slices=325

# 1) On copie la première coupe telle quelle dans le dossier de sortie
#    car elle servira de référence pour le recalage des suivantes.
cp "${input_dir}/slice_0000.nii.gz" "${output_dir}/slice_0000_reg.nii.gz"

# 2) Boucle : on recale la i-ème coupe sur la (i-1)-ème coupe déjà recalée.
#    On utilise antsRegistration (ANTs) pour faire un rigid + affine, en restant
#    strictement dans le plan XY (pas de variation le long de Z).
#
#    Note : Ici on suppose que le z-dimension vaut 1, donc "dimensionality" peut
#    rester à 3, mais on force à ne pas bouger dans l'axe Z grâce à
#    --restrict-deformation 1x1x0 pour bloquer la translation/rotation en Z.
#    (ANTs > 2.4.0)
#
#    Pour chaque itération :
#    - fixed  = slice_(i-1)_reg.nii.gz
#    - moving = slice_i.nii.gz
#    - sortie = slice_i_reg.nii.gz

for (( i=1; i<nb_slices; i++ )); do
  prev_index=$(printf "%04d" $((i-1)))
  curr_index=$(printf "%04d" $i)

  fixed="${output_dir}/slice_${prev_index}_reg.nii.gz"
  moving="${input_dir}/slice_${curr_index}.nii.gz"

  out_prefix="${output_dir}/slice_${curr_index}"

  echo "==> Recalage slice_${curr_index} sur slice_${prev_index}..."

  antsRegistration \
    --dimensionality 3 \
    --float 1 \
    --output [${out_prefix},${out_prefix}_Warped.nii.gz] \
    --interpolation Linear \
    --use-histogram-matching 0 \
    --winsorize-image-intensities [0.005,0.995] \
    \
    --initial-moving-transform [${fixed},${moving},1] \
    \
    --transform Rigid[0.1] \
    --metric MI[${fixed},${moving},1,32,Regular,0.25] \
    --convergence [1000x500x250x100,1e-6,10] \
    --shrink-factors 8x4x2x1 \
    --smoothing-sigmas 3x2x1x0vox \
    \
    --transform Affine[0.1] \
    --metric MI[${fixed},${moving},1,32,Regular,0.25] \
    --convergence [1000x500x250x100,1e-6,10] \
    --shrink-factors 8x4x2x1 \
    --smoothing-sigmas 3x2x1x0vox \
    \
    --restrict-deformation 1x1x0

  # Le résultat recalé final se trouve dans out_prefix_Warped.nii.gz
  # On le renomme en slice_${curr_index}_reg.nii.gz
  mv "${out_prefix}_Warped.nii.gz" "${output_dir}/slice_${curr_index}_reg.nii.gz"

  # Les transformations rigides/affines sont dans :
  #   out_prefix0GenericAffine.mat etc.
  # Si besoin, on peut les conserver ou les supprimer.
done

echo "==> Recalage terminé. Toutes les coupes sont dans ${output_dir}."
