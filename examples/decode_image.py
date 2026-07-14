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

from PIL import Image

from picopod import Userdata, unpod


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a Picotron pod containing an image to an image file"
    )
    parser.add_argument("podpath", help="Path to the input pod")
    parser.add_argument("outpath", help="Path to the output image")
    args = parser.parse_args()
    podpath = Path(args.podpath)
    outpath = Path(args.outpath)

    # Unpod the input file, expecting 2D userdata.
    data = unpod(podpath.read_bytes(), type=Userdata)
    if data.height is None:
        print("Userdata is not 2D", file=sys.stderr)
        return 1

    # Use to_rgb() to easily convert the userdata to RGB values.
    image = Image.frombytes("RGB", (data.width, data.height), data.to_rgb())

    # Convert and save to the output file.
    image.save(outpath)
    return 0


if __name__ == "__main__":
    sys.exit(main())
