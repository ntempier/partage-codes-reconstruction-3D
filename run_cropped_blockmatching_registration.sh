#!/usr/bin/env bash
set -euo pipefail

INDIR="${INDIR:-cropped_nifti_slices}"
OUTDIR="${OUTDIR:-registration_blockmatching_rigid}"
START_INDEX="${START_INDEX:-0}"
END_INDEX="${END_INDEX:-324}"
PYRAMID_LOWEST_LEVEL="${PYRAMID_LOWEST_LEVEL:-1}"
PYRAMID_HIGHEST_LEVEL="${PYRAMID_HIGHEST_LEVEL:-4}"
TRANSFORM_TYPE="${TRANSFORM_TYPE:-rigid2D}"
MAX_ITERATIONS="${MAX_ITERATIONS:-5}"
MAX_CHUNKS="${MAX_CHUNKS:-8}"

mkdir -p "${OUTDIR}/slices"
mkdir -p "${OUTDIR}/transforms"

first=$(printf "%04d" "${START_INDEX}")
cp "${INDIR}/slice_${first}.nii" "${OUTDIR}/slices/slice_${first}_aligned.nii"

echo "Input: ${INDIR}"
echo "Output: ${OUTDIR}"
echo "Range: ${START_INDEX}..${END_INDEX}"
echo "Transform: ${TRANSFORM_TYPE}"
echo "Pyramid: lowest=${PYRAMID_LOWEST_LEVEL}, highest=${PYRAMID_HIGHEST_LEVEL}"

for ((z=START_INDEX + 1; z<=END_INDEX; z++)); do
  prev=$(printf "%04d" "$((z - 1))")
  curr=$(printf "%04d" "${z}")

  ref="${OUTDIR}/slices/slice_${prev}_aligned.nii"
  flo="${INDIR}/slice_${curr}.nii"
  res="${OUTDIR}/slices/slice_${curr}_aligned.nii"
  trsf="${OUTDIR}/transforms/slice_${prev}_to_${curr}_${TRANSFORM_TYPE}.trsf"

  echo "==> ${curr} on ${prev}"
  blockmatching \
    -reference "${ref}" \
    -floating "${flo}" \
    -result "${res}" \
    -res-trsf "${trsf}" \
    -transformation-type "${TRANSFORM_TYPE}" \
    -normalisation \
    -pyramid-lowest-level "${PYRAMID_LOWEST_LEVEL}" \
    -pyramid-highest-level "${PYRAMID_HIGHEST_LEVEL}" \
    -block-size 16 16 1 \
    -block-spacing 16 16 1 \
    -similarity cc \
    -max-iterations "${MAX_ITERATIONS}" \
    -parallel \
    -max-chunks "${MAX_CHUNKS}" \
    -no-verbose
done

echo "Done: ${OUTDIR}/slices"
