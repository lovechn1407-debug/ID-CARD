"""
extract_cards.py - Extract Canva card pages and rebuild clean standalone HTML
Usage: python extract_cards.py [input.html] [output.html]
"""
import sys
import re
from bs4 import BeautifulSoup

INPUT  = sys.argv[1] if len(sys.argv) > 1 else "index.html"
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else "design.html"

print(f"Reading {INPUT}...")
with open(INPUT, encoding="utf-8") as f:
    raw = f.read()

soup = BeautifulSoup(raw, "html.parser")

# ── 1. Collect ALL CSS from <style> blocks ─────────────────────────────────────
all_css_blocks = []
for style_tag in soup.find_all("style"):
    text = style_tag.get_text()
    # Remove the broken container-visibility overrides we injected earlier
    # (we'll re-inject better ones below)
    text = re.sub(r'/\* Standalone Browser Preview.*?\*/.*?(?=</style|@|\.[A-Z])', '', text, flags=re.DOTALL)
    all_css_blocks.append(text)
all_css = "\n".join(all_css_blocks)

# ── 2. Extract every .DPPJ_A card page ────────────────────────────────────────
cards = soup.select("div.DPPJ_A")
print(f"Found {len(cards)} card pages (DPPJ_A elements)")

if not cards:
    print("ERROR: No .DPPJ_A elements found! Check input file.")
    sys.exit(1)

cards_html = "\n".join(str(c) for c in cards)

# ── 3. Extract @font-face rules ───────────────────────────────────────────────
font_faces = re.findall(r'@font-face\s*\{[^}]+\}', all_css)
font_css = "\n".join(font_faces)

# ── 4. Extract @keyframes ─────────────────────────────────────────────────────
keyframes = re.findall(r'@keyframes\s+\S+\s*\{(?:[^{}]|\{[^{}]*\})*\}', all_css)
keyframes_css = "\n".join(keyframes)

# ── 5. Collect all class selectors used in the card HTML ──────────────────────
used_classes = set(re.findall(r'class="([^"]+)"', cards_html))
flat_classes  = set()
for cls_str in used_classes:
    for c in cls_str.split():
        flat_classes.add(c.strip())

print(f"Found {len(flat_classes)} unique classes in card elements")

# ── 6. Extract only needed CSS rules (that reference used classes) ─────────────
def extract_relevant_css(css_text, classes):
    """Keep CSS rules that reference at least one class used in the card HTML."""
    needed = []
    # Split into individual rule blocks heuristically
    # We'll keep: @font-face, @keyframes, :root, and any selector that contains a used class
    blocks = re.split(r'(?<=\})\s*(?=[@.]|\w)', css_text)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Always keep at-rules
        if block.startswith('@'):
            needed.append(block)
            continue
        # Check if any used class appears in the selector part (before first {)
        selector_part = block.split('{')[0] if '{' in block else block
        for cls in classes:
            if cls in selector_part:
                needed.append(block)
                break
    return "\n".join(needed)

# We'll use all CSS but override the broken parts
# Build standalone CSS overrides
standalone_css = """
/* ===== STANDALONE CARD VIEWER RESET ===== */
*, *::before, *::after { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  min-height: 100vh;
  overflow-x: hidden;
  overflow-y: auto;
  background: radial-gradient(ellipse at 20% 50%, #1a1040 0%, #070b1a 60%, #000000 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  font-family: 'Inter', sans-serif;
}

/* ===== CARD VIEWER WRAPPER ===== */
.card-viewer {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 24px 80px;
  gap: 40px;
  width: 100%;
}

.card-wrapper {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.08),
    0 32px 64px rgba(0,0,0,0.7),
    0 0 80px rgba(100,80,255,0.15);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card-wrapper:hover {
  transform: translateY(-8px) scale(1.01);
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.12),
    0 48px 80px rgba(0,0,0,0.8),
    0 0 100px rgba(100,80,255,0.25);
}

/* ===== FIX CANVA CONTAINER OVERFLOWS ===== */
/* Remove broken SVG clip-paths that clip out the card background */
.bFnJ2A {
  clip-path: none !important;
  -webkit-clip-path: none !important;
}

/* All absolutely-positioned card elements must be visible */
.DF_utQ {
  position: absolute !important;
  opacity: 1 !important;
  visibility: visible !important;
}

/* Card page container */
.DPPJ_A {
  position: relative !important;
  overflow: hidden !important;
}

/* Inner scaled canvas */
._14BoqA {
  position: relative !important;
  transform-origin: 0 0 !important;
  overflow: visible !important;
}

._mXnjA {
  position: relative !important;
}

/* Background fill layer */
.fbzKiw {
  position: absolute !important;
  inset: 0 !important;
}

/* Image containers */
.a26Xuw {
  width: 100% !important;
  height: 100% !important;
}

.PcHy7w, .uk_25A, .Ty61NA {
  width: 100% !important;
  height: 100% !important;
  position: relative !important;
}

.H5qArQ {
  width: 100% !important;
  height: 100% !important;
  position: relative !important;
}

.Izwocg {
  position: absolute !important;
  overflow: hidden !important;
}

._7_i_XA {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
  display: block !important;
}

/* SVG canvas layers */
._KMJVg, ._7KaXww {
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  width: 100% !important;
  height: 100% !important;
  overflow: visible !important;
}

.Ms_IOA {
  width: 100% !important;
  height: 100% !important;
  position: relative !important;
}

/* Text rendering */
.aF9o6Q {
  position: relative !important;
  overflow: visible !important;
}

._2UyCZQ {
  position: relative !important;
}

._28USrA {
  margin: 0 !important;
}

/* Drop-shadow wrapper */
.xx0k8Q {
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
}

/* Shape containers */
.hWv4NA {
  position: relative !important;
  overflow: visible !important;
}
"""

# ── 7. Build the final clean HTML ─────────────────────────────────────────────
page_title_html = """
  <div style="
    color: rgba(255,255,255,0.5);
    font-size: 12px;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 8px;
    font-family: 'Inter', system-ui, sans-serif;
  ">E-CELL ID CARD</div>
"""

cards_wrapped = ""
for i, card in enumerate(cards):
    label = "FRONT" if i == 0 else "BACK" if i == 1 else f"PAGE {i+1}"
    cards_wrapped += f"""
  <div>
    <div style="
      color: rgba(255,255,255,0.35);
      font-size: 11px;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-bottom: 12px;
      text-align: center;
      font-family: 'Inter', system-ui, sans-serif;
    ">{label}</div>
    <div class="card-wrapper">
      {str(card)}
    </div>
  </div>
"""

html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>E-Cell ID Card</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <style>
{font_css}
{keyframes_css}
{all_css}
{standalone_css}
  </style>
</head>
<body>
  <div class="card-viewer">
    {page_title_html}
    {cards_wrapped}
  </div>
</body>
</html>"""

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html_output)

print(f"SUCCESS: Clean card HTML written to '{OUTPUT}'")
print(f"   {len(cards)} card page(s) extracted and wrapped in standalone layout")
