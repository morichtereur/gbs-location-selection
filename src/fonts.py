"""Typefaces, embedded as data URIs.

The page has to carry its own fonts. It is published to contexts where a strict
policy blocks every external host, so a stylesheet link to a font CDN does not
fail loudly — it falls back to a system stack, and the page quietly loses the
identity it was designed with.

Latin subsets only, and only the weights actually used: six faces, about 90 kB
before encoding. All three families are OFL-licensed; see assets/fonts/LICENSE.md.
"""

from __future__ import annotations

import base64
from functools import lru_cache

from src import config as C

FONT_DIR = C.ROOT / "assets" / "fonts"

# family, weight, file
FACES = [
    ("Archivo", 400, "archivo-400.woff2"),
    ("Archivo", 600, "archivo-600.woff2"),
    ("Archivo", 700, "archivo-700.woff2"),
    ("Source Serif 4", 400, "source-serif-400.woff2"),
    ("IBM Plex Mono", 400, "plex-mono-400.woff2"),
    ("IBM Plex Mono", 500, "plex-mono-500.woff2"),
]


@lru_cache(maxsize=1)
def face_css() -> str:
    rules = []
    for family, weight, filename in FACES:
        path = FONT_DIR / filename
        if not path.exists():
            continue
        encoded = base64.b64encode(path.read_bytes()).decode()
        rules.append(
            f"@font-face{{font-family:'{family}';font-style:normal;"
            f"font-weight:{weight};font-display:swap;"
            f"src:url(data:font/woff2;base64,{encoded}) format('woff2')}}"
        )
    return "\n".join(rules)
