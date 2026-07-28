#!/usr/bin/env python3
"""
Generate an animated "snake wanders the grid and reveals a name" SVG.

Every cell starts the same dim tone, so the name is genuinely hidden. As the
snake wanders it clears ordinary cells and lights the letter cells, so the
wordmark emerges behind it.

The route cannot simply be shuffled: consecutive cells must stay orthogonally
adjacent or the snake teleports. It also must not be a Hamiltonian path. On a
grid this wide and shallow, visiting every cell exactly once forces a
near-monotonic left-to-right march - the route cannot doubleback without
revisiting - and that reads as a clean wipe rather than a snake. (Randomising
such a path with backbite does not help; the within-column spread plateaus
around 0.14 however long it is mixed, because the geometry, not the ordering,
is the constraint.)

So the snake is allowed to revisit. It eats whatever is next to it, and when
it runs out of adjacent food it strikes out for a RANDOM far cell rather than
the nearest one. Those excursions are what leave a ragged frontier behind it,
and they raise the spread to ~0.59 for only ~1.2x the steps.

Rendered by GitHub inside an <img>. That means:
  - no one-shot CSS animation with fill-mode "both" (it never plays in image
    context and pins the element at its "from" state, i.e. invisible)
  - SMIL with repeatCount="indefinite" is fine and does animate
Every animation below is SMIL on an infinite loop sharing one cycle length, so
the cells and the snake stay in sync.
"""

import argparse
import random

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

DIM = "#3A2E22"
LIT = "#EFC38F"
SNAKE_HEAD = "#FFE7C4"
SNAKE_BODY = "#C9A375"

CYCLE = 18.0     # full loop, seconds
SWEEP = 14.6     # time spent crossing the board
FADE = 0.010     # fraction of the cycle a cell takes to change
BODY = 5         # snake body segments behind the head


def letter_cells(word):
    """Cells covered by the wordmark, centred on the grid."""
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


def neighbours(cell):
    c, r = cell
    out = []
    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nc, nr = c + dc, r + dr
        if 0 <= nc < COLS and 0 <= nr < ROWS:
            out.append((nc, nr))
    return out


def serpentine():
    order = []
    for c in range(COLS):
        rows = range(ROWS) if c % 2 == 0 else range(ROWS - 1, -1, -1)
        order += [(c, r) for r in rows]
    return order


def _step_toward(start, remaining):
    """First step of a shortest route from start to any cell in `remaining`."""
    if not remaining:
        return None
    seen = {start}
    queue = [(start, None)]
    while queue:
        cell, first = queue.pop(0)
        if cell in remaining:
            return first
        for nb in neighbours(cell):
            if nb not in seen:
                seen.add(nb)
                queue.append((nb, first or nb))
    return None


def wander(seed, straightness=0.62, roam=0.0):
    """
    A snake that roams and doubles back, eating each cell the first time it
    passes. Deliberately NOT a Hamiltonian path: on a 53x7 grid, visiting every
    cell exactly once forces a near-monotonic left-to-right march (the route
    cannot cross back without revisiting), which reads as a clean wipe rather
    than a snake. Allowing revisits is what makes the motion look alive.

    Ordinary cells are the targets. Letter cells are never eaten, so the snake
    simply slithers over the hidden name.
    """
    rnd = random.Random(seed)
    lets = wander.letters
    targets = {(c, r) for c in range(COLS) for r in range(ROWS)} - lets
    eaten = set()

    pos = (0, ROWS // 2)
    path = [pos]
    if pos in targets:
        eaten.add(pos)
    heading = None
    goal = None

    while len(eaten) < len(targets):
        left = targets - eaten
        # Head for a RANDOM far cell now and then, not the nearest one. Eating
        # only what is next to you keeps the snake pinned to a tidy frontier;
        # these excursions are what leave the ragged holes behind it.
        if goal is None or goal in eaten:
            goal = rnd.choice(sorted(left))

        fresh = [n for n in neighbours(pos) if n in left]
        if fresh and rnd.random() > roam:
            ahead = [n for n in fresh
                     if (n[0] - pos[0], n[1] - pos[1]) == heading]
            # bias toward carrying on straight, else the walk looks twitchy
            nxt = rnd.choice(ahead) if ahead and rnd.random() < straightness \
                else rnd.choice(fresh)
        else:
            nxt = _step_toward(pos, {goal}) or _step_toward(pos, left)
            if nxt is None:
                break
        heading = (nxt[0] - pos[0], nxt[1] - pos[1])
        pos = nxt
        path.append(pos)
        if pos in targets:
            eaten.add(pos)

    assert eaten == targets, "snake must clear every ordinary cell"
    for a, b in zip(path, path[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, "path must stay adjacent"
    return path


def xy(c, r):
    return PAD_X + c * PITCH, PAD_Y + r * PITCH


def build(word, seed, straightness, roam=0.0):
    lets = letter_cells(word)
    wander.letters = lets
    path = wander(seed, straightness, roam)
    total = len(path)
    swf = SWEEP / CYCLE

    # The snake may pass a cell more than once, so everything keys off the
    # FIRST time it arrives.
    first = {}
    for i, cell in enumerate(path):
        first.setdefault(cell, i)

    # Letter cells are never stepped on reliably (the snake only has to clear
    # ordinary cells), so light each one when the snake first comes alongside.
    light_at = {}
    for i, cell in enumerate(path):
        for nb in (cell, *neighbours(cell)):
            if nb in lets and nb not in light_at:
                light_at[nb] = i

    W = PAD_X * 2 + COLS * PITCH - GAP
    H = PAD_Y * 2 + ROWS * PITCH - GAP

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" aria-label="A snake clearing a '
        f'grid to reveal {word}">',
        f"<title>{word}</title>",
        "<defs>",
        '<filter id="g" x="-70%" y="-70%" width="240%" height="240%">',
        '<feGaussianBlur stdDeviation="3.2" result="b"/>',
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>',
        "</filter>",
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="#0A0A0A" rx="10"/>',
    ]

    # Letter cells must be identical to ordinary cells until they light, or the
    # name shows through and there is no reveal. So the glow sits on a separate
    # overlay that fades in only as each cell lights.
    lit_group, glow_group = [], []
    for c in range(COLS):
      for r in range(ROWS):
        cell = (c, r)
        i = light_at.get(cell, total - 1) if cell in lets else first[cell]
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

    out += lit_group
    out.append('<g filter="url(#g)">')
    out += glow_group
    out.append("</g>")

    # Snake: explicit translate values per segment. Robust, and avoids
    # animateMotion phase problems at the loop boundary.
    end_t = round(swf, 5)
    gone = round(min(swf + 0.02, 0.999), 5)
    for k in range(BODY, -1, -1):
        pts, times = [], []
        for i in range(total):
            j = max(i - k, 0)
            cx, cy = xy(*path[j])
            pts.append(f"{cx} {cy}")
            times.append(round(i / total * swf, 5))
        times[-1] = min(times[-1], end_t)
        for n in range(1, len(times)):
            if times[n] <= times[n - 1]:
                times[n] = min(times[n - 1] + 1e-5, 1.0)
        # hold the final position through the end of the cycle
        pts.append(pts[-1])
        times.append(1.0)

        head = k == 0
        fill = SNAKE_HEAD if head else SNAKE_BODY
        op = 1.0 if head else round(0.85 - k * 0.11, 2)
        size = CELL + (3 if head else 1)
        off = (size - CELL) / 2
        glow = ' filter="url(#g)"' if head else ""
        out.append(
            f'<g><rect x="{-off}" y="{-off}" width="{size}" height="{size}" '
            f'rx="{3 if head else 2.5}" fill="{fill}" opacity="{op}"{glow}>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="{";".join(pts)}" keyTimes="{";".join(str(t) for t in times)}" '
            f'dur="{CYCLE}s" calcMode="linear" repeatCount="indefinite"/>'
            # vanish once the board is clear, so the name holds on its own
            f'<animate attributeName="opacity" values="{op};{op};0;0" '
            f'keyTimes="0;{end_t};{gone};1" dur="{CYCLE}s" '
            f'repeatCount="indefinite"/>'
            f"</rect></g>"
        )

    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--word", default="MAKLE")
    ap.add_argument("--out", default="assets/name-snake.svg")
    ap.add_argument("--seed", type=int, default=7, help="change for a new route")
    ap.add_argument("--straightness", type=float, default=0.62,
                    help="0 = twitchy random walk, 1 = long straight runs")
    ap.add_argument("--roam", type=float, default=0.0,
                    help="chance of abandoning nearby food mid-run")
    a = ap.parse_args()
    svg = build(a.word.upper(), a.seed, a.straightness, a.roam)
    with open(a.out, "w") as fh:
        fh.write(svg)
    print(f"wrote {a.out}  ({len(svg)//1024} KB, seed={a.seed}, "
          f"straightness={a.straightness})")
