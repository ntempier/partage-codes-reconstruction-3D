#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import nibabel as nib
import numpy as np


def read_slice_order(path: Path) -> dict[int, int]:
    if not path.exists():
        return {}
    order: dict[int, int] = {}
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            order[int(row["volume_z"])] = int(row["original_slice_index"])
    return order


def slice_affine_from_volume(volume_affine: np.ndarray, z: int) -> np.ndarray:
    affine = volume_affine.copy()
    world_origin = volume_affine @ np.array([0.0, 0.0, float(z), 1.0])
    affine[:3, 3] = world_origin[:3]
    return affine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract each cryobloc z-slice as a singleton-Z NIfTI located in the 3D volume space."
    )
    parser.add_argument(
        "--volume",
        type=Path,
        default=Path("registration_ants_affine_filtered_fix135_136/final_3D/cryobloc_filtered_fix135_136_uint8.nii"),
    )
    parser.add_argument(
        "--slice-order",
        type=Path,
        default=Path("registration_ants_affine_filtered_fix135_136/final_3D/volume_slice_order.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("registration_ants_affine_filtered_fix135_136/slices_in_3D_space"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    image = nib.load(args.volume)
    if len(image.shape) != 3:
        raise SystemExit(f"Expected a 3D volume, got shape {image.shape}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    order = read_slice_order(args.slice_order)
    dataobj = image.dataobj
    dtype = image.get_data_dtype()
    metadata_path = args.output_dir / "slices_in_3D_space.csv"

    with metadata_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "volume_z",
                "original_slice_index",
                "world_x0",
                "world_y0",
                "world_z0",
                "output_file",
            ]
        )

        for z in range(image.shape[2]):
            original_index = order.get(z, z)
            output = args.output_dir / f"cryobloc_z{z:03d}_orig{original_index:03d}.nii"
            affine = slice_affine_from_volume(image.affine, z)
            if args.overwrite or not output.exists():
                data = np.asanyarray(dataobj[:, :, z])[:, :, np.newaxis].astype(dtype, copy=False)
                out_image = nib.Nifti1Image(data, affine, header=image.header.copy())
                out_image.set_data_dtype(dtype)
                out_image.header.set_data_shape(data.shape)
                nib.save(out_image, output)
            writer.writerow([z, original_index, affine[0, 3], affine[1, 3], affine[2, 3], output.name])
            if z == 0 or z == image.shape[2] - 1 or (z + 1) % 25 == 0:
                print(f"Extracted {z + 1}/{image.shape[2]}: {output}", flush=True)

    readme = args.output_dir / "README.txt"
    readme.write_text(
        "\n".join(
            [
                "Each NIfTI in this folder contains one cryobloc slice as a singleton-Z 3D image.",
                "The affine origin is shifted so voxel (0,0,0) matches the corresponding z slice in the 3D cryobloc volume.",
                f"Source volume: {args.volume}",
                f"Slice order table: {args.slice_order}",
                f"Metadata: {metadata_path}",
                "",
            ]
        )
    )

    print(f"Slices: {image.shape[2]}")
    print(f"Output dir: {args.output_dir}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
