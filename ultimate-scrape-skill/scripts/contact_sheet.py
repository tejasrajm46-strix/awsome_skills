#!/usr/bin/env python3
"""Create a labeled local image contact sheet; Pillow is optional until invoked."""
import argparse
from pathlib import Path


def main():
    from PIL import Image, ImageDraw
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("images", nargs="+")
    ap.add_argument("-o", "--out", default="sheet.jpg")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--cell", type=int, default=320)
    args = ap.parse_args()
    if args.cols < 1 or args.cell < 64:
        ap.error("cols must be positive and cell at least 64")
    rows = (len(args.images) + args.cols - 1) // args.cols
    canvas = Image.new("RGB", (args.cols * args.cell, rows * (args.cell + 44)), "#111412")
    draw = ImageDraw.Draw(canvas)
    for index, name in enumerate(args.images):
        with Image.open(name) as image:
            image = image.convert("RGB")
            image.thumbnail((args.cell - 20, args.cell - 20))
            x = (index % args.cols) * args.cell
            y = (index // args.cols) * (args.cell + 44)
            canvas.paste(image, (x + (args.cell - image.width) // 2, y + (args.cell - image.height) // 2))
            draw.text((x + 12, y + args.cell), "%d. %s" % (index + 1, Path(name).name), fill="white")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    print("Created %s with %d reviewed candidates" % (output, len(args.images)))


if __name__ == "__main__":
    main()
