# tools

Helpers for the content pages. Nothing here is served by Vercel (`.vercelignore` excludes
the folder).

## Warhammer Tone Pro colour chart

- `tone_pro.csv` — the 150 paints + 2 mediums (`colour,tone,hex,...`). The same file feeds
  the Thinned app's paint library, so the page and the app agree.
- `sample_gw_swatches.py` — produces `tone_pro.csv` by sampling the flat colour squares in
  Games Workshop's own three Tone Pro chart images (the Sunday Preview article of
  4 October 2026). Needs Pillow and numpy. The PNGs are downloaded to a temp folder and
  are not kept in the repo.
- `build_tone_pro.py` — regenerates the swatch grid between the `tone-pro-grid` markers in
  `paints/warhammer-tone-pro-colour-chart.html` and writes `og/tone-pro-og.html`. Prose on
  the page is hand-written and untouched by the script.

```bash
python tools/sample_gw_swatches.py --compare tools/tone_pro.csv   # re-sample GW's images
python tools/build_tone_pro.py                                      # rebuild the grid
```

To refresh the Open Graph image after a data change, render `tools/og/tone-pro-og.html`
at 1200x630 with any headless browser, e.g. on Windows:

```bash
"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --disable-gpu \
  --hide-scrollbars --virtual-time-budget=5000 --window-size=1200,630 \
  --screenshot="paints/warhammer-tone-pro-colour-chart.png" "tools/og/tone-pro-og.html"
```

Provenance check, 17 October 2026: the sampled values are identical to the 150 hex codes
in the Tone Pro chart published by Warhue (warhue.app), which sampled the same images.
