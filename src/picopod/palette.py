"""Defines the Picotron color palette."""

from typing import Final

#: A list of (R, G, B) tuples representing a color palette.
type Palette = list[tuple[int, int, int]]

# Dumped using this Lua script:
#
#   ncolors = 32
#   addr = 0x5000
#   result = ""
#   for i = 0, ncolors - 1 do
#     b, g, r, a = peek(addr + i * 4, 4)
#     result ..= string.format(
#       "(%d, %d, %d),  # [%d] %02x%02x%02x\n",
#       r, g, b, i, r, g, b)
#   end
#   store("palette.txt", result)

#: Color palette from Picotron 0.3.0d as a list of (R, G, B) tuples.
PICOTRON_PALETTE: Final[Palette] = [
    (0, 0, 0),  # [0] 000000
    (29, 43, 83),  # [1] 1d2b53
    (126, 37, 83),  # [2] 7e2553
    (0, 135, 81),  # [3] 008751
    (171, 82, 54),  # [4] ab5236
    (95, 87, 79),  # [5] 5f574f
    (194, 195, 199),  # [6] c2c3c7
    (255, 241, 232),  # [7] fff1e8
    (255, 0, 77),  # [8] ff004d
    (255, 163, 0),  # [9] ffa300
    (255, 236, 39),  # [10] ffec27
    (0, 228, 54),  # [11] 00e436
    (41, 173, 255),  # [12] 29adff
    (131, 118, 156),  # [13] 83769c
    (255, 119, 168),  # [14] ff77a8
    (255, 204, 170),  # [15] ffccaa
    (36, 99, 176),  # [16] 2463b0
    (0, 165, 161),  # [17] 00a5a1
    (101, 70, 136),  # [18] 654688
    (18, 83, 89),  # [19] 125359
    (112, 50, 46),  # [20] 70322e
    (69, 45, 50),  # [21] 452d32
    (162, 136, 121),  # [22] a28879
    (255, 172, 197),  # [23] ffacc5
    (185, 0, 62),  # [24] b9003e
    (226, 107, 19),  # [25] e26b13
    (149, 240, 75),  # [26] 95f04b
    (0, 178, 81),  # [27] 00b251
    (100, 223, 246),  # [28] 64dff6
    (189, 154, 223),  # [29] bd9adf
    (228, 13, 171),  # [30] e40dab
    (244, 150, 113),  # [31] f49671
]
