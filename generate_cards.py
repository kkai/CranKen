#!/usr/bin/env python3
"""Generate CranKen Playdate launcher card images.

Produces card.png, card-pressed.png, and card-highlighted/1-10.png
in a style inspired by the Gemini collage illustration: scattered math
symbols, partial grids, bold title, and a 4x4 KenKen grid.

All images are 350x155 greyscale PNGs. Playdate's pdc handles 1-bit
dithering at compile time.

Usage:
    python3 generate_cards.py
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFont, ImageOps

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

W, H = 350, 155
SEED = 42

FONT_IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
FONT_ARIAL_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
FONT_HELVETICA = "/System/Library/Fonts/Helvetica.ttc"

OUT_DIR = os.path.join(os.path.dirname(__file__), "source", "images")

# 4x4 KenKen puzzle definition
SOLUTION = [
    [4, 1, 3, 2],
    [3, 2, 4, 1],
    [1, 4, 2, 3],
    [2, 3, 1, 4],
]

CAGES = [
    {"cells": [(0, 0), (1, 0)], "op": "+", "target": 7},
    {"cells": [(2, 0), (3, 0), (3, 1)], "op": "+", "target": 6},
    {"cells": [(0, 1), (0, 2)], "op": "-", "target": 2},
    {"cells": [(1, 1), (2, 1)], "op": "x", "target": 8},
    {"cells": [(1, 2), (1, 3)], "op": "/", "target": 4},
    {"cells": [(2, 2), (2, 3)], "op": "+", "target": 3},
    {"cells": [(0, 3)], "op": "=", "target": 2},
    {"cells": [(3, 2), (3, 3)], "op": "+", "target": 7},
]

# Grid positioning
CELL_SIZE = 27
GRID_SIZE = 4
GRID_PX = CELL_SIZE * GRID_SIZE  # 108
GRID_X = 18  # left margin
GRID_Y = (H - GRID_PX) // 2  # vertically centred

# Animation: order in which cells fill (col, row)
FILL_ORDER = [
    (0, 0), (2, 0), (1, 1),
    (3, 2), (0, 3), (2, 3),
    (1, 2), (3, 0),
]

# Cells pre-filled on the static card.png (first 3 from FILL_ORDER)
STATIC_FILLS = set(FILL_ORDER[:3])


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def load_font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_scattered_symbols(draw, rng, exclusion_rects):
    """Layer 1: light-grey scattered math symbols as background texture."""
    font_small = load_font(FONT_ARIAL_BLACK, 11)
    font_med = load_font(FONT_ARIAL_BLACK, 15)
    font_large = load_font(FONT_ARIAL_BLACK, 19)
    fonts = [font_small, font_med, font_large]
    chars = list("123456789+-x/=")

    def in_exclusion(x, y, w, h):
        for ex, ey, ew, eh in exclusion_rects:
            if x + w > ex and x < ex + ew and y + h > ey and y < ey + eh:
                return True
        return False

    placed = 0
    attempts = 0
    while placed < 40 and attempts < 300:
        attempts += 1
        ch = rng.choice(chars)
        f = rng.choice(fonts)
        x = rng.randint(-5, W - 10)
        y = rng.randint(-5, H - 10)
        bbox = f.getbbox(ch)
        cw = bbox[2] - bbox[0]
        ch_h = bbox[3] - bbox[1]

        if in_exclusion(x, y, cw + 4, ch_h + 4):
            continue

        # Draw rotated symbol on a small temp image
        pad = 6
        tmp_size = max(cw, ch_h) + pad * 2
        tmp = Image.new("L", (tmp_size, tmp_size), 255)
        tmp_draw = ImageDraw.Draw(tmp)
        tx = (tmp_size - cw) // 2
        ty = (tmp_size - ch_h) // 2
        grey = rng.randint(175, 210)
        tmp_draw.text((tx, ty), ch, font=f, fill=grey)
        angle = rng.randint(-35, 35)
        tmp = tmp.rotate(angle, resample=Image.BICUBIC, fillcolor=255)
        # Paste onto main image
        paste_x = x - pad
        paste_y = y - pad
        # Use the symbol image as both source and mask (inverted)
        mask = ImageOps.invert(tmp)
        try:
            draw._image.paste(tmp, (paste_x, paste_y), mask)
        except Exception:
            draw._image.paste(tmp, (paste_x, paste_y))
        placed += 1


def draw_mini_grids(draw, rng):
    """Layer 2: small partial grid decorations in corners."""
    patterns = [
        # (x_offset, y_offset, rows, cols, filled_cells, cell_px)
        (260, 5, 3, 3, [(0, 0), (1, 1), (2, 0), (0, 2)], 10),
        (290, 110, 3, 2, [(0, 0), (1, 1), (2, 0)], 11),
        (145, 125, 2, 3, [(0, 1), (1, 0)], 9),
    ]
    for ox, oy, rows, cols, filled, cpx in patterns:
        for r in range(rows):
            for c in range(cols):
                x0 = ox + c * cpx
                y0 = oy + r * cpx
                if (r, c) in filled:
                    draw.rectangle([x0, y0, x0 + cpx - 1, y0 + cpx - 1], fill=160)
                draw.rectangle([x0, y0, x0 + cpx - 1, y0 + cpx - 1], outline=180)


def draw_cage_borders(draw, cage, cell_size, gx, gy, line_width=3, color=0):
    """Draw thick borders around cage boundaries (port of game_ui.lua logic)."""
    cell_set = set(cage["cells"])
    for cx, cy in cage["cells"]:
        sx = gx + cx * cell_size
        sy = gy + cy * cell_size
        # Top
        if cy == 0 or (cx, cy - 1) not in cell_set:
            draw.line([(sx, sy), (sx + cell_size, sy)], fill=color, width=line_width)
        # Bottom
        if cy == GRID_SIZE - 1 or (cx, cy + 1) not in cell_set:
            draw.line([(sx, sy + cell_size), (sx + cell_size, sy + cell_size)],
                      fill=color, width=line_width)
        # Left
        if cx == 0 or (cx - 1, cy) not in cell_set:
            draw.line([(sx, sy), (sx, sy + cell_size)], fill=color, width=line_width)
        # Right
        if cx == GRID_SIZE - 1 or (cx + 1, cy) not in cell_set:
            draw.line([(sx + cell_size, sy), (sx + cell_size, sy + cell_size)],
                      fill=color, width=line_width)


def draw_grid(draw, filled_cells, gx=GRID_X, gy=GRID_Y):
    """Draw the 4x4 KenKen grid with cage borders, targets, and numbers."""
    cs = CELL_SIZE
    font_num = load_font(FONT_HELVETICA, 16)
    font_target = load_font(FONT_ARIAL_BLACK, 8)

    # White grid background
    draw.rectangle([gx, gy, gx + GRID_PX, gy + GRID_PX], fill=255)

    # Thin internal grid lines
    for i in range(GRID_SIZE + 1):
        draw.line([(gx + i * cs, gy), (gx + i * cs, gy + GRID_PX)], fill=180, width=1)
        draw.line([(gx, gy + i * cs), (gx + GRID_PX, gy + i * cs)], fill=180, width=1)

    # Cage borders (thick black)
    for cage in CAGES:
        draw_cage_borders(draw, cage, cs, gx, gy, line_width=3, color=0)

    # Cage target labels
    for cage in CAGES:
        first = cage["cells"][0]
        tx = gx + first[0] * cs + 3
        ty = gy + first[1] * cs + 1
        if cage["op"] == "=":
            label = str(cage["target"])
        else:
            label = f"{cage['target']}{cage['op']}"
        draw.text((tx, ty), label, font=font_target, fill=0)

    # Fill in numbers for specified cells
    for cx, cy in filled_cells:
        num = SOLUTION[cx][cy]
        bbox = font_num.getbbox(str(num))
        nw = bbox[2] - bbox[0]
        nh = bbox[3] - bbox[1]
        nx = gx + cx * cs + (cs - nw) // 2
        ny = gy + cy * cs + (cs - nh) // 2 + 2  # nudge down past target
        draw.text((nx, ny), str(num), font=font_num, fill=0)


def draw_title(draw, x, y):
    """Draw bold 'CranKen' title with offset-shadow technique."""
    font_title = load_font(FONT_IMPACT, 36)
    font_sub = load_font(FONT_ARIAL_BLACK, 11)

    # Double-strike for boldness
    draw.text((x + 1, y + 1), "CranKen", font=font_title, fill=0)
    draw.text((x, y), "CranKen", font=font_title, fill=0)

    # Subtitle
    draw.text((x + 2, y + 40), "Math Puzzle", font=font_sub, fill=40)
    draw.text((x + 2, y + 55), "Game", font=font_sub, fill=40)


def draw_crank_icon(draw, cx, cy, radius=16, angle_deg=0):
    """Draw a simple crank/dial icon: circle with a handle line."""
    # Outer circle
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=0, width=2
    )
    # Inner dot
    draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=0)
    # Handle
    angle_rad = math.radians(angle_deg)
    hx = cx + int(radius * 0.9 * math.cos(angle_rad))
    hy = cy - int(radius * 0.9 * math.sin(angle_rad))
    draw.line([(cx, cy), (hx, hy)], fill=0, width=2)
    # Handle knob
    draw.ellipse([hx - 3, hy - 3, hx + 3, hy + 3], fill=0)


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

def make_base_image(filled_cells, crank_angle=45):
    """Create a full card composition with the given filled cells."""
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)
    rng = random.Random(SEED)

    # Exclusion zones: grid area, title area
    exclusions = [
        (GRID_X - 4, GRID_Y - 4, GRID_PX + 8, GRID_PX + 8),
        (148, 15, 185, 80),  # title region
    ]

    # Layer 1: scattered symbols
    draw_scattered_symbols(draw, rng, exclusions)

    # Layer 2: mini grid decorations
    draw_mini_grids(draw, rng)

    # Layer 3: main KenKen grid
    draw_grid(draw, filled_cells)

    # Layer 4: title
    draw_title(draw, 155, 20)

    # Crank icon (right side, below title)
    draw_crank_icon(draw, 305, 105, radius=18, angle_deg=crank_angle)

    return img


def generate_all():
    os.makedirs(os.path.join(OUT_DIR, "card-highlighted"), exist_ok=True)

    # --- card.png (static, 3 pre-filled numbers) ---
    card = make_base_image(STATIC_FILLS, crank_angle=45)
    card_path = os.path.join(OUT_DIR, "card.png")
    card.save(card_path)
    print(f"  card.png")

    # --- card-pressed.png (inverted) ---
    pressed = ImageOps.invert(card)
    pressed_path = os.path.join(OUT_DIR, "card-pressed.png")
    pressed.save(pressed_path)
    print(f"  card-pressed.png")

    # --- card-highlighted animation (10 frames) ---
    for frame_num in range(1, 11):
        if frame_num <= 8:
            # Frames 1-8: progressively fill cells
            filled = set(FILL_ORDER[:frame_num])
            crank_angle = 45 + (frame_num - 1) * 40
            img = make_base_image(filled, crank_angle=crank_angle)
        else:
            # Frames 9-10: all cells filled, bold outer border
            filled = set(FILL_ORDER[:8])
            crank_angle = 45 + 7 * 40  # keep at final position
            img = make_base_image(filled, crank_angle=crank_angle)
            # Add a bold outer border on the grid for completion emphasis
            d = ImageDraw.Draw(img)
            d.rectangle(
                [GRID_X - 2, GRID_Y - 2, GRID_X + GRID_PX + 2, GRID_Y + GRID_PX + 2],
                outline=0, width=4
            )

        frame_path = os.path.join(OUT_DIR, "card-highlighted", f"{frame_num}.png")
        img.save(frame_path)
        print(f"  card-highlighted/{frame_num}.png")

    # --- animation.txt ---
    anim_path = os.path.join(OUT_DIR, "card-highlighted", "animation.txt")
    with open(anim_path, "w") as f:
        f.write("loopCount = 0\n")
        f.write("frames = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10\n")
        f.write("introFrames = 1x2, 2, 3\n")
    print(f"  card-highlighted/animation.txt")


if __name__ == "__main__":
    print("Generating CranKen launcher cards...")
    generate_all()
    print("Done!")
