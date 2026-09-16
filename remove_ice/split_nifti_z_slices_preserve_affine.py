#!/usr/bin/env python3
"""Split a 3D NIfTI-1 .nii volume into z single-slice NIfTI files.

Each output is a 3D volume with shape (X, Y, 1).  The qform/sform offsets are
shifted so voxel (0, 0, 0) in the slice corresponds to voxel (0, 0, z) in the
source volume.
"""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path


HEADER_SIZE = 348
SINGLE_FILE_VOX_OFFSET = 352.0


def nifti_endian(header: bytes) -> str:
    if struct.unpack("<i", header[:4])[0] == HEADER_SIZE:
        return "<"
    if struct.unpack(">i", header[:4])[0] == HEADER_SIZE:
        return ">"
    raise ValueError("Not a valid NIfTI-1 header: sizeof_hdr is not 348")


def unpack(fmt: str, header: bytes, start: int, endian: str):
    size = struct.calcsize(endian + fmt)
    values = struct.unpack(endian + fmt, header[start : start + size])
    return values[0] if len(values) == 1 else values


def pack_into(fmt: str, header: bytearray, start: int, endian: str, *values) -> None:
    struct.pack_into(endian + fmt, header, start, *values)


def qform_z_column(header: bytes, endian: str) -> tuple[float, float, float]:
    pixdim = unpack("8f", header, 76, endian)
    b = unpack("f", header, 256, endian)
    c = unpack("f", header, 260, endian)
    d = unpack("f", header, 264, endian)

    a2 = 1.0 - (b * b + c * c + d * d)
    a = math.sqrt(max(a2, 0.0))
    qfac = -1.0 if pixdim[0] < 0 else 1.0
    dz = pixdim[3] * qfac

    return (
        (2.0 * b * d + 2.0 * a * c) * dz,
        (2.0 * c * d - 2.0 * a * b) * dz,
        (a * a + d * d - c * c - b * b) * dz,
    )


def shifted_header(source_header: bytes, endian: str, z_index: int) -> bytearray:
    header = bytearray(source_header)
    dims = list(unpack("8h", header, 40, endian))

    dims[0] = 3
    dims[3] = 1
    for axis in range(4, 8):
        if dims[axis] == 0:
            dims[axis] = 1
    pack_into("8h", header, 40, endian, *dims)

    pack_into("h", header, 74, endian, 0)  # slice_start
    pack_into("f", header, 108, endian, SINGLE_FILE_VOX_OFFSET)
    pack_into("h", header, 120, endian, 0)  # slice_end

    sform_code = unpack("h", header, 254, endian)
    if sform_code > 0:
        for start in (280, 296, 312):
            row = list(unpack("4f", source_header, start, endian))
            row[3] = row[3] + row[2] * z_index
            pack_into("4f", header, start, endian, *row)

    qform_code = unpack("h", header, 252, endian)
    if qform_code > 0:
        z_col = qform_z_column(source_header, endian)
        for start, delta in zip((268, 272, 276), z_col):
            original_offset = unpack("f", source_header, start, endian)
            pack_into("f", header, start, endian, original_offset + delta * z_index)

    return header


def split_z_slices(input_path: Path, output_dir: Path, prefix: str | None) -> None:
    with input_path.open("rb") as src:
        source_header = src.read(HEADER_SIZE)
        endian = nifti_endian(source_header)
        magic = source_header[344:348]
        if magic != b"n+1\x00":
            raise ValueError("Only single-file NIfTI-1 .nii files are supported")

        dims = unpack("8h", source_header, 40, endian)
        if dims[0] < 3:
            raise ValueError(f"Expected a 3D NIfTI, got dim[0]={dims[0]}")
        nx, ny, nz = dims[1], dims[2], dims[3]
        if any(v <= 0 for v in (nx, ny, nz)):
            raise ValueError(f"Invalid NIfTI dimensions: {dims}")

        bitpix = unpack("h", source_header, 72, endian)
        if bitpix <= 0 or bitpix % 8 != 0:
            raise ValueError(f"Invalid bitpix value: {bitpix}")
        bytes_per_voxel = bitpix // 8

        tail_volumes = 1
        for dim in dims[4:]:
            tail_volumes *= max(dim, 1)
        if tail_volumes != 1:
            raise ValueError(f"Expected a 3D scalar volume, got trailing dims {dims[4:]}")

        vox_offset = int(round(unpack("f", source_header, 108, endian)))
        slice_bytes = nx * ny * bytes_per_voxel
        expected_bytes = vox_offset + slice_bytes * nz
        actual_bytes = input_path.stat().st_size
        if actual_bytes < expected_bytes:
            raise ValueError(
                f"File is smaller than expected from header: {actual_bytes} < {expected_bytes}"
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        output_prefix = prefix or input_path.stem
        src.seek(vox_offset)

        extension = b"\x00\x00\x00\x00"
        for z_index in range(nz):
            data = src.read(slice_bytes)
            if len(data) != slice_bytes:
                raise IOError(f"Could not read complete z slice {z_index}")

            header = shifted_header(source_header, endian, z_index)
            out_path = output_dir / f"{output_prefix}_z{z_index:03d}.nii"
            with out_path.open("wb") as dst:
                dst.write(header)
                dst.write(extension)
                dst.write(data)

            if (z_index + 1) % 25 == 0 or z_index + 1 == nz:
                print(f"{z_index + 1}/{nz} slices written", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split a 3D NIfTI-1 .nii volume into z single-slice NIfTI files."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory. Defaults to '<input_stem>_slices_z'.",
    )
    parser.add_argument("--prefix", help="Output filename prefix. Defaults to input stem.")
    args = parser.parse_args()

    output_dir = args.output_dir or args.input.with_name(f"{args.input.stem}_slices_z")
    split_z_slices(args.input, output_dir, args.prefix)
    print(f"Done: {output_dir}")


if __name__ == "__main__":
    main()
