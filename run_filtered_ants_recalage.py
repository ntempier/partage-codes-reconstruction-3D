#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import os
import re
import shutil
import subprocess
from pathlib import Path

import nibabel as nib
import numpy as np


SLICE_RE = re.compile(r"slice_(\d+)\.nii(?:\.gz)?$")


def parse_exclude(spec: str) -> set[int]:
    excluded: set[int] = set()
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            first, last = item.split("-", 1)
            start, stop = int(first), int(last)
            if start > stop:
                start, stop = stop, start
            excluded.update(range(start, stop + 1))
        else:
            excluded.add(int(item))
    return excluded


def iter_input_slices(root: Path) -> dict[int, Path]:
    slices: dict[int, Path] = {}
    for path in root.glob("slice_*.nii*"):
        match = SLICE_RE.match(path.name)
        if match:
            slices[int(match.group(1))] = path
    return slices


def load_as_2d_float32(path: Path) -> np.ndarray:
    data = np.squeeze(np.asanyarray(nib.load(path).dataobj))
    if data.ndim != 2:
        raise ValueError(f"{path} is not 2D after squeeze: shape={data.shape}")
    return data.astype(np.float32, copy=False)


def prepare_ants_inputs(source_paths: dict[int, Path], kept_indices: list[int], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    affine = np.eye(4, dtype=float)
    for position, index in enumerate(kept_indices):
        output = output_dir / f"slice_{index:04d}.nii"
        if output.exists():
            continue
        image = nib.Nifti1Image(load_as_2d_float32(source_paths[index]), affine)
        image.set_data_dtype(np.float32)
        nib.save(image, output)
        if position == 0 or position == len(kept_indices) - 1 or (position + 1) % 25 == 0:
            print(f"Prepared ANTs input {position + 1}/{len(kept_indices)}: {output}", flush=True)


def write_slice_order(path: Path, kept_indices: list[int], excluded: set[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["registered_z", "original_slice_index", "excluded"])
        for z, index in enumerate(kept_indices):
            writer.writerow([z, index, "no"])
        for index in sorted(excluded):
            writer.writerow(["", index, "yes"])


def ants_registration_command(
    fixed: Path,
    moving: Path,
    result: Path,
    transform_prefix: Path,
    sampling_rate: float,
) -> list[str]:
    return [
        "antsRegistration",
        "--dimensionality",
        "2",
        "--float",
        "1",
        "--collapse-output-transforms",
        "1",
        "--output",
        f"[{transform_prefix},{result}]",
        "--interpolation",
        "Linear",
        "--use-histogram-matching",
        "0",
        "--winsorize-image-intensities",
        "[0.005,0.995]",
        "--initial-moving-transform",
        f"[{fixed},{moving},1]",
        "--transform",
        "Rigid[0.1]",
        "--metric",
        f"Mattes[{fixed},{moving},1,32,Regular,{sampling_rate}]",
        "--convergence",
        "[80x40x20,1e-6,10]",
        "--shrink-factors",
        "8x4x2",
        "--smoothing-sigmas",
        "3x2x1vox",
        "--transform",
        "Affine[0.1]",
        "--metric",
        f"Mattes[{fixed},{moving},1,32,Regular,{sampling_rate}]",
        "--convergence",
        "[80x40x20,1e-6,10]",
        "--shrink-factors",
        "8x4x2",
        "--smoothing-sigmas",
        "3x2x1vox",
    ]


def run_pair(
    fixed: Path,
    moving: Path,
    result: Path,
    transform_prefix: Path,
    sampling_rate: float,
    overwrite: bool,
) -> None:
    if result.exists() and not overwrite:
        print(f"Skip existing: {result}", flush=True)
        return
    command = ants_registration_command(fixed, moving, result, transform_prefix, sampling_rate)
    subprocess.run(command, check=True)


def run_branch(
    direction: str,
    kept_indices: list[int],
    center_position: int,
    input_dir: Path,
    slices_dir: Path,
    transforms_dir: Path,
    sampling_rate: float,
    overwrite: bool,
) -> None:
    if direction == "ascending":
        positions = range(center_position + 1, len(kept_indices))
    elif direction == "descending":
        positions = range(center_position - 1, -1, -1)
    else:
        raise ValueError(direction)

    for pos in positions:
        current_index = kept_indices[pos]
        reference_pos = pos - 1 if direction == "ascending" else pos + 1
        reference_index = kept_indices[reference_pos]
        fixed = slices_dir / f"slice_{reference_index:04d}_aligned.nii"
        moving = input_dir / f"slice_{current_index:04d}.nii"
        result = slices_dir / f"slice_{current_index:04d}_aligned.nii"
        label = f"slice_{reference_index:04d}_to_{current_index:04d}"
        transform_prefix = transforms_dir / f"{label}_"
        print(f"==> {direction} {current_index:04d} on {reference_index:04d}", flush=True)
        run_pair(fixed, moving, result, transform_prefix, sampling_rate, overwrite)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register cropped cryobloc slices with ANTs after excluding known bad slices."
    )
    parser.add_argument("--input-dir", type=Path, default=Path("cropped_nifti_slices"))
    parser.add_argument("--output-dir", type=Path, default=Path("registration_ants_affine_filtered"))
    parser.add_argument("--exclude", default="29,271,320-324")
    parser.add_argument("--center-index", type=int, default=162)
    parser.add_argument("--sampling-rate", type=float, default=0.2)
    parser.add_argument("--itk-threads", type=int, default=8)
    parser.add_argument("--run-mode", choices=["parallel", "sequential"], default="parallel")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS", str(args.itk_threads))
    source_paths = iter_input_slices(args.input_dir)
    if not source_paths:
        raise SystemExit(f"No slice_*.nii* found in {args.input_dir}")

    excluded = parse_exclude(args.exclude)
    kept_indices = [index for index in sorted(source_paths) if index not in excluded]
    missing_excluded = sorted(index for index in excluded if index not in source_paths)
    if missing_excluded:
        print(f"Warning: excluded indices absent from input: {missing_excluded}", flush=True)
    if args.center_index not in kept_indices:
        raise SystemExit(f"Center slice {args.center_index} is excluded or absent")
    if len(kept_indices) < 2:
        raise SystemExit("Need at least two kept slices for registration")

    input_2d_dir = args.output_dir / "input_2d"
    slices_dir = args.output_dir / "slices"
    transforms_dir = args.output_dir / "transforms"
    slices_dir.mkdir(parents=True, exist_ok=True)
    transforms_dir.mkdir(parents=True, exist_ok=True)

    write_slice_order(args.output_dir / "slice_order.csv", kept_indices, excluded)
    prepare_ants_inputs(source_paths, kept_indices, input_2d_dir)

    center_input = input_2d_dir / f"slice_{args.center_index:04d}.nii"
    center_output = slices_dir / f"slice_{args.center_index:04d}_aligned.nii"
    if args.overwrite or not center_output.exists():
        shutil.copyfile(center_input, center_output)

    center_position = kept_indices.index(args.center_index)
    print(f"Input: {args.input_dir}")
    print(f"Output: {args.output_dir}")
    print(f"Excluded: {sorted(index for index in excluded if index in source_paths)}")
    print(f"Kept slices: {len(kept_indices)}")
    print(f"Center: {args.center_index:04d}")
    print("Transform: ANTs Rigid -> Affine, 2D, middle-out")

    if args.run_mode == "sequential":
        run_branch("ascending", kept_indices, center_position, input_2d_dir, slices_dir, transforms_dir, args.sampling_rate, args.overwrite)
        run_branch("descending", kept_indices, center_position, input_2d_dir, slices_dir, transforms_dir, args.sampling_rate, args.overwrite)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    run_branch,
                    "ascending",
                    kept_indices,
                    center_position,
                    input_2d_dir,
                    slices_dir,
                    transforms_dir,
                    args.sampling_rate,
                    args.overwrite,
                ),
                executor.submit(
                    run_branch,
                    "descending",
                    kept_indices,
                    center_position,
                    input_2d_dir,
                    slices_dir,
                    transforms_dir,
                    args.sampling_rate,
                    args.overwrite,
                ),
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()

    print(f"Done: {slices_dir}")


if __name__ == "__main__":
    main()
