#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "picopod",
# ]
#
# [tool.uv.sources]
# picopod = { path = "../" }
# ///

import argparse
import re
import sys
from pathlib import Path
from typing import Final, cast

from picopod import pod, unpod
from picopod.types import Value

IDENT_REGEX: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def dump_pod(p: Value, level: int = 0) -> None:
    if isinstance(p, list):
        pl = cast("list[Value]", p)  # For type checking purposes
        if level > 0:
            print()
        indent = "  " * level
        for i, value in enumerate(pl):
            print(f"{indent}[{i}]: ", end="")
            dump_pod(value, level + 1)

    elif isinstance(p, dict):
        pd = cast("dict[Value, Value]", p)  # For type checking purposes
        if level > 0:
            print()
        indent = "  " * level
        for key, value in pd.items():
            if isinstance(key, str) and IDENT_REGEX.fullmatch(key):
                print(f"{indent}{key}: ", end="")
            else:
                print(f"{indent}[{pod(key)}]: ", end="")
            dump_pod(value, level + 1)

    else:
        print(pod(p))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dump a pod's structure to the console"
    )
    parser.add_argument("podpath", help="Path to the input pod")
    args = parser.parse_args()
    podpath = Path(args.podpath)
    dump_pod(unpod(podpath.read_bytes()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
