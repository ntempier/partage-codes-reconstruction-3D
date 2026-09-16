#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np


def iter_slices(root: Path) -> list[Path]:
    return sorted(p for p in root.glob("slice_*.nii*") if p.is_file())


def load_as_2d_float32(path: Path) -> np.ndarray:
    data = np.asanyarray(nib.load(path).dataobj)
    data = np.squeeze(data)
    if data.ndim != 2:
        raise ValueError(f"{path} is not a 2D/singleton-Z slice after squeeze: shape={data.shape}")
    return data.astype(np.float32, copy=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare cropped NIfTI slices as true 2D float32 images for ANTs 2D registration."
    )
    parser.add_argument("--input-dir", type=Path, default=Path("cropped_nifti_slices"))
    parser.add_argument("--output-dir", type=Path, default=Path("ants_nifti_slices"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    slices = iter_slices(args.input_dir)
    if not slices:
        raise SystemExit(f"No slice_*.nii* found in {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    affine = np.eye(4, dtype=float)

    for index, path in enumerate(slices, start=1):
        out_path = args.output_dir / path.name.replace(".nii.gz", ".nii")
        if out_path.exists() and not args.overwrite:
            continue

        data = load_as_2d_float32(path)
        image = nib.Nifti1Image(data, affine)
        image.set_data_dtype(np.float32)
        nib.save(image, out_path)

        if index == 1 or index == len(slices) or index % 25 == 0:
            print(f"Prepared {index}/{len(slices)}: {out_path}", flush=True)

    print(f"Slices: {len(slices)}")
    print(f"Output dir: {args.output_dir}")


if __name__ == "__main__":
    main()
