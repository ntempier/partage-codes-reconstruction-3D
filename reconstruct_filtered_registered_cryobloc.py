#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw


SLICE_RE = re.compile(r"slice_(\d+)_aligned\.nii(?:\.gz)?$")


def iter_registered_slices(root: Path) -> list[Path]:
    paths = [p for p in root.glob("slice_*_aligned.nii*") if SLICE_RE.match(p.name)]
    return sorted(paths, key=lambda p: int(SLICE_RE.match(p.name).group(1)))  # type: ignore[union-attr]


def load_2d(path: Path) -> np.ndarray:
    data = np.squeeze(np.asanyarray(nib.load(path).dataobj))
    if data.ndim != 2:
        raise ValueError(f"{path} is not 2D after squeeze: shape={data.shape}")
    return data.astype(np.float32, copy=False)


def resize_if_needed(data: np.ndarray, downsample_xy: int) -> np.ndarray:
    if downsample_xy == 1:
        return data
    image = Image.fromarray(np.clip(data, 0, 255).astype(np.uint8))
    target = (max(1, round(data.shape[1] / downsample_xy)), max(1, round(data.shape[0] / downsample_xy)))
    return np.asarray(image.resize(target, Image.BILINEAR), dtype=np.float32)


def cast_volume(volume: np.ndarray, dtype: str) -> np.ndarray:
    if dtype == "uint8":
        return np.clip(volume, 0, 255).astype(np.uint8)
    if dtype == "float32":
        return volume.astype(np.float32, copy=False)
    raise ValueError(dtype)


def write_order(path: Path, files: list[Path]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["volume_z", "original_slice_index", "file"])
        for z, file_path in enumerate(files):
            match = SLICE_RE.match(file_path.name)
            writer.writerow([z, int(match.group(1)), file_path.name])  # type: ignore[union-attr]


def make_slice_preview(volume: np.ndarray, output: Path, max_columns: int = 8) -> None:
    indices = np.linspace(0, volume.shape[2] - 1, min(24, volume.shape[2]), dtype=int)
    thumbs: list[Image.Image] = []
    for z in indices:
        image = Image.fromarray(np.clip(volume[:, :, z], 0, 255).astype(np.uint8))
        image.thumbnail((360, 360), Image.BILINEAR)
        canvas = Image.new("RGB", (image.width, image.height + 24), "white")
        canvas.paste(image.convert("RGB"), (0, 24))
        draw = ImageDraw.Draw(canvas)
        draw.text((6, 5), f"z {z:04d}", fill=(0, 0, 0))
        thumbs.append(canvas)

    columns = min(max_columns, len(thumbs))
    rows = int(np.ceil(len(thumbs) / columns))
    cell_w = max(t.width for t in thumbs)
    cell_h = max(t.height for t in thumbs)
    montage = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    for i, thumb in enumerate(thumbs):
        montage.paste(thumb, ((i % columns) * cell_w, (i // columns) * cell_h))
    montage.save(output, quality=92)


def panel(data: np.ndarray, label: str, target_width: int = 980) -> Image.Image:
    image = Image.fromarray(np.clip(data, 0, 255).astype(np.uint8)).convert("RGB")
    ratio = target_width / image.width
    image = image.resize((target_width, max(80, int(round(image.height * ratio)))), Image.BILINEAR)
    canvas = Image.new("RGB", (image.width, image.height + 24), "white")
    canvas.paste(image, (0, 24))
    draw = ImageDraw.Draw(canvas)
    draw.text((6, 5), label, fill=(0, 0, 0))
    return canvas


def make_mpr_preview(volume: np.ndarray, output: Path) -> None:
    height, width, _ = volume.shape
    y_indices = [height // 4, height // 2, (3 * height) // 4]
    x_indices = [width // 4, width // 2, (3 * width) // 4]
    panels = [panel(volume[y, :, :].T, f"x-z plane, y={y}") for y in y_indices]
    panels.extend(panel(volume[:, x, :].T, f"y-z plane, x={x}") for x in x_indices)

    columns = 2
    rows = int(np.ceil(len(panels) / columns))
    cell_w = max(p.width for p in panels)
    cell_h = max(p.height for p in panels)
    montage = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    for i, item in enumerate(panels):
        montage.paste(item, ((i % columns) * cell_w, (i // columns) * cell_h))
    montage.save(output, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct a 3D cryobloc from filtered registered slices.")
    parser.add_argument("--input-dir", type=Path, default=Path("registration_ants_affine_filtered/slices"))
    parser.add_argument("--output-dir", type=Path, default=Path("registration_ants_affine_filtered/final_3D"))
    parser.add_argument("--output-name", default="cryobloc_filtered_registered_uint8.nii")
    parser.add_argument("--downsample-xy", type=int, default=1)
    parser.add_argument("--dtype", choices=["uint8", "float32"], default="uint8")
    parser.add_argument("--voxel-size-z", type=float, default=1.0)
    args = parser.parse_args()

    if args.downsample_xy < 1:
        raise SystemExit("--downsample-xy must be >= 1")

    files = iter_registered_slices(args.input_dir)
    if not files:
        raise SystemExit(f"No slice_*_aligned.nii* found in {args.input_dir}")

    first = resize_if_needed(load_2d(files[0]), args.downsample_xy)
    volume = np.empty((first.shape[0], first.shape[1], len(files)), dtype=np.float32)
    for z, path in enumerate(files):
        data = resize_if_needed(load_2d(path), args.downsample_xy)
        if data.shape != first.shape:
            raise SystemExit(f"{path} shape {data.shape} does not match first slice shape {first.shape}")
        volume[:, :, z] = data
        if z == 0 or z == len(files) - 1 or (z + 1) % 25 == 0:
            print(f"Stacked {z + 1}/{len(files)}: {path}", flush=True)

    output_volume = cast_volume(volume, args.dtype)
    affine = np.eye(4, dtype=float)
    affine[0, 0] = args.downsample_xy
    affine[1, 1] = args.downsample_xy
    affine[2, 2] = args.voxel_size_z

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / args.output_name
    image = nib.Nifti1Image(output_volume, affine)
    image.set_data_dtype(output_volume.dtype)
    nib.save(image, output)

    write_order(args.output_dir / "volume_slice_order.csv", files)
    slice_preview = args.output_dir / f"{output.stem}_slices_preview.jpg"
    mpr_preview = args.output_dir / f"{output.stem}_mpr_preview.jpg"
    make_slice_preview(output_volume, slice_preview)
    make_mpr_preview(output_volume, mpr_preview)

    print(f"Slices: {len(files)}")
    print(f"Output shape: {output_volume.shape}")
    print(f"Dtype: {output_volume.dtype}")
    print(f"Output: {output}")
    print(f"Slice order: {args.output_dir / 'volume_slice_order.csv'}")
    print(f"Slice preview: {slice_preview}")
    print(f"MPR preview: {mpr_preview}")


if __name__ == "__main__":
    main()
