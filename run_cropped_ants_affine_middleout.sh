#!/usr/bin/env bash
set -euo pipefail

INDIR="${INDIR:-ants_nifti_slices}"
OUTDIR="${OUTDIR:-registration_ants_affine_middleout}"
START_INDEX="${START_INDEX:-0}"
END_INDEX="${END_INDEX:-324}"
CENTER_INDEX="${CENTER_INDEX:-162}"
SAMPLING_RATE="${SAMPLING_RATE:-0.2}"
RUN_MODE="${RUN_MODE:-parallel}"
ITK_THREADS="${ITK_THREADS:-8}"
export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS="${ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS:-${ITK_THREADS}}"

mkdir -p "${OUTDIR}/slices"
mkdir -p "${OUTDIR}/transforms"

register_ants_rigid_affine_2d() {
  local ref="$1"
  local mov="$2"
  local res="$3"
  local label="$4"
  local prefix="${OUTDIR}/transforms/${label}_"

  antsRegistration \
    --dimensionality 2 \
    --float 1 \
    --collapse-output-transforms 1 \
    --output ["${prefix}","${res}"] \
    --interpolation Linear \
    --use-histogram-matching 0 \
    --winsorize-image-intensities [0.005,0.995] \
    --initial-moving-transform ["${ref}","${mov}",1] \
    --transform Rigid[0.1] \
    --metric Mattes["${ref}","${mov}",1,32,Regular,"${SAMPLING_RATE}"] \
    --convergence [80x40x20,1e-6,10] \
    --shrink-factors 8x4x2 \
    --smoothing-sigmas 3x2x1vox \
    --transform Affine[0.1] \
    --metric Mattes["${ref}","${mov}",1,32,Regular,"${SAMPLING_RATE}"] \
    --convergence [80x40x20,1e-6,10] \
    --shrink-factors 8x4x2 \
    --smoothing-sigmas 3x2x1vox
}

center=$(printf "%04d" "${CENTER_INDEX}")
cp "${INDIR}/slice_${center}.nii" "${OUTDIR}/slices/slice_${center}_aligned.nii"

echo "Input: ${INDIR}"
echo "Output: ${OUTDIR}"
echo "Range: ${START_INDEX}..${END_INDEX}"
echo "Center: ${CENTER_INDEX}"
echo "Transform: ANTs Rigid -> Affine, middle-out"
echo "Sampling rate: ${SAMPLING_RATE}"
echo "Run mode: ${RUN_MODE}"
echo "ITK threads per ANTs process: ${ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS}"

run_ascending() {
  echo "=== Ascending from center ==="
  for ((z=CENTER_INDEX + 1; z<=END_INDEX; z++)); do
    prev=$(printf "%04d" "$((z - 1))")
    curr=$(printf "%04d" "${z}")
    ref="${OUTDIR}/slices/slice_${prev}_aligned.nii"
    mov="${INDIR}/slice_${curr}.nii"
    res="${OUTDIR}/slices/slice_${curr}_aligned.nii"
    label="slice_${prev}_to_${curr}"
    echo "==> ascending ${curr} on ${prev}"
    register_ants_rigid_affine_2d "${ref}" "${mov}" "${res}" "${label}"
  done
}

run_descending() {
  echo "=== Descending from center ==="
  for ((z=CENTER_INDEX - 1; z>=START_INDEX; z--)); do
    next=$(printf "%04d" "$((z + 1))")
    curr=$(printf "%04d" "${z}")
    ref="${OUTDIR}/slices/slice_${next}_aligned.nii"
    mov="${INDIR}/slice_${curr}.nii"
    res="${OUTDIR}/slices/slice_${curr}_aligned.nii"
    label="slice_${next}_to_${curr}"
    echo "==> descending ${curr} on ${next}"
    register_ants_rigid_affine_2d "${ref}" "${mov}" "${res}" "${label}"
  done
}

case "${RUN_MODE}" in
  ascending)
    run_ascending
    ;;
  descending)
    run_descending
    ;;
  sequential)
    run_ascending
    run_descending
    ;;
  parallel)
    run_ascending &
    ascending_pid=$!
    run_descending &
    descending_pid=$!

    set +e
    wait "${ascending_pid}"
    ascending_status=$?
    wait "${descending_pid}"
    descending_status=$?
    set -e

    if [[ "${ascending_status}" -ne 0 || "${descending_status}" -ne 0 ]]; then
      echo "Registration failed: ascending=${ascending_status}, descending=${descending_status}" >&2
      exit 1
    fi
    ;;
  *)
    echo "Invalid RUN_MODE=${RUN_MODE}; expected parallel, sequential, ascending, or descending" >&2
    exit 2
    ;;
esac

echo "Done: ${OUTDIR}/slices"
