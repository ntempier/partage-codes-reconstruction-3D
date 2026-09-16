#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


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


def oriented_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        width, height = image.size
        orientation = image.getexif().get(274, 1)
    if orientation in (5, 6, 7, 8):
        return height, width
    return width, height


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def interpolate_crops(
    files: list[Path],
    config: dict,
) -> list[dict]:
    width, height = map(int, config["common_size"])
    points = sorted(config["crops"], key=lambda item: int(item["index"]))
    if len(points) < 2:
        raise ValueError("Need at least two sampled crops to interpolate x/y")

    sample_indices = np.array([int(item["index"]) for item in points], dtype=float)
    sample_x = np.array([int(item["x"]) for item in points], dtype=float)
    sample_y = np.array([int(item["y"]) for item in points], dtype=float)
    all_indices = np.arange(len(files), dtype=float)
    interp_x = np.rint(np.interp(all_indices, sample_indices, sample_x)).astype(int)
    interp_y = np.rint(np.interp(all_indices, sample_indices, sample_y)).astype(int)

    crops = []
    for index, path in enumerate(files):
        full_width, full_height = oriented_size(path)
        if width > full_width or height > full_height:
            raise ValueError(
                f"Crop {width}x{height} is larger than oriented image "
                f"{full_width}x{full_height} for {path}"
            )
        x = clamp(int(interp_x[index]), 0, full_width - width)
        y = clamp(int(interp_y[index]), 0, full_height - height)
        crops.append(
            {
                "index": index,
                "number": index + 1,
                "file": str(path),
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "x2": x + width,
                "y2": y + height,
                "full_width": full_width,
                "full_height": full_height,
            }
        )
    return crops


def save_crop_table(crops: list[dict], output_json: Path, output_csv: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps({"crops": crops}, indent=2))

    fieldnames = [
        "index",
        "number",
        "file",
        "x",
        "y",
        "width",
        "height",
        "x2",
        "y2",
        "full_width",
        "full_height",
    ]
    with output_csv.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(crops)


def apply_crops(crops: list[dict], output_dir: Path, mode: str, quality: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, crop in enumerate(crops, start=1):
        path = Path(crop["file"])
        with Image.open(path) as raw:
            image = orient_image(raw).convert(mode)
            cropped = image.crop((crop["x"], crop["y"], crop["x2"], crop["y2"]))
        output_path = output_dir / f"{crop['number']:04d}.JPG"
        if mode == "L":
            cropped.save(output_path, quality=quality)
        else:
            cropped.save(output_path, quality=quality, subsampling=0)
        if i == 1 or i == len(crops) or i % 25 == 0:
            print(f"Cropped {i}/{len(crops)}: {output_path}", flush=True)


def make_preview(
    crops: list[dict],
    output: Path,
    samples: int = 20,
    mode: str = "overlay",
) -> None:
    if samples >= len(crops):
        selected = crops
    else:
        indices = sorted({round(i * (len(crops) - 1) / (samples - 1)) for i in range(samples)})
        selected = [crops[i] for i in indices]

    cols = 5
    tile_w = 360
    tile_h = 540 if mode == "overlay" else 360
    label_h = 34
    margin = 18
    rows = (len(selected) + cols - 1) // cols
    sheet = Image.new(
        "RGB",
        (cols * tile_w + (cols + 1) * margin, rows * (tile_h + label_h) + (rows + 1) * margin),
        "white",
    )
    sheet_draw = ImageDraw.Draw(sheet)

    for pos, crop in enumerate(selected):
        path = Path(crop["file"])
        with Image.open(path) as raw:
            image = orient_image(raw).convert("RGB")

        if mode == "crop":
            image = image.crop((crop["x"], crop["y"], crop["x2"], crop["y2"]))
            full_width, full_height = image.size
            thumb = image.copy()
        else:
            full_width, full_height = image.size
            thumb = image.copy()

        thumb.thumbnail((tile_w, tile_h), Image.LANCZOS)
        canvas = Image.new("RGB", (tile_w, tile_h), (245, 245, 245))
        offset_x = (tile_w - thumb.width) // 2
        offset_y = (tile_h - thumb.height) // 2
        canvas.paste(thumb, (offset_x, offset_y))

        if mode == "overlay":
            sx = thumb.width / full_width
            sy = thumb.height / full_height
            rect = [
                offset_x + crop["x"] * sx,
                offset_y + crop["y"] * sy,
                offset_x + crop["x2"] * sx,
                offset_y + crop["y2"] * sy,
            ]
            ImageDraw.Draw(canvas).rectangle(rect, outline=(255, 0, 0), width=3)

        row, col = divmod(pos, cols)
        x = margin + col * (tile_w + margin)
        y = margin + row * (tile_h + label_h + margin)
        sheet.paste(canvas, (x, y))
        label = f"{crop['number']:04d} {path.name} x={crop['x']} y={crop['y']}"
        sheet_draw.text((x, y + tile_h + 5), label, fill=(0, 0, 0))

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply sampled cryobloc crop config to every image by interpolating x/y."
    )
    parser.add_argument("--config", type=Path, default=Path("crop_selection/crop_config.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("cropped_images_gray"))
    parser.add_argument("--mode", choices=["L", "RGB"], default="L")
    parser.add_argument("--quality", type=int, default=95)
    parser.add_argument("--skip-preview", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    input_dir = Path(config["input_dir"])
    files = iter_images(input_dir)
    if len(files) != int(config["total_images"]):
        raise SystemExit(
            f"Found {len(files)} images in {input_dir}, config expects {config['total_images']}"
        )

    crops = interpolate_crops(files, config)
    table_json = Path("crop_selection/crop_interpolated_all.json")
    table_csv = Path("crop_selection/crop_interpolated_all.csv")
    save_crop_table(crops, table_json, table_csv)

    if not args.skip_preview:
        make_preview(crops, Path("crop_selection/crop_interpolated_overlay.jpg"), mode="overlay")
        make_preview(crops, Path("crop_selection/crop_interpolated_crops.jpg"), mode="crop")

    if not args.dry_run:
        apply_crops(crops, args.output_dir, args.mode, args.quality)

    first = crops[0]
    print(f"Images: {len(crops)}")
    print(f"Output size: {first['width']} x {first['height']}")
    print(f"Mode: {args.mode}")
    print(f"Output dir: {args.output_dir}")
    print(f"Crop table: {table_json}")
    print(f"Preview overlay: crop_selection/crop_interpolated_overlay.jpg")
    print(f"Preview crops: crop_selection/crop_interpolated_crops.jpg")


if __name__ == "__main__":
    main()
