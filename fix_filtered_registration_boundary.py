#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
from pathlib import Path


SLICE_RE = re.compile(r"slice_(\d+)_aligned\.nii(?:\.gz)?$")


def iter_aligned_slices(root: Path) -> list[tuple[int, Path]]:
    items: list[tuple[int, Path]] = []
    for path in root.glob("slice_*_aligned.nii*"):
        match = SLICE_RE.match(path.name)
        if match:
            items.append((int(match.group(1)), path))
    return sorted(items)


def ants_registration_command(
    fixed: Path,
    moving: Path,
    result: Path,
    transform_prefix: Path,
    transform_type: str,
    sampling_rate: float,
) -> list[str]:
    transform = {
        "Translation": "Translation[0.1]",
        "Rigid": "Rigid[0.1]",
        "Affine": "Affine[0.1]",
    }[transform_type]
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
        transform,
        "--metric",
        f"Mattes[{fixed},{moving},1,32,Regular,{sampling_rate}]",
        "--convergence",
        "[100x60x30,1e-6,10]",
        "--shrink-factors",
        "8x4x2",
        "--smoothing-sigmas",
        "3x2x1vox",
    ]


def ants_apply_command(input_image: Path, reference: Path, output_image: Path, transform: Path) -> list[str]:
    return [
        "antsApplyTransforms",
        "-d",
        "2",
        "-i",
        str(input_image),
        "-r",
        str(reference),
        "-o",
        str(output_image),
        "-n",
        "Linear",
        "-t",
        str(transform),
    ]


def write_boundary_log(
    output: Path,
    corrected_indices: list[int],
    copied_indices: list[int],
    lower: int,
    upper: int,
    transform: Path,
) -> None:
    with output.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["lower_boundary", "upper_boundary", "transform"])
        writer.writerow([lower, upper, transform])
        writer.writerow([])
        writer.writerow(["original_slice_index", "action"])
        for index in corrected_indices:
            writer.writerow([index, "boundary_transform_applied"])
        for index in copied_indices:
            writer.writerow([index, "copied_unchanged"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Correct a single registration boundary by applying one ANTs transform "
            "to an entire block of already registered slices."
        )
    )
    parser.add_argument("--input-dir", type=Path, default=Path("registration_ants_affine_filtered/slices"))
    parser.add_argument("--output-dir", type=Path, default=Path("registration_ants_affine_filtered_fix134_135"))
    parser.add_argument("--lower", type=int, default=134)
    parser.add_argument("--upper", type=int, default=135)
    parser.add_argument("--side", choices=["lower", "upper"], default="lower")
    parser.add_argument("--transform-type", choices=["Translation", "Rigid", "Affine"], default="Translation")
    parser.add_argument("--sampling-rate", type=float, default=0.3)
    parser.add_argument("--itk-threads", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS", str(args.itk_threads))
    items = iter_aligned_slices(args.input_dir)
    if not items:
        raise SystemExit(f"No slice_*_aligned.nii* found in {args.input_dir}")
    by_index = dict(items)
    fixed_index = args.upper if args.side == "lower" else args.lower
    moving_index = args.lower if args.side == "lower" else args.upper
    if fixed_index not in by_index or moving_index not in by_index:
        raise SystemExit(f"Missing boundary slice(s): fixed={fixed_index}, moving={moving_index}")

    slices_dir = args.output_dir / "slices"
    transforms_dir = args.output_dir / "transforms"
    work_dir = args.output_dir / "work"
    slices_dir.mkdir(parents=True, exist_ok=True)
    transforms_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    fixed = by_index[fixed_index]
    moving = by_index[moving_index]
    boundary_result = work_dir / f"slice_{moving_index:04d}_to_{fixed_index:04d}_boundary_check.nii"
    transform_prefix = transforms_dir / f"boundary_{moving_index:04d}_to_{fixed_index:04d}_"
    transform_path = transforms_dir / f"boundary_{moving_index:04d}_to_{fixed_index:04d}_0GenericAffine.mat"

    if args.overwrite or not transform_path.exists():
        print(f"Register boundary: moving {moving_index:04d} -> fixed {fixed_index:04d}", flush=True)
        subprocess.run(
            ants_registration_command(
                fixed=fixed,
                moving=moving,
                result=boundary_result,
                transform_prefix=transform_prefix,
                transform_type=args.transform_type,
                sampling_rate=args.sampling_rate,
            ),
            check=True,
        )
    else:
        print(f"Reuse existing transform: {transform_path}", flush=True)

    corrected_indices: list[int] = []
    copied_indices: list[int] = []
    for index, input_path in items:
        output_path = slices_dir / input_path.name
        if args.side == "lower":
            should_correct = index <= args.lower
        else:
            should_correct = index >= args.upper

        if output_path.exists() and not args.overwrite:
            continue
        if should_correct:
            print(f"Apply boundary correction to slice {index:04d}", flush=True)
            subprocess.run(ants_apply_command(input_path, fixed, output_path, transform_path), check=True)
            corrected_indices.append(index)
        else:
            shutil.copyfile(input_path, output_path)
            copied_indices.append(index)

    source_order = args.input_dir.parent / "slice_order.csv"
    if source_order.exists():
        shutil.copyfile(source_order, args.output_dir / "slice_order.csv")
    write_boundary_log(
        args.output_dir / "boundary_fix_log.csv",
        corrected_indices=corrected_indices,
        copied_indices=copied_indices,
        lower=args.lower,
        upper=args.upper,
        transform=transform_path,
    )

    print(f"Done: {slices_dir}")
    print(f"Transform: {transform_path}")
    print(f"Boundary check: {boundary_result}")


if __name__ == "__main__":
    main()
