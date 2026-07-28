#!/usr/bin/env python3
"""
Build the link bar that sits under the banner.

Three fixed-width shields.io badges can never add up to exactly the banner's
width, because the banner is width="100%" and reflows with the column. So this
draws the bar as ONE svg on the banner's own 1584-unit viewBox: set both to
width="100%" and they render identically wide at any column size, forever.

Trade-off: one <img> means one link target, so the bar links to the portfolio.
"""

W, H = 1584, 74          # same viewBox width as banner.png -> identical scaling
BLACK, GOLD, BRONZE = "#0A0A0A", "#EFC38F", "#9E7F5F"
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"

# segment boundaries; last one is the filled highlight
SEGMENTS = [
    (0,    600,  "PORTFOLIO", "MAKLERICHARDS.COM", False),
    (600,  1090, "AGENCY",    "PROSPECT FUTURE",   False),
    (1090, W,    None,        "1,000+ CONTRIBUTIONS", True),
]

K_SIZE, V_SIZE = 19, 22          # kicker / value type sizes
K_LS,  V_LS = 3.6, 4.2           # letter-spacing


def build():
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="Portfolio maklerichards.com | Agency Prospect Future | '
        f'1,000+ contributions this year">',
        '<title>Makle Richards — links</title>',
        f'<rect width="{W}" height="{H}" fill="{BLACK}"/>',
    ]
    for x0, x1, kicker, value, filled in SEGMENTS:
        mid = (x0 + x1) / 2
        if filled:
            out.append(f'<rect x="{x0}" y="0" width="{x1-x0}" height="{H}" fill="{GOLD}"/>')
            out.append(
                f'<text x="{mid}" y="47" text-anchor="middle" font-family="{SANS}" '
                f'font-size="{V_SIZE}" font-weight="700" letter-spacing="{V_LS}" '
                f'fill="{BLACK}">{value}</text>')
        else:
            # One <text> with two <tspan>s: the browser measures and centres the
            # pair itself, so no glyph-width guessing (which is what broke the
            # first attempt - estimates ran long and the labels collided).
            out.append(
                f'<text x="{mid}" y="47" text-anchor="middle" font-family="{SANS}">'
                f'<tspan font-size="{K_SIZE}" font-weight="600" letter-spacing="{K_LS}" '
                f'fill="{BRONZE}">{kicker} </tspan>'
                f'<tspan font-size="{V_SIZE}" font-weight="700" letter-spacing="{V_LS}" '
                f'fill="#FFFFFF">{value}</tspan></text>')

    # hairline dividers between segments, in the banner's gold
    for x0, _, _, _, _ in SEGMENTS[1:]:
        out.append(f'<rect x="{x0-1}" y="16" width="2" height="{H-32}" '
                   f'fill="{BRONZE}" opacity="0.55"/>')

    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    svg = build()
    with open("assets/link-bar.svg", "w") as fh:
        fh.write(svg)
    print(f"wrote assets/link-bar.svg ({len(svg)} bytes, viewBox {W}x{H})")
