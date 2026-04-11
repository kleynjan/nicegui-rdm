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
MOVE_STEPS = 10              # frames for cursor glide between targets


# ---------------------------------------------------------------------------
# Cursor drawing
# ---------------------------------------------------------------------------

# Mutable cursor position for Window A (in its 600px viewport space)
_cur_a: list[float] = [PANEL_W * 0.5, VIEWPORT_H * 0.4]


def _draw_cursor(draw: ImageDraw.ImageDraw, x: float, y: float, clicking: bool = False) -> None:
    """Draw a standard arrow cursor at (x, y)."""
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


def _snap_a(locator) -> tuple[float, float]:
    bbox = locator.bounding_box()
    return bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2


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


def make_side_by_side(
    left_png: bytes,
    right_png: bytes,
    left_label: str = "Browser A — editing",
    right_label: str = "Browser B — watching",
    clicking: bool = False,
) -> Image.Image:
    left = Image.open(io.BytesIO(left_png)).convert("RGB")
    right = Image.open(io.BytesIO(right_png)).convert("RGB")
    # draw cursor on left panel (Window A)
    draw = ImageDraw.Draw(left)
    _draw_cursor(draw, _cur_a[0], _cur_a[1], clicking)
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


def capture_pair(page_a, page_b, clicking: bool = False) -> Image.Image:
    return make_side_by_side(page_a.screenshot(), page_b.screenshot(), clicking=clicking)


def add_pause(frames: list, frame: Image.Image, secs: float):
    frames.append((frame, secs))


def add_transition(frames: list, page_a, page_b, count: int = 3, delay: float = FRAME_DELAY):
    for _ in range(count):
        frames.append((capture_pair(page_a, page_b), delay))


def move_cursor_a(frames: list, page_a, page_b, target: tuple[float, float], steps: int = MOVE_STEPS) -> None:
    """Animate cursor gliding across Window A from current pos to target."""
    fx, fy = _cur_a
    tx, ty = target
    for i in range(1, steps + 1):
        t = i / steps
        _cur_a[0] = fx + (tx - fx) * t
        _cur_a[1] = fy + (ty - fy) * t
        frames.append((capture_pair(page_a, page_b), FRAME_DELAY))
    _cur_a[0], _cur_a[1] = tx, ty


def click_element_a(frames: list, page_a, page_b, locator, post_wait: int = 400, steps: int = MOVE_STEPS) -> None:
    """Move cursor to locator, flash, click, wait."""
    target = _snap_a(locator)
    move_cursor_a(frames, page_a, page_b, target, steps)
    for _ in range(2):
        frames.append((capture_pair(page_a, page_b, clicking=True), 0.08))
    locator.click()
    page_a.wait_for_timeout(post_wait)


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

            # ── 3. Opening frame: both idle ───────────────────────────────
            opening = capture_pair(page_a, page_b)
            add_pause(frames, opening, PAUSE_DELAY * 1.5)
            add_pause(frames, opening, PAUSE_DELAY * 1.5)

            # ── 4. Cursor glides to title input, click ────────────────────
            title_input = page_a.locator("input[aria-label='Task title']")
            click_element_a(frames, page_a, page_b, title_input, post_wait=200)
            add_transition(frames, page_a, page_b, count=2)

            # ── 5. Type task title character by character ─────────────────
            for char in "New urgent task":
                title_input.type(char, delay=60)
                frames.append((capture_pair(page_a, page_b), 0.06))

            add_pause(frames, capture_pair(page_a, page_b), PAUSE_DELAY * 0.6)

            # ── 6. Cursor glides to priority select, click ────────────────
            priority_select = page_a.locator(".q-select").first
            click_element_a(frames, page_a, page_b, priority_select, post_wait=400)
            add_transition(frames, page_a, page_b, count=2)

            # ── 7. Cursor glides to "high" menu item, click ───────────────
            high_item = page_a.locator(".q-menu .q-item").filter(has_text="high")
            click_element_a(frames, page_a, page_b, high_item, post_wait=300, steps=6)
            add_transition(frames, page_a, page_b, count=2)

            # ── 8. Cursor glides to "Add Task" button, click ──────────────
            add_btn = page_a.locator("button").filter(has_text="Add Task")
            click_element_a(frames, page_a, page_b, add_btn, post_wait=800)

            for _ in range(6):
                frames.append((capture_pair(page_a, page_b), FRAME_DELAY))

            add_pause(frames, capture_pair(page_a, page_b), PAUSE_DELAY * 1.5)

            # ── 9. Cursor glides to "Toggle priority" button, click ───────
            toggle_btn = page_a.locator("button").filter(has_text="Toggle priority")
            click_element_a(frames, page_a, page_b, toggle_btn, post_wait=800)

            for _ in range(6):
                frames.append((capture_pair(page_a, page_b), FRAME_DELAY))

            add_pause(frames, capture_pair(page_a, page_b), PAUSE_DELAY * 2)
            add_pause(frames, capture_pair(page_a, page_b), PAUSE_DELAY * 2)

            # ── 10. Closing frame ─────────────────────────────────────────
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

    # ── 11. Write GIF ─────────────────────────────────────────────────────
    print(f"  Encoding {len(frames)} frames …")
    frames_to_gif(frames, OUTPUT_PATH)
    print("Done.")


if __name__ == "__main__":
    run()
