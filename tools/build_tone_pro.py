#!/usr/bin/env python3
"""Build the swatch grid for paints/warhammer-tone-pro-colour-chart.html.

Reads tools/tone_pro.csv (columns: colour,tone,hex,code,category,is_metallic — the
same CSV that feeds the Thinned app's paint library) and rewrites everything between
the <!-- tone-pro-grid:start --> and <!-- tone-pro-grid:end --> markers in the page.
It also writes tools/og/tone-pro-og.html, the 1200x630 source for the page's Open
Graph image (render it with a headless browser; see tools/README.md).

Prose on the page is hand-written; only the grid is generated. To change the hex
source (for example to values sampled from GW's own swatch images), replace the CSV
and re-run:

    python tools/build_tone_pro.py
"""
from __future__ import annotations

import csv
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "tools" / "tone_pro.csv"
PAGE_PATH = ROOT / "paints" / "warhammer-tone-pro-colour-chart.html"
OG_PATH = ROOT / "tools" / "og" / "tone-pro-og.html"

START = "<!-- tone-pro-grid:start -->"
END = "<!-- tone-pro-grid:end -->"

INK = "#3C4142"      # site text colour (dark label)
PAPER = "#FFFDF5"    # site white (light label)
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Editorial hue groups (ours, not Games Workshop's). Family order within a group
# follows the order GW prints on its range chart, which is also the CSV order.
GROUPS: list[tuple[str, list[str]]] = [
    ("Reds and oranges", ["Carmine Blades", "Bloodtoof Red", "Chotec Orange", "Ta'unar Ochre"]),
    ("Yellows and golds", ["Khemri Sands", "Hawkshroud Yellow", "Megaboss Yellow"]),
    ("Greens", ["Plague Toad Venom", "Kruleboyz Green", "Lustria Green", "Kasrkin Green",
                "Hierotek Green", "Green Morkshroom"]),
    ("Teals and blues", ["Seraphon Blue", "Craventhrone Cloak", "Stormwolf Blue", "Scinari Blue",
                         "Blue Gorkshroom", "Ultramar Blue"]),
    ("Violets and magentas", ["Shalaxi Violet", "Enrapturess Dusk", "Hive Fleet Purple",
                              "Magnus the Red", "Eye of Terror"]),
    ("Skin, wood and bone", ["Carthalos Skin", "Celestine Skin", "Gnarlwood", "Necrolith Bone"]),
    ("Greys", ["Dataslate Grey", "Blackstone Void"]),
]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def luminance(hex_colour: str) -> float:
    """WCAG 2.x relative luminance of an #RRGGBB colour."""
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def label_class(swatch: str) -> str:
    """Pick the label colour with the higher contrast against the swatch."""
    return "sw--dark-label" if contrast(swatch, INK) >= contrast(swatch, PAPER) else "sw--light-label"


def load() -> tuple[dict[str, dict[int, str]], list[tuple[str, str]]]:
    families: dict[str, dict[int, str]] = {}
    mediums: list[tuple[str, str]] = []
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            colour = row["colour"].strip()
            hex_colour = row["hex"].strip().upper()
            if not HEX_RE.match(hex_colour):
                sys.exit(f"bad hex for {colour!r}: {hex_colour!r}")
            tone = row["tone"].strip()
            if not tone:
                mediums.append((colour, hex_colour))
                continue
            families.setdefault(colour, {})[int(tone)] = hex_colour

    expected = [f for _, fams in GROUPS for f in fams]
    missing = [f for f in expected if f not in families]
    extra = [f for f in families if f not in expected]
    if missing or extra:
        sys.exit(f"family mismatch - missing: {missing}, unexpected: {extra}")
    for fam, tones in families.items():
        if sorted(tones) != [1, 2, 3, 4, 5]:
            sys.exit(f"{fam}: expected tones 1-5, got {sorted(tones)}")
    return families, mediums


def swatch_li(family: str, tone: int, hex_colour: str) -> str:
    name = f"{family} {tone}"
    return (
        f'        <li class="sw {label_class(hex_colour)}" style="--c:{hex_colour}" '
        f'title="{html.escape(name)}: {hex_colour}">\n'
        f'          <span class="sw-tone" aria-hidden="true">{tone}</span>\n'
        f'          <span class="vh">{html.escape(name)}</span>\n'
        f'          <code class="sw-hex">{hex_colour}</code>\n'
        f'        </li>\n'
    )


def render_grid(families: dict[str, dict[int, str]]) -> str:
    out: list[str] = []
    for label, fams in GROUPS:
        gid = "g-" + slugify(label)
        out.append(f'<section class="group" aria-labelledby="{gid}">\n')
        out.append(f'  <h3 class="group-title" id="{gid}">{html.escape(label)}</h3>\n')
        for fam in fams:
            fid = slugify(fam)
            out.append(f'  <div class="fam" id="{fid}">\n')
            out.append(f'    <h4 class="fam-name"><a href="#{fid}">{html.escape(fam)}</a></h4>\n')
            out.append(f'    <ol class="ramp" aria-label="{html.escape(fam)}, tones 1 to 5">\n')
            for tone in range(1, 6):
                out.append(swatch_li(fam, tone, families[fam][tone]))
            out.append('    </ol>\n  </div>\n')
        out.append('</section>\n')
    return "".join(out)


def render_og(families: dict[str, dict[int, str]]) -> str:
    cells: list[str] = []
    for _, fams in GROUPS:
        for fam in fams:
            # tone 5 (lightest) on top, tone 1 (darkest) at the bottom, so each column reads as a ramp
            for tone in (5, 4, 3, 2, 1):
                cells.append(f'<i style="background:{families[fam][tone]}"></i>')
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex">
<title>OG image source: Warhammer Tone Pro colour chart</title>
<link href="https://fonts.googleapis.com/css2?family=Bitter:wght@300;400&display=swap" rel="stylesheet">
<style>
  html,body{{margin:0;width:1200px;height:630px;overflow:hidden;background:#FFF8E7;color:#3C4142;
    font-family:'Bitter',Georgia,serif;font-weight:300;}}
  .frame{{position:relative;width:1200px;height:630px;padding:56px 64px;box-sizing:border-box;}}
  .brand{{font-size:15px;letter-spacing:.3em;text-transform:uppercase;font-weight:400;}}
  .brand small{{margin-left:18px;letter-spacing:.22em;color:#7A6E5A;font-weight:300;font-size:12px;}}
  h1{{margin:26px 0 10px;font-size:58px;line-height:1.05;font-weight:400;letter-spacing:.06em;
    text-transform:uppercase;color:#A67B5B;}}
  .sub{{font-size:22px;color:#5E5344;margin:0 0 34px;letter-spacing:.02em;}}
  .grid{{display:grid;grid-template-columns:repeat(30,1fr);grid-auto-flow:column;
    grid-template-rows:repeat(5,42px);gap:3px;border:1px solid #BBA88A;padding:6px;border-radius:4px;
    background:#EDE4D3;}}
  .grid i{{display:block;border-radius:2px;}}
  .foot{{position:absolute;left:64px;right:64px;bottom:34px;display:flex;justify-content:space-between;
    font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#7A6E5A;}}
</style></head>
<body><div class="frame">
  <div class="brand">Thinned <small>Paint reference</small></div>
  <h1>Warhammer Tone Pro<br>colour chart</h1>
  <p class="sub">150 paints &middot; 30 colour families &middot; 5 numbered tones &middot; approximate hex codes</p>
  <div class="grid">{"".join(cells)}</div>
  <div class="foot"><span>www.thinned.app</span><span>Warhammer &amp; Citadel are trademarks of Games Workshop Ltd &middot; not affiliated</span></div>
</div></body></html>
"""


def main() -> None:
    families, mediums = load()
    grid = render_grid(families)

    page = PAGE_PATH.read_text(encoding="utf-8")
    if START not in page or END not in page:
        sys.exit(f"markers not found in {PAGE_PATH}")
    before, rest = page.split(START, 1)
    _, after = rest.split(END, 1)
    PAGE_PATH.write_text(f"{before}{START}\n{grid}{END}{after}", encoding="utf-8", newline="\n")

    OG_PATH.parent.mkdir(parents=True, exist_ok=True)
    OG_PATH.write_text(render_og(families), encoding="utf-8", newline="\n")

    n = sum(len(t) for t in families.values())
    print(f"{len(families)} families, {n} paints, {len(mediums)} mediums "
          f"({', '.join(m for m, _ in mediums)}) -> {PAGE_PATH.relative_to(ROOT)}, {OG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
