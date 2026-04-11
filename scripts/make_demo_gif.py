"""
make_demo_gif.py — record a two-browser-window reactivity demo and export as an
animated GIF (or WebP) to docs/screenshots/reactivity-demo.gif.

Scenario:
  Window A  (left)   — the "editor": adds a task and toggles priority
  Window B  (right)  — the "watcher": open at the same page, never touched

The script launches the catalog example in the background, then drives
both windows in lockstep so the viewer can see Window B update in real time
without Window A doing anything after the initial edit.

Run from repo root with the rdm_test conda env:
    conda run -n rdm_test python scripts/make_demo_gif.py

Outputs:
    docs/screenshots/reactivity-demo.gif
"""

import asyncio
import io
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "screenshots" / "reactivity-demo.gif"
APP_PORT = 7788
APP_SCRIPT = Path(__file__).parent / "demo_app.py"
APP_URL = f"http://localhost:{APP_PORT}"
SECTION_URL = APP_URL

# GIF settings
FRAME_DELAY = 0.07       # seconds between frame captures during smooth sections
PAUSE_DELAY = 1.8        # seconds to hold a "look at this" moment
VIEWPORT_W = 1200
VIEWPORT_H = 640
PANEL_W = VIEWPORT_W // 2   # each browser panel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def label_frame(img: Image.Image, left_text: str, right_text: str) -> Image.Image:
    """Add 'Browser A' / 'Browser B' labels and a divider line to a side-by-side frame."""
    draw = ImageDraw.Draw(img)
    # divider
    draw.line([(PANEL_W, 0), (PANEL_W, img.height)], fill=(100, 100, 100), width=2)
    # labels
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        font = ImageFont.load_default()
    draw.rectangle([(0, 0), (PANEL_W, 22)], fill=(40, 40, 40, 200))
    draw.rectangle([(PANEL_W, 0), (VIEWPORT_W, 22)], fill=(40, 40, 40, 200))
    draw.text((8, 4), left_text, fill=(220, 220, 220), font=font)
    draw.text((PANEL_W + 8, 4), right_text, fill=(220, 220, 220), font=font)
    return img


def make_side_by_side(left_png: bytes, right_png: bytes,
                      left_label="Browser A — editing", right_label="Browser B — watching") -> Image.Image:
    left = Image.open(io.BytesIO(left_png)).convert("RGB")
    right = Image.open(io.BytesIO(right_png)).convert("RGB")
    # resize to equal height
    h = max(left.height, right.height)
    if left.height != h:
        left = left.resize((left.width, h), Image.LANCZOS)
    if right.height != h:
        right = right.resize((right.width, h), Image.LANCZOS)
    # crop / pad widths to PANEL_W
    combined = Image.new("RGB", (PANEL_W * 2, h), (30, 30, 30))
    combined.paste(left.crop((0, 0, PANEL_W, h)), (0, 0))
    combined.paste(right.crop((0, 0, PANEL_W, h)), (PANEL_W, 0))
    return label_frame(combined, left_label, right_label)


def frames_to_gif(frames: list[tuple[Image.Image, float]], output: Path):
    """Write list of (image, duration_s) to an animated GIF using Pillow."""
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


def capture_pair(page_a, page_b) -> Image.Image:
    return make_side_by_side(
        page_a.screenshot(),
        page_b.screenshot(),
    )


def add_pause(frames: list, frame: Image.Image, secs: float):
    frames.append((frame, secs))


def add_transition(frames: list, page_a, page_b, count: int = 3, delay: float = FRAME_DELAY):
    for _ in range(count):
        frames.append((capture_pair(page_a, page_b), delay))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    from playwright.sync_api import sync_playwright

    # ── 1. Start the catalog app in a subprocess ──────────────────────────
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, str(APP_SCRIPT)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(REPO_ROOT),
    )

    # wait for the server to be ready
    import urllib.request
    for attempt in range(30):
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

            # ── 2. Open two pages ─────────────────────────────────────────
            ctx_a = browser.new_context(viewport={"width": PANEL_W, "height": VIEWPORT_H})
            ctx_b = browser.new_context(viewport={"width": PANEL_W, "height": VIEWPORT_H})
            page_a = ctx_a.new_page()
            page_b = ctx_b.new_page()

            # navigate both to the custom-component section
            page_a.goto(SECTION_URL, wait_until="networkidle")
            page_b.goto(SECTION_URL, wait_until="networkidle")

            # let both pages settle
            for page in (page_a, page_b):
                page.wait_for_timeout(400)

            # ── 3. Opening frame: both idle, let viewer read the UI ───────
            opening = capture_pair(page_a, page_b)
            add_pause(frames, opening, PAUSE_DELAY * 1.5)
            add_pause(frames, opening, PAUSE_DELAY * 1.5)   # hold long

            # ── 4. Window A: focus & fill the title input ─────────────────
            title_input = page_a.locator("input[aria-label='Task title']")
            title_input.click()
            page_a.wait_for_timeout(200)
            add_transition(frames, page_a, page_b, count=2)

            for char in "New urgent task":
                title_input.type(char, delay=60)
                frames.append((capture_pair(page_a, page_b), 0.06))

            add_pause(frames, capture_pair(page_a, page_b), PAUSE_DELAY * 0.6)

            # ── 5. Select priority = high via Quasar QSelect ─────────────
            page_a.locator(".q-select").first.click()
            page_a.wait_for_timeout(400)
            add_transition(frames, page_a, page_b, count=2)

            page_a.locator(".q-menu .q-item").filter(has_text="high").click()
            page_a.wait_for_timeout(300)
            add_transition(frames, page_a, page_b, count=2)

            # ── 6. Click "Add Task" ───────────────────────────────────────
            page_a.locator("button").filter(has_text="Add Task").click()
            page_a.wait_for_timeout(800)   # wait for store notify + rebuild

            # capture the moment the table updates in B
            for _ in range(6):
                frames.append((capture_pair(page_a, page_b), FRAME_DELAY))

            add_pause(frames, capture_pair(page_a, page_b), PAUSE_DELAY * 1.5)

            # ── 7. Toggle priority of "Write tests" via Window A ─────────
            page_a.locator("button").filter(has_text="Toggle priority").click()
            page_a.wait_for_timeout(800)

            for _ in range(6):
                frames.append((capture_pair(page_a, page_b), FRAME_DELAY))

            # long hold so reader sees the highlight update in B
            add_pause(frames, capture_pair(page_a, page_b), PAUSE_DELAY * 2)
            add_pause(frames, capture_pair(page_a, page_b), PAUSE_DELAY * 2)

            # ── 8. Closing frame ──────────────────────────────────────────
            closing = make_side_by_side(
                page_a.screenshot(),
                page_b.screenshot(),
                left_label="Browser A — edited",
                right_label="Browser B — updated automatically",
            )
            add_pause(frames, closing, PAUSE_DELAY * 3)
            add_pause(frames, closing, PAUSE_DELAY * 3)

            browser.close()

    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

    # ── 9. Write GIF ──────────────────────────────────────────────────────
    print(f"  Encoding {len(frames)} frames …")
    frames_to_gif(frames, OUTPUT_PATH)
    print("Done.")


if __name__ == "__main__":
    run()
