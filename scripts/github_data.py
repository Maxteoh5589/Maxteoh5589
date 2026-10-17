#!/usr/bin/env python3
"""Draw the last year of GitHub contributions as an ink-wash mountain range.

Each week becomes a point on the ridge: busy weeks rise into peaks, quiet weeks
sink into misty valleys. A cinnabar dot marks the busiest day.

Standard library only. Run by .github/workflows/github-data.yml once a day.

    GITHUB_TOKEN=... python scripts/github_data.py --user Maxteoh5589
    python scripts/github_data.py --sample          # offline preview with fake data
"""
import argparse
import datetime as dt
import json
import math
import os
import random
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "github-data.svg")
FONT_CSS = os.path.join(ROOT, "scripts", "ink-fonts.css")

PAPER, MUTED, DIM, CINNABAR, BORDER = "#ebe7df", "#8f8a82", "#5f5b55", "#b5523b", "#2a2b2f"
SERIF = "LoraInk,Georgia,'Times New Roman',serif"
SANS = "InterInk,'Segoe UI',Ubuntu,Arial,sans-serif"
DIGIT_W = {"0": .626, "1": .378, "2": .536, "3": .558, "4": .544, "5": .543,
           "6": .577, "7": .464, "8": .565, "9": .577, ",": .252}

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


# ------------------------------------------------------------------ data
def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "ink-contribution-ridge"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def sample(seed=5):
    rnd = random.Random(seed)
    end = dt.date.today()
    start = end - dt.timedelta(days=364 + (end.weekday() + 1) % 7)
    weeks, cur, d = [], [], start
    level = 1.0
    while d <= end:
        level = min(4, max(0, level + rnd.uniform(-.8, .8)))
        day = (d - start).days
        burst = 7 if 285 < day < 330 else 4 if 160 < day < 185 else 0     # hackathon months
        c = max(0, int(rnd.gauss(level + burst, 2.2))) if rnd.random() < .55 else 0
        cur.append((d.isoformat(), c))
        if len(cur) == 7:
            weeks.append(cur); cur = []
        d += dt.timedelta(days=1)
    if cur:
        weeks.append(cur)
    return sum(c for w in weeks for _, c in w), weeks


# ------------------------------------------------------------------ geometry
def catmull(points):
    """Smooth path through points (Catmull-Rom -> cubic Bezier)."""
    p = [points[0]] + points + [points[-1]]
    d = f"L{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(1, len(p) - 2):
        x0, y0 = p[i - 1]; x1, y1 = p[i]; x2, y2 = p[i + 1]; x3, y3 = p[i + 2]
        c1 = (x1 + (x2 - x0) / 6, y1 + (y2 - y0) / 6)
        c2 = (x2 - (x3 - x1) / 6, y2 - (y3 - y1) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {x2:.1f},{y2:.1f}"
    return d


def jitter(points, seed, amt=1.6):
    rnd = random.Random(seed)
    out = []
    for i, (x, y) in enumerate(points):
        out.append((x, y))
        if i < len(points) - 1:                      # add a rough mid-point for a hand-drawn ridge
            nx, ny = points[i + 1]
            out.append(((x + nx) / 2, (y + ny) / 2 + rnd.uniform(-amt, amt)))
    return out


def filters():
    return """
<filter id="brush" x="-5%" y="-10%" width="110%" height="130%">
 <feTurbulence type="fractalNoise" baseFrequency="0.022 0.06" numOctaves="3" seed="3" result="n"/>
 <feDisplacementMap in="SourceGraphic" in2="n" scale="10" xChannelSelector="R" yChannelSelector="G" result="d"/>
 <feTurbulence type="fractalNoise" baseFrequency="0.045 0.07" numOctaves="4" seed="7" result="g"/>
 <feColorMatrix in="g" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -2.2 1.9" result="ga"/>
 <feComposite in="d" in2="ga" operator="in"/>
</filter>
<filter id="bleed" x="-10%" y="-20%" width="120%" height="140%">
 <feTurbulence type="fractalNoise" baseFrequency="0.02 0.05" numOctaves="2" seed="9" result="n"/>
 <feDisplacementMap in="SourceGraphic" in2="n" scale="16" xChannelSelector="R" yChannelSelector="G" result="d"/>
 <feGaussianBlur in="d" stdDeviation="5"/>
</filter>
<filter id="mist" x="-20%" y="-60%" width="140%" height="220%">
 <feTurbulence type="fractalNoise" baseFrequency="0.008 0.03" numOctaves="3" seed="5" result="n"/>
 <feDisplacementMap in="SourceGraphic" in2="n" scale="40" xChannelSelector="R" yChannelSelector="G" result="d"/>
 <feGaussianBlur in="d" stdDeviation="9"/>
</filter>
<filter id="stroke" x="-5%" y="-30%" width="110%" height="160%">
 <feTurbulence type="fractalNoise" baseFrequency="0.04 0.5" numOctaves="2" seed="10" result="n"/>
 <feDisplacementMap in="SourceGraphic" in2="n" scale="4" xChannelSelector="R" yChannelSelector="G" result="d"/>
 <feTurbulence type="fractalNoise" baseFrequency="0.01 0.9" numOctaves="1" seed="11" result="g"/>
 <feColorMatrix in="g" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -2 1.8" result="ga"/>
 <feComposite in="d" in2="ga" operator="in"/>
</filter>
<filter id="rough" x="-5%" y="-20%" width="110%" height="140%">
 <feTurbulence type="fractalNoise" baseFrequency="0.08" numOctaves="2" seed="8" result="n"/>
 <feDisplacementMap in="SourceGraphic" in2="n" scale="3" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<filter id="soft"><feGaussianBlur stdDeviation="1.2"/></filter>
<filter id="paper" x="0" y="0" width="100%" height="100%">
 <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="3" seed="4" result="n"/>
 <feColorMatrix in="n" type="matrix" values="0 0 0 0 0.92 0 0 0 0 0.9 0 0 0 0 0.87 0 0 0 0.055 0"/>
 <feComposite operator="in" in2="SourceGraphic"/>
</filter>"""


def fmt_int(n):
    return f"{n:,}"


def fmt_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b')} {d.year}"


# ------------------------------------------------------------------ draw
def draw(total, weeks, user):
    W, H = 1000, 318
    X0, X1, BASE, HMAX = 40, 960, 254, 126
    counts = [sum(c for _, c in w) for w in weeks]
    n = len(counts)
    peak = max(counts) or 1
    step = (X1 - X0) / max(1, n - 1)

    def hy(v, scale=1.0):
        return BASE - (6 + math.sqrt(v / peak) * (HMAX - 6)) * scale if v else BASE - 4

    near = [(X0 + i * step, hy(v)) for i, v in enumerate(counts)]
    avg = [sum(counts[max(0, i - 3):i + 4]) / len(counts[max(0, i - 3):i + 4]) for i in range(n)]
    far = [(X0 + i * step, hy(a, 1.12) - 12) for i, a in enumerate(avg)]

    near = [(X0 - 40, BASE - 2)] + near + [(X1 + 40, BASE - 2)]
    far = [(X0 - 40, BASE - 8)] + far + [(X1 + 40, BASE - 8)]
    near_j = jitter(near, 2)
    ridge_d = catmull(near_j)
    near_fill = f"M{X0-40},{BASE+30} " + ridge_d + f" L{X1+40},{BASE+30} Z"
    far = [(X0 - 80, BASE - 8)] + far[1:-1] + [(X1 + 80, BASE - 8)]
    far_fill = f"M{X0-80},{BASE+30} " + catmull(far) + f" L{X1+80},{BASE+30} Z"

    # busiest day
    best_date, best_count, best_week = None, -1, 0
    for wi, w in enumerate(weeks):
        for date, c in w:
            if c > best_count:
                best_date, best_count, best_week = date, c, wi
    bx, by = near[best_week + 1]

    # moss dots on high ground, mist in the quietest valleys
    rnd = random.Random(7)
    moss = ""
    for (x, y), v in zip(near[1:-1], counts):
        if v > peak * .45:
            for _ in range(2):
                moss += (f'<ellipse cx="{x + rnd.uniform(-5, 5):.1f}" cy="{y + rnd.uniform(4, 16):.1f}" '
                         f'rx="{rnd.uniform(1, 2.2):.1f}" ry="{rnd.uniform(.8, 1.4):.1f}" fill="{PAPER}" opacity="{rnd.uniform(.35, .75):.2f}"/>')
    lows = sorted(range(n), key=lambda i: sum(counts[max(0, i - 2):i + 3]))
    picked = []
    for i in lows:
        if all(abs(i - j) > 9 for j in picked):
            picked.append(i)
        if len(picked) == 3:
            break
    mist = "".join(f'<g class="m{k}"><ellipse cx="{X0 + i*step:.0f}" cy="{BASE - 22}" rx="120" ry="16" fill="{PAPER}" '
                   f'opacity=".10" filter="url(#mist)"/></g>' for k, i in enumerate(picked))

    # month labels
    months, last = "", None
    for wi, w in enumerate(weeks):
        d = dt.date.fromisoformat(w[0][0])
        if d.month != last and d.day <= 7 and wi > 0:
            months += f'<text x="{X0 + wi*step:.0f}" y="{BASE + 44}" class="mo" text-anchor="middle">{d.strftime("%b")}</text>'
        last = d.month

    ripples = ""
    for _ in range(26):
        x, y = rnd.uniform(X0, X1), rnd.uniform(BASE + 6, BASE + 22)
        w_ = rnd.uniform(18, 70)
        ripples += (f'<path d="M{x:.0f},{y:.0f} q{w_/2:.0f},{rnd.uniform(-1.2,1.2):.1f} {w_:.0f},0" stroke="{PAPER}" '
                    f'stroke-width="{rnd.uniform(.6,1.2):.1f}" fill="none" opacity="{rnd.uniform(.1,.3):.2f}"/>')

    motes = ""
    for _ in range(18):
        motes += (f'<circle class="mote" cx="{rnd.uniform(30, 970):.0f}" cy="{rnd.uniform(110, H):.0f}" r="{rnd.uniform(.8, 2):.1f}" '
                  f'fill="{PAPER}" filter="url(#soft)" style="animation-duration:{rnd.uniform(9, 18):.1f}s;'
                  f'animation-delay:-{rnd.uniform(0, 18):.1f}s"/>')
    num = fmt_int(total)
    num_w = sum(DIGIT_W.get(c, .55) for c in num) * 46
    if best_count > 0:
        anchor_end = bx > 720
        lx = bx - 14 if anchor_end else bx + 14
        label = (f'<text x="{lx:.0f}" y="{by - 10:.0f}" class="best" text-anchor="{"end" if anchor_end else "start"}">'
                 f'busiest day · {fmt_date(best_date)} · {best_count}</text>')
        marker = (f'<circle class="ripple" cx="{bx:.1f}" cy="{by:.1f}" r="6" fill="none" stroke="{PAPER}" stroke-width="1"/>'
                  f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="5" fill="{CINNABAR}" filter="url(#soft)"/>')
    else:
        label = f'<text x="500" y="{BASE - 40}" class="best" text-anchor="middle">quiet waters, the first commit is still ahead</text>'
        marker = ""

    updated = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y")
    style = f"""{open(FONT_CSS).read() if os.path.exists(FONT_CSS) else ''}
.lbl{{font:600 12px {SANS};fill:{MUTED};letter-spacing:2.4px}}
.num{{font:500 46px {SERIF};fill:{PAPER}}}
.it{{font:italic 400 18px {SERIF};fill:#b5b0a6}}
.best{{font:italic 400 15px {SERIF};fill:{PAPER}}}
.mo{{font:500 12.5px {SANS};fill:{DIM};letter-spacing:1px}}
.foot{{font:italic 400 14px {SERIF};fill:{DIM}}}
.par{{animation:par 30s ease-in-out infinite alternate}}
@keyframes par{{from{{transform:translateX(-12px)}}to{{transform:translateX(12px)}}}}
.flow{{animation:flow 9s ease-in-out infinite alternate}}
@keyframes flow{{from{{transform:translateX(-14px)}}to{{transform:translateX(14px)}}}}
.mote{{animation:rise 12s linear infinite;opacity:0}}
@keyframes rise{{0%{{transform:translate(0,0);opacity:0}}15%{{opacity:.7}}85%{{opacity:.5}}100%{{transform:translate(22px,-70px);opacity:0}}}}
.m0{{animation:dr 26s ease-in-out infinite alternate}}
.m1{{animation:dr 32s ease-in-out infinite alternate-reverse}}
.m2{{animation:dr 38s ease-in-out infinite alternate}}
@keyframes dr{{from{{transform:translateX(-30px)}}to{{transform:translateX(30px)}}}}
.ripple{{transform-box:fill-box;transform-origin:center;animation:rp 3.2s ease-out infinite}}
@keyframes rp{{from{{transform:scale(.6);opacity:.7}}to{{transform:scale(2.8);opacity:0}}}}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}"""

    body = f"""<defs>{filters()}
<linearGradient id="gNear" x1="0" y1="{BASE-HMAX}" x2="0" y2="{BASE+6}" gradientUnits="userSpaceOnUse">
 <stop offset="0" stop-color="{PAPER}" stop-opacity=".72"/><stop offset=".45" stop-color="{PAPER}" stop-opacity=".22"/>
 <stop offset="1" stop-color="{PAPER}" stop-opacity="0"/></linearGradient>
<linearGradient id="gFar" x1="0" y1="{BASE-HMAX-20}" x2="0" y2="{BASE}" gradientUnits="userSpaceOnUse">
 <stop offset="0" stop-color="{PAPER}" stop-opacity=".26"/><stop offset="1" stop-color="{PAPER}" stop-opacity="0"/></linearGradient>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b0c0e"/><stop offset="1" stop-color="#131417"/></linearGradient>
<clipPath id="cl"><rect width="{W}" height="{H}" rx="14"/></clipPath>

</defs>
<g clip-path="url(#cl)"><rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="#fff" filter="url(#paper)"/>
<g>
<g class="par"><path d="{far_fill}" fill="url(#gFar)" filter="url(#bleed)"/></g>
{mist}
<path d="{near_fill}" fill="url(#gNear)" filter="url(#bleed)" opacity=".6"/>
<path d="{near_fill}" fill="url(#gNear)" filter="url(#brush)"/>
<path d="M{ridge_d[1:]}" fill="none" stroke="{PAPER}" stroke-width="2.4" opacity=".85" filter="url(#stroke)"/>
{moss}
<g class="flow" filter="url(#rough)">{ripples}</g>
{motes}
{marker}{label}
</g>
<path d="M{X0},{BASE + 2} L{X1},{BASE + 2}" stroke="{PAPER}" stroke-width="1" opacity=".18"/>
{months}
<text x="40" y="48" class="lbl">CONTRIBUTIONS · LAST 12 MONTHS</text>
<text x="38" y="100" class="num">{num}</text>
<text x="{38 + num_w + 14:.0f}" y="100" class="it">contributions</text>
<text x="{W-40}" y="48" class="foot" text-anchor="end">each peak is one week · updated {updated}</text>
</g><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{BORDER}"/>"""

    title = f"{user}: {num} contributions in the last year"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{title}"><title>{title}</title><style>{style}</style>{body}</svg>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GH_USER", "Maxteoh5589"))
    ap.add_argument("--sample", action="store_true", help="use fake data (offline preview)")
    ap.add_argument("--empty", action="store_true", help="preview the zero-contribution state")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    if a.sample or a.empty:
        total, weeks = sample()
        if a.empty:
            weeks = [[(d, 0) for d, _ in w] for w in weeks]
            total = 0
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("Set GITHUB_TOKEN (the Action provides it automatically).")
        total, weeks = fetch(a.user, token)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(draw(total, weeks, a.user))
    print(f"wrote {a.out}: {total} contributions over {len(weeks)} weeks")


if __name__ == "__main__":
    main()
