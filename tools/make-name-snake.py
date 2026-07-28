#!/usr/bin/env python3
"""
Generate an animated "snake eats the grid and reveals MAKLE" SVG.

Every cell starts the same dim tone, so the name is genuinely hidden. As the
snake sweeps the board it clears ordinary cells and lights the letter cells,
so the name draws itself in behind the snake.

Rendered by GitHub inside an <img>. That means:
  - no one-shot CSS animation with fill-mode "both" (it never plays in image
    context and pins the element at its "from" state, i.e. invisible)
  - SMIL with repeatCount="indefinite" is fine and does animate
Every animation below is SMIL on an infinite loop, sharing one cycle length so
the cells and the snake stay in sync.
"""

import argparse

# 5x7 bitmap font, only the glyphs this wordmark needs.
GLYPHS = {
    "M": ["X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"],
    "A": ["..X..", ".X.X.", "X...X", "X...X", "XXXXX", "X...X", "X...X"],
    "K": ["X...X", "X..X.", "X.X..", "XX...", "X.X..", "X..X.", "X...X"],
    "L": ["X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"],
    "E": ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"],
}

COLS, ROWS = 53, 7
CELL, GAP = 11, 3
PITCH = CELL + GAP
PAD_X, PAD_Y = 16, 18

DIM = "#3A2E22"        # resting cell - name is invisible at this tone
LIT = "#EFC38F"        # revealed letter cell
SNAKE_HEAD = "#FFE7C4"
SNAKE_BODY = "#C9A375"

CYCLE = 16.0           # full loop, seconds
SWEEP = 12.8           # time spent crossing the board
FADE = 0.010           # fraction of the cycle a cell takes to change
BODY = 5               # snake body segments behind the head


def letter_cells(word):
    """Set of (col,row) covered by the wordmark, centred on the grid."""
    width = len(word) * 5 + (len(word) - 1) * 2
    start = (COLS - width) // 2
    cells, x = set(), start
    for ch in word:
        for r, line in enumerate(GLYPHS[ch]):
            for c, px in enumerate(line):
                if px == "X":
                    cells.add((x + c, r))
        x += 7
    return cells


def serpentine():
    """Visit every cell column by column, alternating direction."""
    order = []
    for c in range(COLS):
        rows = range(ROWS) if c % 2 == 0 else range(ROWS - 1, -1, -1)
        order += [(c, r) for r in rows]
    return order


def xy(c, r):
    return PAD_X + c * PITCH, PAD_Y + r * PITCH


def build(word):
    lets = letter_cells(word)
    order = serpentine()
    total = len(order)
    swf = SWEEP / CYCLE                      # sweep as a fraction of the cycle

    W = PAD_X * 2 + COLS * PITCH - GAP
    H = PAD_Y * 2 + ROWS * PITCH - GAP

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" aria-label="Snake clearing a '
        f'contribution grid to reveal {word}">',
        f"<title>{word}</title>",
        "<defs>",
        '<filter id="g" x="-70%" y="-70%" width="240%" height="240%">',
        '<feGaussianBlur stdDeviation="3.2" result="b"/>',
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>',
        "</filter>",
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="#0A0A0A" rx="10"/>',
    ]

    # --- cells -----------------------------------------------------------
    # keyTimes run across the whole cycle so every cell shares one clock.
    # values never return to their start; the indefinite repeat resets them.
    # Letter cells must be pixel-identical to ordinary cells until they light,
    # otherwise the name shows through and there is no reveal. So the glow
    # lives on a separate overlay that fades in only as each cell lights.
    lit_group, glow_group = [], []
    for i, (c, r) in enumerate(order):
        f = round(i / total * swf, 5)
        f2 = round(min(f + FADE, 0.999), 5)
        x, y = xy(c, r)
        base = f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5"'
        kt = f'keyTimes="0;{f};{f2};1"'
        if (c, r) in lets:
            lit_group.append(
                f'{base} fill="{DIM}">'
                f'<animate attributeName="fill" values="{DIM};{DIM};{LIT};{LIT}" '
                f'{kt} dur="{CYCLE}s" repeatCount="indefinite"/></rect>'
            )
            glow_group.append(
                f'{base} fill="{LIT}" opacity="0">'
                f'<animate attributeName="opacity" values="0;0;0.55;0.55" '
                f'{kt} dur="{CYCLE}s" repeatCount="indefinite"/></rect>'
            )
        else:
            out.append(
                f'{base} fill="{DIM}" opacity="1">'
                f'<animate attributeName="opacity" values="1;1;0;0" '
                f'{kt} dur="{CYCLE}s" repeatCount="indefinite"/></rect>'
            )

    # letters sit above the cleared field; glow layered on top of them
    out += lit_group
    out.append('<g filter="url(#g)">')
    out += glow_group
    out.append("</g>")

    # --- snake -----------------------------------------------------------
    # Explicit translate values per segment: robust, and avoids animateMotion
    # phase issues at the loop boundary.
    exit_steps = 10
    for k in range(BODY, -1, -1):
        pts, times = [], []
        for i in range(total + exit_steps):
            j = i - k
            if j < 0:
                cx, cy = xy(order[0][0], order[0][1])
                cx -= PITCH * 2
            elif j >= total:
                cx, cy = xy(COLS - 1, order[-1][1])
                cx += PITCH * (j - total + 1)
            else:
                cx, cy = xy(order[j][0], order[j][1])
            pts.append(f"{cx} {cy}")
            times.append(round(min(i / total * swf, 1.0), 5))
        # strictly non-decreasing, ending exactly at 1
        times[-1] = 1.0
        for n in range(1, len(times)):
            if times[n] <= times[n - 1]:
                times[n] = min(times[n - 1] + 1e-5, 1.0)
        head = k == 0
        fill = SNAKE_HEAD if head else SNAKE_BODY
        op = 1.0 if head else round(0.85 - k * 0.11, 2)
        size = CELL + (3 if head else 1)
        off = (size - CELL) / 2
        out.append(
            f'<g opacity="{op}"><rect x="{-off}" y="{-off}" width="{size}" '
            f'height="{size}" rx="{3 if head else 2.5}" fill="{fill}"'
            f'{" filter=\"url(#g)\"" if head else ""}>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="{";".join(pts)}" keyTimes="{";".join(str(t) for t in times)}" '
            f'dur="{CYCLE}s" calcMode="linear" repeatCount="indefinite"/>'
            f"</rect></g>"
        )

    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--word", default="MAKLE")
    ap.add_argument("--out", default="assets/name-snake.svg")
    a = ap.parse_args()
    svg = build(a.word.upper())
    with open(a.out, "w") as fh:
        fh.write(svg)
    print(f"wrote {a.out}  ({len(svg)//1024} KB)")
