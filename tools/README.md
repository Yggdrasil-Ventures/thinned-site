# tools

Helpers for the content pages. Nothing here is served by Vercel.

## Warhammer Tone Pro colour chart

- `tone_pro.csv` — the 150 paints + 2 mediums (`colour,tone,hex,...`). Same file that feeds
  the Thinned app's paint library, so the page and the app always agree.
- `build_tone_pro.py` — regenerates the swatch grid between the `tone-pro-grid` markers in
  `paints/warhammer-tone-pro-colour-chart.html` and writes `og/tone-pro-og.html`. Prose on
  the page is hand-written and untouched by the script.

```bash
python tools/build_tone_pro.py
```

To refresh the Open Graph image after a data change, render `tools/og/tone-pro-og.html`
at 1200x630 with any headless browser, e.g. on Windows:

```bash
"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --disable-gpu \
  --hide-scrollbars --virtual-time-budget=5000 --window-size=1200,630 \
  --screenshot="paints/warhammer-tone-pro-colour-chart.png" "tools/og/tone-pro-og.html"
```
