#!/usr/bin/env python3
"""
Render the whole toolkit as ONE svg.

Why one image: GitHub's marketing bundle (loaded on every SIGNED-OUT page)
ships an unscoped `img,picture{max-width:100%;display:block}`. It leaks onto
README images and blockifies them, so a row of separate <img> badges collapses
to one per line for anyone not logged in. A single image is immune — being
display:block changes nothing when it is alone on its line.

Fit: every chip uses the SAME type size, so uniformity comes from the row
BREAKS, not from scaling rows differently (scaling would make the type size
differ row to row). Each row's leftover space is shared out equally as extra
chip padding, so rows span the full width and chips stay visually consistent.
Row breaks are chosen by DP over the ordered list to minimise the variance of
leftover space — the flattest possible packing that keeps the grouping intact.

  python3 tools/make-toolkit.py --fetch      # cache logos (network)
  python3 tools/make-toolkit.py --measure    # emit label-measuring page
  python3 tools/make-toolkit.py --build W    # W = measured widths json
"""

import argparse, base64, json, os, re, urllib.request

TOTAL = 1584                 # banner's viewBox width, so both scale alike
FONT, LS = 21, 2.6           # label type size / letter-spacing
ICON, ICON_GAP = 24, 12
PAD_MIN = 26                 # minimum padding each side of a chip
CHIP_H, ROW_GAP, CHIP_GAP = 58, 12, 10
PAD_X, PAD_Y = 0, 0
RADIUS = 8
BG, CHIP_BG, TEXT = "#0D1117", "#0A0A0A", "#FFFFFF"

TOOLS = [
    ("TypeScript","typescript","3178C6"), ("JavaScript","javascript","F7DF1E"),
    ("Python","python","3776AB"), ("React","react","61DAFB"),
    ("Next.js","nextdotjs","FFFFFF"), ("Astro","astro","BC52EE"),
    ("Node.js","nodedotjs","5FA04E"), ("Tailwind","tailwindcss","06B6D4"),
    ("shadcn/ui","shadcnui","FFFFFF"), ("Vite","vite","646CFF"),
    ("Vitest","vitest","6E9F18"),
    ("Three.js","threedotjs","FFFFFF"), ("Remotion","react","4A9EFF"),
    ("Framer Motion","framer","0055FF"), ("GSAP","greensock","88CE02"),
    ("Matter.js","matterdotjs","FFFFFF"), ("SVG","svg","FFB13B"),
    ("Electron","electron","6FD5E8"), ("React Flow","xyflow","FF0072"),
    ("Drizzle","drizzle","C5F74F"), ("SQLite","sqlite","4DA8DA"),
    ("Figma","figma","F24E1E"), ("Illustrator","adobe","FF9A00"),
    ("Sanity","sanity","F03E2F"), ("Cloudflare","cloudflare","F38020"),
    ("Netlify","netlify","00C7B7"),
]

SANS = "'Segoe UI','Helvetica Neue',Helvetica,Arial,sans-serif"
CACHE = "tools/logos.json"


def fetch():
    logos = {}
    for label, lg, color in TOOLS:
        url = ("https://img.shields.io/badge/x-000?style=for-the-badge"
               f"&logo={lg}&logoColor={color}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        svg = urllib.request.urlopen(req, timeout=25).read().decode()
        m = re.search(r'(?:xlink:)?href="(data:image/svg\+xml;base64,[A-Za-z0-9+/=]+)"', svg)
        if m:
            logos[label] = m.group(1)
        else:
            print(f"  no logo: {label} ({lg}) — renders text-only")
    json.dump(logos, open(CACHE, "w"))
    print(f"cached {len(logos)}/{len(TOOLS)} logos")


def measure_page():
    labels = [t[0] for t in TOOLS]
    texts = "".join(
        f'<text id="t{i}" font-family="{SANS}" font-size="{FONT}" '
        f'font-weight="700" letter-spacing="{LS}">{l.upper()}</text>'
        for i, l in enumerate(labels))
    html = (f'<meta charset="utf-8"><title>measure</title>'
            f'<svg id="s" width="10" height="10">{texts}</svg>'
            f'<script>window.measure=()=>JSON.stringify({json.dumps(labels)}'
            f'.map((l,i)=>[l,document.getElementById("t"+i).getComputedTextLength()]));</script>')
    open("tools/measure.html", "w").write(html)
    print("wrote tools/measure.html")


def natural(label, w, has_logo):
    """Width a chip wants at minimum padding."""
    return PAD_MIN * 2 + (ICON + ICON_GAP if has_logo else 0) + w


def partition(nat, rows):
    """
    Split the ordered chips into `rows` contiguous rows, minimising the
    variance of leftover space. Leftover is what gets shared into padding, so
    flat leftovers == chips that look consistently sized across the whole grid.
    """
    n = len(nat)
    INF = float("inf")
    # cost of a row covering [i, j)
    def cost(i, j):
        content = sum(nat[i:j]) + CHIP_GAP * (j - i - 1)
        slack = TOTAL - content
        if slack < 0:
            return INF                      # does not fit
        return (slack / (j - i)) ** 2       # per-chip padding growth, squared
    dp = [[INF] * (rows + 1) for _ in range(n + 1)]
    back = [[None] * (rows + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    for r in range(1, rows + 1):
        for j in range(1, n + 1):
            for i in range(r - 1, j):
                if dp[i][r - 1] == INF:
                    continue
                c = cost(i, j)
                if c == INF:
                    continue
                v = dp[i][r - 1] + c
                if v < dp[j][r]:
                    dp[j][r] = v
                    back[j][r] = i
    if dp[n][rows] == INF:
        return None, INF
    out, j = [], n
    for r in range(rows, 0, -1):
        i = back[j][r]
        out.append((i, j))
        j = i
    return list(reversed(out)), dp[n][rows]


def slack_per_chip(row, nat):
    content = sum(nat[k] for k in row) + CHIP_GAP * (len(row) - 1)
    return (TOTAL - content) / len(row), TOTAL - content


def spread_of(groups, nat):
    per = [slack_per_chip(g, nat)[0] for g in groups]
    if any(slack_per_chip(g, nat)[1] < 0 for g in groups):
        return float("inf")
    return max(per) - min(per)


def optimise(groups, nat, rounds=80000, adjacent_only=True):
    """
    Local search over which row each chip sits in, to flatten the per-chip
    padding (and so the apparent chip size) across every row.

    adjacent_only limits moves to neighbouring rows. Unconstrained search hits
    a spread of ~0 but shuffles the list globally — Figma lands beside Vite and
    the grid reads as a random tag cloud. Restricting to neighbours keeps the
    grouping (languages, front-end, motion, data, design) legible while still
    balancing the rows. Rows are re-sorted into original order afterwards.
    """
    import random
    rnd = random.Random(11)
    best = [list(g) for g in groups]
    best_s = spread_of(best, nat)
    cur, cur_s = [list(g) for g in best], best_s
    n = len(cur)
    for _ in range(rounds):
        if adjacent_only:
            a = rnd.randrange(n - 1)
            b = a + 1
            if rnd.random() < 0.5:
                a, b = b, a
        else:
            a, b = rnd.sample(range(n), 2)
        if not cur[a]:
            continue
        cand = [list(g) for g in cur]
        if rnd.random() < 0.5 and cur[b]:          # swap one chip each way
            i, j = rnd.randrange(len(cand[a])), rnd.randrange(len(cand[b]))
            cand[a][i], cand[b][j] = cand[b][j], cand[a][i]
        else:                                       # move a chip across
            if len(cand[a]) <= 2:
                continue
            cand[b].append(cand[a].pop(rnd.randrange(len(cand[a]))))
        s = spread_of(cand, nat)
        if s <= cur_s:
            cur, cur_s = cand, s
            if s < best_s:
                best, best_s = [list(g) for g in cand], s
    return [sorted(g) for g in best], best_s


BALANCE = False


def build(widths):
    logos = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    nat = [natural(l, widths[l], l in logos) for l, _, _ in TOOLS]

    best = None
    for rows in range(3, 8):
        cuts, _ = partition(nat, rows)
        if cuts is None:
            continue
        groups = [list(range(i, j)) for i, j in cuts]
        s0 = spread_of(groups, nat)
        # Order-preserving by default. The local search reaches a spread of
        # ~2, but the difference is invisible at render size while the
        # reordering is not: it scatters the grouping into a random tag
        # cloud. Legibility wins over a metric nobody can see.
        groups, s1 = (optimise(groups, nat) if BALANCE else (groups, s0))
        per = [slack_per_chip(g, nat)[0] for g in groups]
        print(f"  {rows} rows -> {[len(g) for g in groups]} chips  "
              f"padding/chip {[round(p) for p in per]}  "
              f"spread {s0:.0f} -> {s1:.0f}")
        if best is None or s1 < best[0]:
            best = (s1, rows, groups, per)

    spread, rows, cuts, per = best
    print(f"\nchosen: {rows} rows, padding spread {spread:.1f} units")

    H = rows * CHIP_H + (rows - 1) * ROW_GAP
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TOTAL} {H}" '
           f'width="{TOTAL}" height="{H}" role="img" '
           f'aria-label="Toolkit: {", ".join(t[0] for t in TOOLS)}">',
           "<title>Toolkit</title>"]

    for r, (group, extra) in enumerate(zip(cuts, per)):
        y = r * (CHIP_H + ROW_GAP)
        x = 0.0
        for k in group:
            label = TOOLS[k][0]
            has = label in logos
            w = nat[k] + extra                      # share the slack evenly
            inner = (ICON + ICON_GAP if has else 0) + widths[label]
            ix = x + (w - inner) / 2
            out.append(f'<rect x="{x:.2f}" y="{y}" width="{w:.2f}" height="{CHIP_H}" '
                       f'rx="{RADIUS}" fill="{CHIP_BG}"/>')
            if has:
                out.append(f'<image x="{ix:.2f}" y="{y + (CHIP_H-ICON)/2}" '
                           f'width="{ICON}" height="{ICON}" href="{logos[label]}"/>')
            out.append(f'<text x="{ix + (ICON+ICON_GAP if has else 0):.2f}" '
                       f'y="{y + CHIP_H/2 + FONT*0.35:.1f}" font-family="{SANS}" '
                       f'font-size="{FONT}" font-weight="700" letter-spacing="{LS}" '
                       f'fill="{TEXT}">{label.upper()}</text>')
            x += w + CHIP_GAP
        # rows must land exactly on the right edge
        assert abs(x - CHIP_GAP - TOTAL) < 0.5, f"row {r} ends at {x-CHIP_GAP}, want {TOTAL}"

    out.append("</svg>")
    svg = "\n".join(out)
    open("assets/toolkit.svg", "w").write(svg)
    print(f"wrote assets/toolkit.svg ({len(svg)//1024} KB, {TOTAL}x{H})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--build", metavar="WIDTHS")
    ap.add_argument("--balance", action="store_true",
                    help="flatten padding by reordering (scrambles grouping)")
    a = ap.parse_args()
    BALANCE = a.balance
    if a.fetch: fetch()
    if a.measure: measure_page()
    if a.build:
        globals()["BALANCE"] = a.balance
        build(dict(json.load(open(a.build))))
