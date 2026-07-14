#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "picopod",
#     "pillow>=12.3.0",
# ]
#
# [tool.uv.sources]
# picopod = { path = "../" }
# ///

import argparse
import sys
from pathlib import Path
from typing import cast

from PIL import Image

from picopod import PICOTRON_PALETTE, Userdata, pod


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert an image file to a Picotron pod"
    )
    parser.add_argument("imgpath", help="Path to the input image")
    parser.add_argument("outpath", help="Path to the output pod")
    args = parser.parse_args()
    imgpath = Path(args.imgpath)
    outpath = Path(args.outpath)

    # Create a palette-only image to quantize to.
    palette = Image.new("P", (1, 1))
    palette.putpalette([c for color in PICOTRON_PALETTE for c in color])

    # Load our input image and quantize + dither it.
    image = Image.open(imgpath).convert("RGB")
    image = image.quantize(len(PICOTRON_PALETTE), palette=palette)

    # Make userdata from the palettized image.
    values = image.get_flattened_data()
    values = cast("tuple[int, ...]", values)  # For type checking purposes
    data = Userdata("u8", image.width, image.height, values)

    # Write it out in compressed binary format.
    outpath.write_bytes(pod(data, binary=True, lz4=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
