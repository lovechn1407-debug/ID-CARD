"""
screenshot_cards.py - Screenshot Canva card pages at full resolution using Selenium.
Saves card-front.png and card-back.png, then builds a clean pixel-perfect HTML page.

Usage: python screenshot_cards.py
"""
import time
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CANVA_URL  = "https://www.canva.com/design/DAHTdFZ4wJY/djAdAoUVANKmhd41fctWSw/view"
OUTPUT_DIR = "."

print("Starting Chrome browser...")
opts = Options()
opts.add_argument("--start-maximized")
opts.add_argument("--disable-blink-features=AutomationControlled")

try:
    import undetected_chromedriver as uc
    uc_opts = uc.ChromeOptions()
    uc_opts.add_argument("--start-maximized")
    driver = uc.Chrome(options=uc_opts)
    print("Using undetected ChromeDriver")
except Exception as e:
    print(f"Falling back to standard Selenium: {e}")
    driver = webdriver.Chrome(options=opts)

driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

print(f"Navigating to {CANVA_URL}...")
driver.get(CANVA_URL)

print("Waiting for design to fully render (15 seconds)...")
time.sleep(15)

# Try to find the card containers
try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.DPPJ_A"))
    )
    print("Cards detected in DOM.")
except Exception as e:
    print(f"Warning: could not confirm cards loaded: {e}")

# Give extra time for fonts, images, and animations to settle
time.sleep(5)

# Find all DPPJ_A card elements
cards = driver.find_elements(By.CSS_SELECTOR, "div.DPPJ_A")
print(f"Found {len(cards)} card(s)")

if not cards:
    print("ERROR: No cards found. Saving full page screenshot instead.")
    driver.save_screenshot(os.path.join(OUTPUT_DIR, "card-full.png"))
    driver.quit()
    sys.exit(1)

card_files = []
labels = ["front", "back", "page3", "page4"]

for i, card in enumerate(cards):
    label = labels[i] if i < len(labels) else f"page{i+1}"
    filename = f"card-{label}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Scroll to make card visible
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
    time.sleep(1)

    # Get card position and size
    loc  = card.location_once_scrolled_into_view
    size = card.size
    print(f"Card {i+1} ({label}): {size['width']}x{size['height']} at ({loc['x']}, {loc['y']})")

    # Take element screenshot (Selenium 4+)
    try:
        card.screenshot(filepath)
        print(f"  Saved: {filename}")
    except Exception as e:
        print(f"  Element screenshot failed ({e}), trying full page crop...")
        # Fallback: take full page screenshot and crop
        full_path = os.path.join(OUTPUT_DIR, f"_full_{i}.png")
        driver.save_screenshot(full_path)
        try:
            from PIL import Image
            dpr = driver.execute_script("return window.devicePixelRatio") or 1
            img = Image.open(full_path)
            x = int(loc['x'] * dpr)
            y = int(loc['y'] * dpr)
            w = int(size['width'] * dpr)
            h = int(size['height'] * dpr)
            img_w, img_h = img.size
            x2 = min(x + w, img_w)
            y2 = min(y + h, img_h)
            cropped = img.crop((x, y, x2, y2))
            cropped.save(filepath)
            print(f"  Saved (cropped): {filename}")
            os.remove(full_path)
        except Exception as crop_err:
            print(f"  Crop failed: {crop_err}. Using full screenshot.")
            os.rename(full_path, filepath)

    card_files.append((label, filename))

driver.quit()
print(f"\nScreenshots saved: {[f for _, f in card_files]}")

# Build pixel-perfect HTML page
print("Building HTML page...")
card_items_html = ""
for label, filename in card_files:
    card_items_html += f"""
  <div class="card-item">
    <div class="card-label">{label.upper()}</div>
    <div class="card-frame">
      <img src="{filename}" alt="ID Card {label}" class="card-img" />
    </div>
  </div>
"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>E-Cell ID Card</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    html, body {{
      width: 100%;
      min-height: 100vh;
      background: radial-gradient(ellipse at 20% 40%, #1a1040 0%, #070b1a 55%, #000 100%);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
      font-family: 'Inter', sans-serif;
      overflow-x: hidden;
    }}

    header {{
      width: 100%;
      padding: 40px 24px 20px;
      text-align: center;
    }}
    header .badge {{
      display: inline-block;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 999px;
      padding: 6px 18px;
      font-size: 11px;
      letter-spacing: 3px;
      text-transform: uppercase;
      color: rgba(255,255,255,0.4);
      margin-bottom: 16px;
    }}
    header h1 {{
      font-size: 28px;
      font-weight: 600;
      color: #fff;
      letter-spacing: -0.5px;
    }}
    header p {{
      font-size: 14px;
      color: rgba(255,255,255,0.35);
      margin-top: 6px;
    }}

    .cards-container {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 48px;
      padding: 20px 24px 80px;
      width: 100%;
    }}

    .card-item {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 14px;
    }}

    .card-label {{
      font-size: 11px;
      letter-spacing: 3px;
      text-transform: uppercase;
      color: rgba(255,255,255,0.3);
      font-weight: 500;
    }}

    .card-frame {{
      border-radius: 20px;
      overflow: hidden;
      box-shadow:
        0 0 0 1px rgba(255,255,255,0.07),
        0 24px 60px rgba(0,0,0,0.75),
        0 0 80px rgba(80,60,200,0.12);
      transition: transform 0.35s cubic-bezier(.22,.68,0,1.2), box-shadow 0.35s ease;
      cursor: default;
    }}

    .card-frame:hover {{
      transform: translateY(-10px) scale(1.015);
      box-shadow:
        0 0 0 1px rgba(255,255,255,0.12),
        0 40px 80px rgba(0,0,0,0.85),
        0 0 120px rgba(80,60,200,0.2);
    }}

    .card-img {{
      display: block;
      max-width: 90vw;
      height: auto;
      border-radius: 20px;
    }}

    footer {{
      padding: 24px;
      text-align: center;
      color: rgba(255,255,255,0.2);
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <header>
    <div class="badge">E-Cell · ITS Engineering College</div>
    <h1>ID Card</h1>
    <p>Love Chauhan &nbsp;·&nbsp; Creative Designing</p>
  </header>

  <div class="cards-container">
    {card_items_html}
  </div>

  <footer>E-Cell @ I.T.S Engineering College, Greater Noida</footer>
</body>
</html>"""

out_path = os.path.join(OUTPUT_DIR, "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

# Also save as design.html
with open(os.path.join(OUTPUT_DIR, "design.html"), "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML page written to {out_path}")
print("Done! Card images saved and HTML built.")
