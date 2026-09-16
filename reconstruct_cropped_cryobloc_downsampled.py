#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw


SLICE_RE = re.compile(r"slice_(\d+)\.nii(?:\.gz)?$")


def iter_slices(root: Path) -> list[Path]:
    paths = [p for p in root.glob("slice_*.nii*") if SLICE_RE.match(p.name)]
    return sorted(paths, key=lambda p: int(SLICE_RE.match(p.name).group(1)))  # type: ignore[union-attr]


def load_2d_uint8(path: Path) -> np.ndarray:
    data = np.squeeze(np.asanyarray(nib.load(path).dataobj))
    if data.ndim != 2:
        raise ValueError(f"{path} is not 2D after squeeze: shape={data.shape}")
    return np.clip(data, 0, 255).astype(np.uint8, copy=False)


def resize_slice(data: np.ndarray, output_shape: tuple[int, int]) -> np.ndarray:
    image = Image.fromarray(data)
    resized = image.resize((output_shape[1], output_shape[0]), Image.BILINEAR)
    return np.asarray(resized, dtype=np.uint8)


def make_slice_preview(volume: np.ndarray, output: Path, max_columns: int = 8) -> None:
    indices = np.linspace(0, volume.shape[2] - 1, min(24, volume.shape[2]), dtype=int)
    thumbs: list[Image.Image] = []
    for z in indices:
        image = Image.fromarray(volume[:, :, z])
        image.thumbnail((360, 360), Image.BILINEAR)
        canvas = Image.new("RGB", (image.width, image.height + 24), "white")
        canvas.paste(image.convert("RGB"), (0, 24))
        draw = ImageDraw.Draw(canvas)
        draw.text((6, 5), f"slice {z:04d}", fill=(0, 0, 0))
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
    image = Image.fromarray(data).convert("RGB")
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
    panels = []
    for y in y_indices:
        panels.append(panel(volume[y, :, :].T, f"x-z plane, y={y}"))
    for x in x_indices:
        panels.append(panel(volume[:, x, :].T, f"y-z plane, x={x}"))

    columns = 2
    rows = int(np.ceil(len(panels) / columns))
    cell_w = max(p.width for p in panels)
    cell_h = max(p.height for p in panels)
    montage = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    for i, item in enumerate(panels):
        montage.paste(item, ((i % columns) * cell_w, (i // columns) * cell_h))
    montage.save(output, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct a lightweight cryobloc from cropped NIfTI slices.")
    parser.add_argument("--input-dir", type=Path, default=Path("cropped_nifti_slices"))
    parser.add_argument("--output-dir", type=Path, default=Path("reconstruction_cropped_downsampled"))
    parser.add_argument("--downsample-xy", type=int, default=4)
    parser.add_argument("--output-name", default=None)
    args = parser.parse_args()

    if args.downsample_xy < 1:
        raise SystemExit("--downsample-xy must be >= 1")

    files = iter_slices(args.input_dir)
    if not files:
        raise SystemExit(f"No slice_*.nii* found in {args.input_dir}")

    first_img = nib.load(files[0])
    first = load_2d_uint8(files[0])
    output_shape_2d = (
        max(1, int(round(first.shape[0] / args.downsample_xy))),
        max(1, int(round(first.shape[1] / args.downsample_xy))),
    )
    volume = np.empty((output_shape_2d[0], output_shape_2d[1], len(files)), dtype=np.uint8)

    for z, path in enumerate(files):
        data = load_2d_uint8(path)
        if data.shape != first.shape:
            raise SystemExit(f"{path} shape {data.shape} does not match first slice shape {first.shape}")
        volume[:, :, z] = resize_slice(data, output_shape_2d)
        if z == 0 or z == len(files) - 1 or (z + 1) % 25 == 0:
            print(f"Stacked {z + 1}/{len(files)}: {path}", flush=True)

    scale0 = first.shape[0] / output_shape_2d[0]
    scale1 = first.shape[1] / output_shape_2d[1]
    affine = first_img.affine.copy()
    affine[:3, 0] *= scale0
    affine[:3, 1] *= scale1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    name = args.output_name or f"cryobloc_cropped_downsample{args.downsample_xy}.nii"
    output = args.output_dir / name
    image = nib.Nifti1Image(volume, affine)
    image.set_data_dtype(np.uint8)
    nib.save(image, output)

    slice_preview = args.output_dir / f"{output.stem}_slices_preview.jpg"
    mpr_preview = args.output_dir / f"{output.stem}_mpr_preview.jpg"
    make_slice_preview(volume, slice_preview)
    make_mpr_preview(volume, mpr_preview)

    print(f"Slices: {len(files)}")
    print(f"Input shape: {first.shape} x {len(files)}")
    print(f"Output shape: {volume.shape}")
    print(f"Voxel size xy: {scale0:.4f}, {scale1:.4f}")
    print(f"Output: {output}")
    print(f"Slice preview: {slice_preview}")
    print(f"MPR preview: {mpr_preview}")


if __name__ == "__main__":
    main()
