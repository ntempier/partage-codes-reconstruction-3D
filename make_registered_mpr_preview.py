#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw


SLICE_RE = re.compile(r"slice_(\d+)_aligned\.nii(?:\.gz)?$")


def iter_slices(root: Path) -> list[Path]:
    paths = [p for p in root.glob("slice_*_aligned.nii*") if SLICE_RE.match(p.name)]
    return sorted(paths, key=lambda p: int(SLICE_RE.match(p.name).group(1)))  # type: ignore[union-attr]


def to_uint8(data: np.ndarray) -> np.ndarray:
    return np.clip(data, 0, 255).astype(np.uint8)


def labeled_panel(data: np.ndarray, label: str, target_width: int = 980) -> Image.Image:
    image = Image.fromarray(to_uint8(data)).convert("RGB")
    ratio = target_width / image.width
    target_height = max(80, int(round(image.height * ratio)))
    image = image.resize((target_width, target_height), Image.BILINEAR)
    canvas = Image.new("RGB", (image.width, image.height + 24), "white")
    canvas.paste(image, (0, 24))
    draw = ImageDraw.Draw(canvas)
    draw.text((6, 5), label, fill=(0, 0, 0))
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="Create orthogonal x-z/y-z previews from registered 2D slices.")
    parser.add_argument("--input-dir", type=Path, default=Path("registration_ants_affine_middleout/slices"))
    parser.add_argument("--output", type=Path, default=Path("registration_ants_affine_middleout/registered_mpr_preview.jpg"))
    args = parser.parse_args()

    files = iter_slices(args.input_dir)
    if not files:
        raise SystemExit(f"No aligned slices found in {args.input_dir}")

    first = np.squeeze(np.asanyarray(nib.load(files[0]).dataobj))
    if first.ndim != 2:
        raise SystemExit(f"First slice is not 2D after squeeze: {first.shape}")
    height, width = first.shape
    y_indices = [height // 4, height // 2, (3 * height) // 4]
    x_indices = [width // 4, width // 2, (3 * width) // 4]
    xz = {y: np.zeros((len(files), width), dtype=np.float32) for y in y_indices}
    yz = {x: np.zeros((len(files), height), dtype=np.float32) for x in x_indices}

    for z, path in enumerate(files):
        data = np.squeeze(np.asanyarray(nib.load(path).dataobj))
        if data.shape != (height, width):
            raise SystemExit(f"{path} shape {data.shape} does not match {(height, width)}")
        for y in y_indices:
            xz[y][z, :] = data[y, :]
        for x in x_indices:
            yz[x][z, :] = data[:, x]

    panels: list[Image.Image] = []
    for y in y_indices:
        panels.append(labeled_panel(xz[y], f"x-z plane, y={y}"))
    for x in x_indices:
        panels.append(labeled_panel(yz[x], f"y-z plane, x={x}"))

    columns = 2
    rows = int(np.ceil(len(panels) / columns))
    cell_w = max(panel.width for panel in panels)
    cell_h = max(panel.height for panel in panels)
    montage = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    for i, panel in enumerate(panels):
        x = (i % columns) * cell_w
        y = (i // columns) * cell_h
        montage.paste(panel, (x, y))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    montage.save(args.output, quality=92)
    print(f"Slices: {len(files)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
