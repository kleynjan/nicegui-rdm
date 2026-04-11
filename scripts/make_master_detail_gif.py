"""
make_master_detail_gif.py — record a master/detail navigation demo and export
as an animated GIF to docs/screenshots/master-detail-demo.gif.

Scenario:
  1. Product list view (3 seeded products)
  2. Click "Wireless Headphones" row → detail view with summary + components
  3. Click edit (pencil) on "Driver Unit" → EditDialog opens
  4. Change Unit Cost from 25.00 → 35, Save → sub-table refreshes
  5. Click back arrow → returns to product list

Run from repo root with the rdm_test conda env:
    conda run -n rdm_test python scripts/make_master_detail_gif.py

Outputs:
    docs/screenshots/master-detail-demo.gif
"""

import io
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "screenshots" / "master-detail-demo.gif"
APP_PORT = 8080
APP_URL = f"http://localhost:{APP_PORT}"

VIEWPORT_W = 1200
VIEWPORT_H = 760
TARGET_W = 1200      # final gif width
LABEL_H = 22         # dark header strip height
MAX_H = 600          # crop gif to this height (removes bottom whitespace)
SCALE = TARGET_W / VIEWPORT_W   # 0.5 — maps viewport coords to gif coords

FRAME_DELAY = 0.07
PAUSE_DELAY = 1.4
MOVE_STEPS = 10      # frames for cursor glide between click targets


# ---------------------------------------------------------------------------
# Cursor drawing
# ---------------------------------------------------------------------------

def _draw_cursor(draw: ImageDraw.ImageDraw, x: float, y: float, clicking: bool = False) -> None:
    """Draw a standard arrow cursor at (x, y) in the already-scaled gif coordinate space."""
    # Arrow cursor polygon (tip at x,y, pointing top-left)
    pts = [
        (x,      y),
        (x,      y + 11),
        (x + 3,  y + 8),
        (x + 5,  y + 13),
        (x + 7,  y + 12),
        (x + 5,  y + 7),
        (x + 9,  y + 7),
    ]
    draw.polygon(pts, fill=(255, 255, 255))
    draw.line(pts + [pts[0]], fill=(20, 20, 20), width=1)
    if clicking:
        r = 14
        draw.ellipse([(x - r, y - r), (x + r, y + r)], outline=(80, 150, 255), width=2)


# ---------------------------------------------------------------------------
# Frame post-processing
# ---------------------------------------------------------------------------

def _postprocess(
    png_bytes: bytes,
    cursor_pos: tuple[float, float] | None = None,
    clicking: bool = False,
) -> Image.Image:
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    w, h = img.size
    if w != TARGET_W:
        new_h = int(h * TARGET_W / w)
        img = img.resize((TARGET_W, new_h), Image.LANCZOS)
    # Label strip at top
    canvas = Image.new("RGB", (TARGET_W, img.height + LABEL_H), (30, 30, 30))
    canvas.paste(img, (0, LABEL_H))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, 0), (TARGET_W, LABEL_H)], fill=(40, 40, 40))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        font = ImageFont.load_default()
    draw.text((8, 4), "Master/detail pattern", fill=(220, 220, 220), font=font)
    # Cursor overlay (cursor_pos is in viewport space; scale to gif space)
    if cursor_pos is not None:
        cx = cursor_pos[0] * SCALE
        cy = cursor_pos[1] * SCALE + LABEL_H
        _draw_cursor(draw, cx, cy, clicking)
    if MAX_H and canvas.height > MAX_H:
        canvas = canvas.crop((0, 0, TARGET_W, MAX_H))
    return canvas


# ---------------------------------------------------------------------------
# GIF assembly
# ---------------------------------------------------------------------------

def frames_to_gif(frames: list[tuple[Image.Image, float]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    palettized = [
        img.convert("P", palette=Image.ADAPTIVE, colors=128)
        for img, _ in frames
    ]
    durations_ms = [int(dur * 1000) for _, dur in frames]
    palettized[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=palettized[1:],
        loop=0,
        duration=durations_ms,
        optimize=True,
    )
    print(f"  → {output}  ({output.stat().st_size // 1024} KB)")


# ---------------------------------------------------------------------------
# Cursor-aware capture helpers
# ---------------------------------------------------------------------------

# Mutable cursor position in viewport coords [x, y]
_cur: list[float] = [VIEWPORT_W * 0.35, VIEWPORT_H * 0.35]


def _snap(locator) -> tuple[float, float]:
    bbox = locator.bounding_box()
    return bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2


def capture(page, clicking: bool = False) -> Image.Image:
    return _postprocess(page.screenshot(), cursor_pos=(_cur[0], _cur[1]), clicking=clicking)


def add_pause(frames: list, img: Image.Image, secs: float) -> None:
    frames.append((img, secs))


def add_frames(frames: list, page, count: int, delay: float = FRAME_DELAY) -> None:
    for _ in range(count):
        frames.append((capture(page), delay))


def move_cursor(frames: list, page, target_xy: tuple[float, float], steps: int = MOVE_STEPS) -> None:
    """Animate cursor gliding from current pos to target, appending frames."""
    fx, fy = _cur
    tx, ty = target_xy
    for i in range(1, steps + 1):
        t = i / steps
        pos = (fx + (tx - fx) * t, fy + (ty - fy) * t)
        frames.append((_postprocess(page.screenshot(), cursor_pos=pos), FRAME_DELAY))
    _cur[0], _cur[1] = tx, ty


def click_element(frames: list, page, locator, post_wait: int = 400, steps: int = MOVE_STEPS) -> None:
    """Move cursor to locator center, flash, click, wait."""
    target = _snap(locator)
    move_cursor(frames, page, target, steps)
    # Click flash (shown before the actual DOM change)
    for _ in range(2):
        frames.append((capture(page, clicking=True), 0.08))
    locator.click()
    page.wait_for_timeout(post_wait)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    from playwright.sync_api import sync_playwright

    # ── 1. Start the master_detail app in a subprocess ────────────────────
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "ng_rdm.examples.master_detail"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(REPO_ROOT),
    )

    for _ in range(40):
        try:
            urllib.request.urlopen(APP_URL, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError(f"Server did not start on {APP_URL}")

    print(f"  Server ready on {APP_URL}")

    frames: list[tuple[Image.Image, float]] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": VIEWPORT_W, "height": VIEWPORT_H})
            page = ctx.new_page()

            page.goto(APP_URL, wait_until="networkidle")
            page.wait_for_timeout(800)

            # ── 2. Opening frame: product list ────────────────────────────
            opening = capture(page)
            add_pause(frames, opening, PAUSE_DELAY * 1.5)
            add_pause(frames, opening, PAUSE_DELAY * 1.5)

            # ── 3. Cursor glides to "Wireless Headphones", click ──────────
            row = page.locator("tr").filter(has_text="Wireless Headphones")
            click_element(frames, page, row, post_wait=700)

            add_frames(frames, page, count=5)
            add_pause(frames, capture(page), PAUSE_DELAY * 1.2)
            add_pause(frames, capture(page), PAUSE_DELAY * 1.2)

            # ── 4. Cursor glides to "Driver Unit" pencil, click ───────────
            pencil = page.locator("tr").filter(has_text="Driver Unit").locator(
                ".rdm-actions .rdm-icon"
            ).first
            click_element(frames, page, pencil, post_wait=600)

            add_frames(frames, page, count=3)
            add_pause(frames, capture(page), PAUSE_DELAY * 0.9)

            # ── 5. Cursor moves to Unit Cost input, type new value ─────────
            cost_input = page.locator("input[aria-label='Unit Cost']")
            click_element(frames, page, cost_input, post_wait=200, steps=6)
            cost_input.press("Control+a")
            page.wait_for_timeout(100)

            for char in "35":
                cost_input.type(char, delay=80)
                frames.append((capture(page), 0.10))

            add_pause(frames, capture(page), PAUSE_DELAY * 0.8)

            # ── 6. Cursor glides to Save button, click ────────────────────
            save_btn = page.locator(".rdm-dialog-footer button").filter(has_text="Save")
            click_element(frames, page, save_btn, post_wait=900)

            add_frames(frames, page, count=5)
            add_pause(frames, capture(page), PAUSE_DELAY * 1.2)
            add_pause(frames, capture(page), PAUSE_DELAY * 1.2)

            # ── 7. Cursor glides to back arrow, click → product list ───────
            back_btn = page.locator(".rdm-back-nav")
            click_element(frames, page, back_btn, post_wait=600)

            add_frames(frames, page, count=5)

            closing = capture(page)
            add_pause(frames, closing, PAUSE_DELAY * 2)
            add_pause(frames, closing, PAUSE_DELAY * 2)

            browser.close()

    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

    # ── 8. Write GIF ──────────────────────────────────────────────────────
    print(f"  Encoding {len(frames)} frames …")
    frames_to_gif(frames, OUTPUT_PATH)
    print("Done.")


if __name__ == "__main__":
    run()
