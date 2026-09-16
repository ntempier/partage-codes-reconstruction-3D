#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw


SLICE_RE = re.compile(r"slice_(\d+)_aligned\.nii(?:\.gz)?$")


def iter_aligned_slices(root: Path) -> list[Path]:
    paths = [p for p in root.glob("slice_*_aligned.nii*") if SLICE_RE.match(p.name)]
    return sorted(paths, key=lambda p: int(SLICE_RE.match(p.name).group(1)))  # type: ignore[union-attr]


def load_slice(path: Path) -> np.ndarray:
    data = np.asanyarray(nib.load(path).dataobj)
    data = np.squeeze(data)
    if data.ndim != 2:
        raise ValueError(f"{path} is not 2D after squeeze: shape={data.shape}")
    return data.astype(np.float32, copy=False)


def write_preview(samples: list[tuple[int, np.ndarray]], output: Path, max_columns: int = 8) -> None:
    if not samples:
        return

    thumbs: list[Image.Image] = []
    for idx, sample in samples:
        data = np.clip(sample, 0, 255).astype(np.uint8)
        img = Image.fromarray(data)
        img.thumbnail((360, 360), Image.BILINEAR)
        canvas = Image.new("RGB", (img.width, img.height + 24), "white")
        canvas.paste(img.convert("RGB"), (0, 24))
        draw = ImageDraw.Draw(canvas)
        draw.text((6, 5), f"slice {idx:04d}", fill=(0, 0, 0))
        thumbs.append(canvas)

    columns = min(max_columns, len(thumbs))
    rows = int(np.ceil(len(thumbs) / columns))
    cell_w = max(t.width for t in thumbs)
    cell_h = max(t.height for t in thumbs)
    montage = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    for i, thumb in enumerate(thumbs):
        x = (i % columns) * cell_w
        y = (i // columns) * cell_h
        montage.paste(thumb, (x, y))

    output.parent.mkdir(parents=True, exist_ok=True)
    montage.save(output, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stack registered 2D NIfTI slices into a 3D NIfTI volume.")
    parser.add_argument("--input-dir", type=Path, default=Path("registration_ants_affine_middleout/slices"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("registration_ants_affine_middleout/final_3D/cryobloc_cropped_ants_affine_middleout.nii.gz"),
    )
    parser.add_argument(
        "--preview",
        type=Path,
        default=Path("registration_ants_affine_middleout/registered_slices_preview.jpg"),
    )
    parser.add_argument("--work-dir", type=Path, default=None, help="Temporary directory for the volume memmap.")
    parser.add_argument("--voxel-size", type=float, nargs=3, default=(1.0, 1.0, 1.0), metavar=("VX", "VY", "VZ"))
    args = parser.parse_args()

    files = iter_aligned_slices(args.input_dir)
    if not files:
        raise SystemExit(f"No slice_*_aligned.nii* found in {args.input_dir}")

    first_slice = load_slice(files[0])
    slice_shape = first_slice.shape
    output_shape = (slice_shape[0], slice_shape[1], len(files))
    affine = np.diag([args.voxel_size[0], args.voxel_size[1], args.voxel_size[2], 1.0])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    work_dir = args.work_dir or args.output.parent
    work_dir.mkdir(parents=True, exist_ok=True)

    preview_indices = set(np.linspace(0, len(files) - 1, min(24, len(files)), dtype=int).tolist())
    preview_samples: list[tuple[int, np.ndarray]] = []

    with tempfile.NamedTemporaryFile(prefix="cryobloc_stack_", suffix=".dat", dir=work_dir, delete=False) as tmp:
        memmap_path = Path(tmp.name)

    try:
        # Fortran order makes each z-plane contiguous for fast slice-by-slice writes.
        volume = np.memmap(memmap_path, dtype=np.float32, mode="w+", shape=output_shape, order="F")
        volume[:, :, 0] = first_slice
        if 0 in preview_indices:
            preview_samples.append((0, first_slice.copy()))

        for z, path in enumerate(files[1:], start=1):
            data = load_slice(path)
            if data.shape != slice_shape:
                raise SystemExit(f"{path} shape {data.shape} does not match first slice shape {slice_shape}")
            volume[:, :, z] = data
            if z in preview_indices:
                preview_samples.append((z, data.copy()))
            if z == len(files) - 1 or (z + 1) % 25 == 0:
                print(f"Stacked {z + 1}/{len(files)}: {path}", flush=True)

        volume.flush()
        image = nib.Nifti1Image(volume, affine)
        image.set_data_dtype(np.float32)
        nib.save(image, args.output)
    finally:
        try:
            memmap_path.unlink()
        except FileNotFoundError:
            pass

    write_preview(preview_samples, args.preview)

    print(f"Slices: {len(files)}")
    print(f"Shape: {output_shape}")
    print(f"Dtype: float32")
    print(f"Output: {args.output}")
    print(f"Preview: {args.preview}")


if __name__ == "__main__":
    main()
