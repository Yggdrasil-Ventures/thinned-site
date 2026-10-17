#!/usr/bin/env python3
"""Sample the 150 Warhammer Tone Pro swatches from Games Workshop's own chart images.

Source: the three swatch PNGs in Warhammer Community's "Sunday Preview - Warhammer Tone Pro"
article (4 October 2026). Each image shows ten colour families in two columns of five, with a
pot, a name banner and five flat colour squares numbered 1-5. Family order is column-major
(left column top to bottom, then the right column), which is the order of tools/tone_pro.csv.

The squares are flat colour and carry a printed digit in the top-left corner, so the
bottom-right quadrant of each square is sampled (median). The PNGs embed an sRGB profile,
so raw pixel values are already sRGB.

    python tools/sample_gw_swatches.py                      # download the PNGs, write tools/tone_pro.csv
    python tools/sample_gw_swatches.py --compare old.csv    # also diff against an existing CSV
    python tools/sample_gw_swatches.py a.png b.png c.png    # use local copies instead of downloading

Needs Pillow and numpy. Checked 2026-10-17: all 150 values are identical to those in the
Tone Pro chart published by Warhue, which sampled the same images.
"""
from __future__ import annotations

import argparse
import csv
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tools" / "tone_pro.csv"

URLS = [
    "https://assets.warhammer-community.com/articles/0-2026/september/wc28-09/sundaypreview-oct04-swatch1-grrhwun86c.png",
    "https://assets.warhammer-community.com/articles/0-2026/september/wc28-09/sundaypreview-oct04-swatch2-ag7m6xegoh.png",
    "https://assets.warhammer-community.com/articles/0-2026/september/wc28-09/sundaypreview-oct04-swatch3-zo7xgbm2zg.png",
]

# Family order as printed on GW's chart (image 1 left column, image 1 right column, image 2 ...).
FAMILIES = [
    "Carmine Blades", "Bloodtoof Red", "Chotec Orange", "Ta'unar Ochre", "Khemri Sands",
    "Hawkshroud Yellow", "Megaboss Yellow", "Plague Toad Venom", "Kruleboyz Green", "Lustria Green",
    "Kasrkin Green", "Hierotek Green", "Green Morkshroom", "Seraphon Blue", "Craventhrone Cloak",
    "Stormwolf Blue", "Scinari Blue", "Blue Gorkshroom", "Ultramar Blue", "Shalaxi Violet",
    "Enrapturess Dusk", "Hive Fleet Purple", "Magnus the Red", "Eye of Terror", "Carthalos Skin",
    "Celestine Skin", "Gnarlwood", "Necrolith Bone", "Dataslate Grey", "Blackstone Void",
]
MEDIUMS = [("Shading Medium", "#F9F9F9"), ("Blending Medium", "#F9F9F9")]

# x ranges that contain the swatch squares for the left and right columns (1000px wide images)
COLUMNS = [(125, 485), (595, 955)]


def opaque_runs(alpha_line: np.ndarray, x0: int, x1: int, min_w: int = 20) -> list[tuple[int, int]]:
    runs, start = [], None
    for x in range(x0, x1 + 1):
        on = x < x1 and alpha_line[x] >= 128
        if on and start is None:
            start = x
        elif not on and start is not None:
            if x - start >= min_w:
                runs.append((start, x - 1))
            start = None
    return runs


def sample_image(path: Path) -> list[list[str]]:
    """Return 10 lists of 5 hex strings (families in column-major order)."""
    rgba = np.asarray(Image.open(path).convert("RGBA")).astype(int)
    alpha = rgba[:, :, 3]
    a = alpha[:, :, None] / 255.0
    rgb = (rgba[:, :, :3] * a + 255 * (1 - a)).round().astype(int)  # composite on white

    families: list[list[str]] = []
    for xa, xb in COLUMNS:
        profile = (alpha[:, xa:xb] >= 128).sum(axis=1)
        bands, start = [], None
        for y, v in enumerate(list(profile) + [0]):
            if v > 120 and start is None:
                start = y
            elif v <= 120 and start is not None:
                if y - start > 12:
                    bands.append((start, y - 1))
                start = None
        strips = []
        for y0, y1 in bands:
            runs = opaque_runs(alpha[(y0 + y1) // 2], xa, xb)
            if 4 <= len(runs) <= 6 and all(30 <= r1 - r0 <= 90 for r0, r1 in runs):
                strips.append((y0, y1, runs))
        if len(strips) != 5:
            sys.exit(f"{path.name}: expected 5 swatch strips in column {xa}-{xb}, found {len(strips)}")
        for y0, y1, runs in strips:
            pitch = int(round(np.median([runs[i + 1][0] - runs[i][0] for i in range(len(runs) - 1)])))
            width = int(round(np.median([r1 - r0 + 1 for r0, r1 in runs])))
            x_first = runs[0][0]  # the 5th square can be white, so rebuild positions from the first
            hexes = []
            for i in range(5):
                sx0 = x_first + i * pitch
                sx1 = sx0 + width - 1
                qx0, qx1 = sx0 + (sx1 - sx0) // 2, sx1 - 4
                qy0, qy1 = y0 + (y1 - y0) // 2, y1 - 4
                q = rgb[qy0:qy1, qx0:qx1].reshape(-1, 3)
                med = np.median(q, axis=0).round().astype(int)
                hexes.append("#%02X%02X%02X" % tuple(med))
            families.append(hexes)
    return families


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pngs", nargs="*", help="local copies of the three swatch PNGs (downloaded if omitted)")
    ap.add_argument("--out", default=str(OUT), help=f"CSV to write (default {OUT.relative_to(ROOT)})")
    ap.add_argument("--compare", help="existing CSV to diff against")
    args = ap.parse_args()

    tmp = None
    if args.pngs:
        paths = [Path(p) for p in args.pngs]
    else:
        tmp = tempfile.TemporaryDirectory()
        paths = []
        for url in URLS:
            dest = Path(tmp.name) / url.rsplit("/", 1)[-1]
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (thinned.app tone-pro sampler)"})
            with urllib.request.urlopen(req, timeout=60) as resp, dest.open("wb") as fh:
                fh.write(resp.read())
            paths.append(dest)
    if len(paths) != 3:
        sys.exit("expected exactly three swatch images")

    rows: list[tuple[str, int, str]] = []
    fam_i = 0
    for path in paths:
        for hexes in sample_image(path):
            for tone, hx in enumerate(hexes, start=1):
                rows.append((FAMILIES[fam_i], tone, hx))
            fam_i += 1
    assert fam_i == 30 and len(rows) == 150

    if args.compare:
        old = {(r["colour"], r["tone"]): r["hex"].upper() for r in csv.DictReader(open(args.compare, newline="", encoding="utf-8")) if r["tone"]}
        diffs = [(f, t, old.get((f, str(t))), hx) for f, t, hx in rows if old.get((f, str(t))) != hx]
        print(f"compared with {args.compare}: {len(diffs)} of 150 differ")
        for d in diffs:
            print("  %s %d: %s -> %s" % d)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(["colour", "tone", "hex", "code", "category", "is_metallic"])
        for fam, tone, hx in rows:
            wr.writerow([fam, tone, hx, "", "", ""])
        for name, hx in MEDIUMS:
            wr.writerow([name, "", hx, "", "technical", "false"])
    print(f"wrote {args.out}: 150 paints + {len(MEDIUMS)} mediums")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    main()
