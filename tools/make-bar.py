#!/usr/bin/env python3
"""
Build the link bar that sits under the banner.

Emitted as THREE svgs, not one, so each segment can carry its own href — a
single <img> can only ever be one link target, and SVG-internal <a> elements
are inert when the SVG is embedded via <img>.

Keeping them aligned is the whole trick:
  * every piece shares the same viewBox HEIGHT, and its viewBox WIDTH is its
    share of the banner's 1584 units;
  * each <img> gets width="<share>%" (percentages survive GitHub's sanitizer,
    fractions included).
Rendered height is then (share x column) x (H / shareWidth) = column x H/1584
for all three — identical by construction, at any column width. The pieces
also total the banner's width, because the shares total 1584.

Emit the README snippet with --snippet. The three <a> tags MUST stay on one
line with no whitespace between them: images are inline, so a newline becomes
a space, and 100% + spaces wraps the last piece onto its own row.
"""

import argparse

TOTAL, H = 1584, 74          # TOTAL matches banner.png's viewBox width
BLACK, GOLD, BRONZE = "#0A0A0A", "#EFC38F", "#9E7F5F"
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"

K_SIZE, V_SIZE = 19, 22
K_LS, V_LS = 3.6, 4.2

# (file, width, kicker, value, filled, href, divider-on-left)
SEGMENTS = [
    ("link-bar-1.svg", 600, "PORTFOLIO", "MAKLERICHARDS.COM", False,
     "https://www.maklerichards.com", False),
    ("link-bar-2.svg", 490, "AGENCY", "PROSPECT FUTURE", False,
     "https://github.com/Prospect-Future", True),
    ("link-bar-3.svg", 494, None, "1,000+ CONTRIBUTIONS", True, None, False),
]


def piece(w, kicker, value, filled, divider):
    mid = w / 2
    body = [f'<rect width="{w}" height="{H}" fill="{GOLD if filled else BLACK}"/>']
    if filled:
        body.append(
            f'<text x="{mid}" y="47" text-anchor="middle" font-family="{SANS}" '
            f'font-size="{V_SIZE}" font-weight="700" letter-spacing="{V_LS}" '
            f'fill="{BLACK}">{value}</text>')
    else:
        # One <text> with two <tspan>s so the browser measures and centres the
        # pair; estimating glyph widths made the labels collide.
        body.append(
            f'<text x="{mid}" y="47" text-anchor="middle" font-family="{SANS}">'
            f'<tspan font-size="{K_SIZE}" font-weight="600" letter-spacing="{K_LS}" '
            f'fill="{BRONZE}">{kicker} </tspan>'
            f'<tspan font-size="{V_SIZE}" font-weight="700" letter-spacing="{V_LS}" '
            f'fill="#FFFFFF">{value}</tspan></text>')
    if divider:
        body.append(f'<rect x="0" y="16" width="2" height="{H-32}" '
                    f'fill="{BRONZE}" opacity="0.55"/>')
    label = f"{kicker} {value}" if kicker else value
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {H}" '
            f'width="{w}" height="{H}" role="img" aria-label="{label}">'
            + "".join(body) + "</svg>")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--snippet", action="store_true")
    a = ap.parse_args()

    assert sum(s[1] for s in SEGMENTS) == TOTAL, "shares must total the banner width"

    tags = []
    for fname, w, kicker, value, filled, href, divider in SEGMENTS:
        with open(f"assets/{fname}", "w") as fh:
            fh.write(piece(w, kicker, value, filled, divider))
        pct = round(w / TOTAL * 100, 3)
        alt = f"{kicker}: {value}" if kicker else value
        url = f"https://raw.githubusercontent.com/King-Makle/King-Makle/main/assets/{fname}"
        img = f'<img src="{url}" width="{pct}%" alt="{alt}" />'
        tags.append(f'<a href="{href}">{img}</a>' if href else img)
        print(f"wrote assets/{fname:<16} {w:>4} units  ->  width=\"{pct}%\"")

    if a.snippet:
        print("\n--- README snippet (single line, no spaces between tags) ---")
        print("".join(tags))
