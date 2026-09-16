#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
DEFAULT_CROP = (1500, 1400, 4600, 5300)


def iter_images(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*")
        if p.suffix.lower() in IMAGE_EXTENSIONS and not p.name.startswith("._")
    )


def orient_image(image: Image.Image) -> Image.Image:
    orientation = image.getexif().get(274, 1)
    if orientation == 3:
        return image.rotate(180, expand=True)
    if orientation == 6:
        return image.rotate(270, expand=True)
    if orientation == 8:
        return image.rotate(90, expand=True)
    return image.copy()


def sample_indices(n_images: int, n_samples: int) -> list[int]:
    if n_images <= 0:
        return []
    if n_samples >= n_images:
        return list(range(n_images))
    if n_samples <= 1:
        return [n_images // 2]
    return sorted({round(i * (n_images - 1) / (n_samples - 1)) for i in range(n_samples)})


def draw_crop_preview(
    files: list[Path],
    crop: tuple[int, int, int, int],
    output: Path,
    n_samples: int,
    columns: int,
) -> None:
    indices = sample_indices(len(files), n_samples)
    thumb_w = 360
    thumb_h = 540
    margin = 18
    label_h = 34
    rows = (len(indices) + columns - 1) // columns
    sheet_w = columns * thumb_w + (columns + 1) * margin
    sheet_h = rows * (thumb_h + label_h) + (rows + 1) * margin
    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    sheet_draw = ImageDraw.Draw(sheet)

    for k, idx in enumerate(indices):
        path = files[idx]
        with Image.open(path) as raw:
            image = orient_image(raw).convert("RGB")
            full_w, full_h = image.size
            thumb = image.copy()
            thumb.thumbnail((thumb_w, thumb_h), Image.LANCZOS)

        canvas = Image.new("RGB", (thumb_w, thumb_h), (245, 245, 245))
        offset_x = (thumb_w - thumb.width) // 2
        offset_y = (thumb_h - thumb.height) // 2
        canvas.paste(thumb, (offset_x, offset_y))

        scale_x = thumb.width / full_w
        scale_y = thumb.height / full_h
        x1, y1, x2, y2 = crop
        rect = [
            offset_x + x1 * scale_x,
            offset_y + y1 * scale_y,
            offset_x + x2 * scale_x,
            offset_y + y2 * scale_y,
        ]
        color = (255, 0, 0) if 0 <= x1 < x2 <= full_w and 0 <= y1 < y2 <= full_h else (255, 140, 0)
        ImageDraw.Draw(canvas).rectangle(rect, outline=color, width=3)

        row = k // columns
        col = k % columns
        x = margin + col * (thumb_w + margin)
        y = margin + row * (thumb_h + label_h + margin)
        sheet.paste(canvas, (x, y))
        sheet_draw.text((x, y + thumb_h + 5), f"{idx + 1:04d} {path.name}", fill=(0, 0, 0))

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a contact sheet to validate common crop dimensions."
    )
    parser.add_argument("--input", type=Path, default=Path("raw_triees_images"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--crop", type=int, nargs=4, default=DEFAULT_CROP, metavar=("X1", "Y1", "X2", "Y2"))
    parser.add_argument("--samples", type=int, default=18)
    parser.add_argument("--columns", type=int, default=6)
    args = parser.parse_args()

    files = iter_images(args.input)
    if not files:
        raise SystemExit(f"No images found in {args.input}")

    crop = tuple(args.crop)
    x1, y1, x2, y2 = crop
    output = args.output
    if output is None:
        output = Path("crop_selection") / f"crop_x{x1}_y{y1}_w{x2 - x1}_h{y2 - y1}.jpg"

    draw_crop_preview(files, crop, output, args.samples, args.columns)

    with Image.open(files[0]) as raw:
        display_size = orient_image(raw).size
    crop_area = (x2 - x1) * (y2 - y1)
    full_area = display_size[0] * display_size[1]
    print(f"Images: {len(files)}")
    print(f"Display-oriented size: {display_size[0]} x {display_size[1]}")
    print(f"Crop: x={x1}:{x2}, y={y1}:{y2} -> {x2 - x1} x {y2 - y1}")
    print(f"Area kept: {crop_area / full_area:.1%}")
    print(f"Preview: {output}")


if __name__ == "__main__":
    main()
