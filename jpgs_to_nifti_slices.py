#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def iter_images(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*")
        if p.suffix.lower() in IMAGE_EXTENSIONS and not p.name.startswith("._")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert cropped JPG slices to 2D NIfTI slices.")
    parser.add_argument("--input-dir", type=Path, default=Path("cropped_images_gray"))
    parser.add_argument("--output-dir", type=Path, default=Path("cropped_nifti_slices"))
    parser.add_argument("--start", type=int, default=0, help="Zero-based first image index.")
    parser.add_argument("--max-slices", type=int, default=None)
    parser.add_argument("--downsample", type=int, default=1)
    parser.add_argument("--voxel-size", type=float, nargs=2, default=(1.0, 1.0), metavar=("VX", "VY"))
    args = parser.parse_args()

    if args.downsample < 1:
        raise SystemExit("--downsample must be >= 1")

    files = iter_images(args.input_dir)
    if not files:
        raise SystemExit(f"No images found in {args.input_dir}")

    selected = files[args.start :]
    if args.max_slices is not None:
        selected = selected[: args.max_slices]
    if not selected:
        raise SystemExit("No images selected")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    affine = np.eye(4, dtype=float)
    affine[0, 0] = args.voxel_size[0] * args.downsample
    affine[1, 1] = args.voxel_size[1] * args.downsample

    for local_index, path in enumerate(selected):
        global_index = args.start + local_index
        with Image.open(path) as image:
            image = image.convert("L")
            if args.downsample > 1:
                target_size = (image.width // args.downsample, image.height // args.downsample)
                image = image.resize(target_size, Image.BILINEAR)
            data = np.asarray(image, dtype=np.uint8)

        # Keep the historical convention used in this project: rows, columns, singleton Z.
        data = data[:, :, np.newaxis]
        output = args.output_dir / f"slice_{global_index:04d}.nii"
        nib.save(nib.Nifti1Image(data, affine), output)
        if local_index == 0 or local_index == len(selected) - 1 or (local_index + 1) % 25 == 0:
            print(f"Converted {local_index + 1}/{len(selected)}: {output}", flush=True)

    print(f"Images: {len(selected)}")
    print(f"Output dir: {args.output_dir}")
    print(f"Downsample: {args.downsample}")


if __name__ == "__main__":
    main()
