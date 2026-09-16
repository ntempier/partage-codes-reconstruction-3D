#!/usr/bin/env bash
set -euo pipefail

INDIR="${INDIR:-cropped_nifti_slices}"
OUTDIR="${OUTDIR:-registration_blockmatching_affine_middleout}"
START_INDEX="${START_INDEX:-0}"
END_INDEX="${END_INDEX:-324}"
CENTER_INDEX="${CENTER_INDEX:-162}"
PYRAMID_LOWEST_LEVEL="${PYRAMID_LOWEST_LEVEL:-1}"
PYRAMID_HIGHEST_LEVEL="${PYRAMID_HIGHEST_LEVEL:-4}"
MAX_ITERATIONS="${MAX_ITERATIONS:-5}"
MAX_CHUNKS="${MAX_CHUNKS:-8}"

mkdir -p "${OUTDIR}/slices"
mkdir -p "${OUTDIR}/transforms/rigid"
mkdir -p "${OUTDIR}/transforms/affine"
mkdir -p "${OUTDIR}/work"

register_rigid_then_affine_2d() {
  local ref="$1"
  local flo="$2"
  local res="$3"
  local label="$4"

  local rigid_res="${OUTDIR}/work/${label}_rigid.nii"
  local rigid_trsf="${OUTDIR}/transforms/rigid/${label}_rigid2D.trsf"
  local affine_trsf="${OUTDIR}/transforms/affine/${label}_affine2D.trsf"

  blockmatching \
    -reference "${ref}" \
    -floating "${flo}" \
    -result "${rigid_res}" \
    -res-trsf "${rigid_trsf}" \
    -transformation-type rigid2D \
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

  blockmatching \
    -reference "${ref}" \
    -floating "${flo}" \
    -initial-transformation "${rigid_trsf}" \
    -result "${res}" \
    -res-trsf "${affine_trsf}" \
    -transformation-type affine2D \
    -composition-with-initial \
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

  rm -f "${rigid_res}"
}

center=$(printf "%04d" "${CENTER_INDEX}")
cp "${INDIR}/slice_${center}.nii" "${OUTDIR}/slices/slice_${center}_aligned.nii"

echo "Input: ${INDIR}"
echo "Output: ${OUTDIR}"
echo "Range: ${START_INDEX}..${END_INDEX}"
echo "Center: ${CENTER_INDEX}"
echo "Transform: rigid2D -> affine2D, middle-out"
echo "Pyramid: lowest=${PYRAMID_LOWEST_LEVEL}, highest=${PYRAMID_HIGHEST_LEVEL}"

echo "=== Ascending from center ==="
for ((z=CENTER_INDEX + 1; z<=END_INDEX; z++)); do
  prev=$(printf "%04d" "$((z - 1))")
  curr=$(printf "%04d" "${z}")
  ref="${OUTDIR}/slices/slice_${prev}_aligned.nii"
  flo="${INDIR}/slice_${curr}.nii"
  res="${OUTDIR}/slices/slice_${curr}_aligned.nii"
  label="slice_${prev}_to_${curr}"
  echo "==> ${curr} on ${prev}"
  register_rigid_then_affine_2d "${ref}" "${flo}" "${res}" "${label}"
done

echo "=== Descending from center ==="
for ((z=CENTER_INDEX - 1; z>=START_INDEX; z--)); do
  next=$(printf "%04d" "$((z + 1))")
  curr=$(printf "%04d" "${z}")
  ref="${OUTDIR}/slices/slice_${next}_aligned.nii"
  flo="${INDIR}/slice_${curr}.nii"
  res="${OUTDIR}/slices/slice_${curr}_aligned.nii"
  label="slice_${next}_to_${curr}"
  echo "==> ${curr} on ${next}"
  register_rigid_then_affine_2d "${ref}" "${flo}" "${res}" "${label}"
done

echo "Done: ${OUTDIR}/slices"
