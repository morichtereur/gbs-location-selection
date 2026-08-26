"""The link-preview card: Exhibit 1 at the declared starting weights.

A page whose whole claim is that some cities cannot be separated should not be
shared as a bare title and a URL. The card carries the finding — the top band
named, and the bands drawn as bands — so the argument survives being pasted
into a channel where nobody clicks through.

Drawn with matplotlib rather than by screenshotting the page, because a
headless browser is a local convenience here (`make shot`) and not something
`make dashboard` or CI can rely on. The cost is that this is a second rendering
of Exhibit 1 and can drift from the first; what keeps it honest is that both
read the same scenario out of `src/fallback.Scenario`, so the ordering, the
bands and the scores cannot diverge — only the drawing can.

1200x630 is the size every crawler crops to.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src import config as C
from src.fallback import Scenario

# The page's own paper and ink, so the card and the thing it links to are
# recognisably one object.
PAPER = "#e9eae4"
INK = "#121a17"
INK_2 = "#4d554f"
INK_3 = "#7d857e"
RULE = "#b6b9ae"
ACCENT = "#146b54"
REST = "#b9b9b4"

WIDTH, HEIGHT, DPI = 1200, 630, 100


def _font() -> dict:
    """Whatever of the page's families matplotlib can find, then a sane fallback."""
    return {"family": ["Archivo", "Helvetica Neue", "Helvetica", "DejaVu Sans"]}


def render(data: dict, path=None):
    """Draw the card for the declared scenario and return the path written."""
    path = path or (C.DATA / "og.png")
    s = Scenario(data)
    rows = s.order
    best = max(s.scores.values()) or 1.0

    fig = plt.figure(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI, facecolor=PAPER)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(HEIGHT, 0)
    ax.axis("off")

    snap = data["provenance"]["postings"]
    eyebrow = f"{len(rows)} GBS AND GCC CITIES  ·  {len(s.weights)} PILLARS"
    if snap:
        eyebrow += f"  ·  ONE SNAPSHOT, {snap['dateLabel'].upper()}"
    ax.text(64, 62, " ".join(eyebrow), color=INK_3, fontsize=9.5, va="center",
            fontfamily=["IBM Plex Mono", "DejaVu Sans Mono", "monospace"])

    top = [r["name"] for r in s.top]
    headline = (
        f"{len(top)} cities finish level at the top."
        if len(top) > 1 else f"{rows[0]['name']} leads outright."
    )
    ax.text(64, 118, headline, color=INK, fontsize=34, va="center",
            fontweight="bold", **_font())

    sub = (
        f"{', '.join(top[:-1])} and {top[-1]} — the draws cannot separate them."
        if len(top) > 1
        else f"Holding a top-three place in {s.freq.get(rows[0]['id'], 0) * 100:.0f}% of runs."
    )
    ax.text(64, 162, sub, color=INK_2, fontsize=15.5, va="center",
            fontfamily=["Source Serif 4", "Georgia", "DejaVu Serif", "serif"])

    ax.add_line(plt.Line2D([64, WIDTH - 64], [196, 196], color=RULE, linewidth=1))

    # The bars. Band, not rank, decides the tone: the card should carry the
    # same refusal to order what the evidence cannot.
    # Wide enough for the longest name in the panel — Johannesburg ran
    # under the bars at 232.
    x0, x1 = 286, WIDTH - 168
    top_y, row_h = 232, 33
    for i, r in enumerate(rows):
        y = top_y + i * row_h
        band = s.band.get(r["id"], 1)
        lead = band == 1
        if lead:
            ax.add_patch(Rectangle((64, y - 13), 5, 26, color=ACCENT, lw=0))
        ax.text(84, y, str(band) if (i == 0 or s.band.get(rows[i - 1]["id"]) != band)
                else "", color=INK_3, fontsize=11, va="center", ha="left",
                fontfamily=["IBM Plex Mono", "DejaVu Sans Mono", "monospace"])
        ax.text(108, y, r["name"], color=INK if lead else INK_2,
                fontsize=14.5, va="center",
                fontweight="bold" if lead else "normal", **_font())
        w = (s.scores[r["id"]] / best) * (x1 - x0)
        ax.add_patch(Rectangle((x0, y - 8), w, 16,
                               color=ACCENT if lead else REST, lw=0))
        ax.text(WIDTH - 160, y, f"{s.freq.get(r['id'], 0.0) * 100:.0f}%",
                color=INK_2, fontsize=12.5, va="center", ha="left",
                fontfamily=["IBM Plex Mono", "DejaVu Sans Mono", "monospace"])

    ax.text(64, HEIGHT - 32,
            "Seven pillars of public data, re-ranked across 2,000 defensible weightings",
            color=INK_3, fontsize=11, va="center",
            fontfamily=["IBM Plex Mono", "DejaVu Sans Mono", "monospace"])
    ax.text(WIDTH - 64, HEIGHT - 32,
            C.PUBLISHED_URL.replace("https://", "").rstrip("/"),
            color=INK_3, fontsize=11, va="center", ha="right",
            fontfamily=["IBM Plex Mono", "DejaVu Sans Mono", "monospace"])

    fig.savefig(path, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return path


def main() -> None:
    from src.dashboard import payload

    path = render(payload())
    print(f"wrote {path.name} ({path.stat().st_size / 1024:.0f} kB)")


if __name__ == "__main__":
    main()
