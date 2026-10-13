#!/usr/bin/env python3
"""Derive resources/themes/Nordic.theme.json from RustRover's own "Islands Darcula" UI theme.

The structure (keys, arcs, insets, icon palette) is kept exactly as JetBrains ships it, so the
theme is guaranteed to have a shape the IDE understands; only colours are replaced:
  * the named palette in "colors" is mapped explicitly onto nordic.nvim roles
    (islands = editor bg, window frame = statusline black0, popups = float black1, ...)
  * remaining literal colours are mapped by role: neutrals onto nordic's gray ramp by
    luminance, chromatic colours onto the nearest nordic accent at matching luminance.

    python3 tools/derive_ui_theme.py [/Applications/RustRover.app]
"""
import colorsys
import io
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from build import P, blend  # noqa: E402

APP = sys.argv[1] if len(sys.argv) > 1 else '/Applications/RustRover.app'
JAR = os.path.join(APP, 'Contents/lib/intellij.platform.ide.impl.jar')
SRC = 'themes/islands/ManyIslandsDarcula.theme.json'
OUT = os.path.join(HERE, 'resources/themes/Nordic.theme.json')

NAMED = {
    'Gray3': P['gray2'], 'Gray2.5': blend(P['gray2'], P['gray1'], 0.5), 'Gray2.25': P['gray1'],
    'Gray2': blend(P['gray1'], P['gray0'], 0.5), 'Gray1.5': P['gray0'], 'Gray1.25': P['black2'],
    'Gray1': P['black1'], 'Gray0.75': P['black0'], 'Gray0.5': '171A21', 'Gray0.25': '15181E', 'Gray0': '000000',
    'ForegroundDefault': P['white0'],
    'BackgroundDark': P['gray0'],          # tool-window islands = editor background (nvim-tree uses Normal bg)
    'BackgroundMid': P['gray0'],
    'BackgroundLight': P['black0'],        # window frame / toolbar / status bar = StatusLine bg
    'BackgroundLightest': P['gray2'],
    'AltBackgroundLight': P['gray1'],
    'BorderLight': P['gray2'], 'BorderDark': P['gray1'],
    'ComponentBorder': P['gray3'], 'ComponentBorderFocus': P['blue0'], 'ComponentBorderDisabled': P['gray1'],
    'PopupBackground': P['black1'],        # NormalFloat / Pmenu
    'PopupBackgroundLight': P['gray1'], 'PopupBorder': P['gray2'],
    'TooltipBackground': P['black1'], 'TooltipBorder': P['gray2'],
    'SelectionActive': P['gray2'],         # PmenuSel / TreeCursorLine (bg_selected)
    'SelectionActiveLight': P['gray2'],
    'SelectionInactive': P['gray1'],
}
LITERAL = {  # frequently used literals with a clear role
    '3C3F41': P['black0'],                 # MainWindow.background etc. (frame)
    '2B2B2B': P['gray0'],                  # island / editor tabs background
    '131314': '15181E',
    'BBBBBB': P['white0'],
    'FFFFFF': P['white3'],
    '000000': '000000',
}
NEUTRAL_RAMP = [  # (source luminance anchor, nordic colour)
    ('000000', '000000'), ('131314', '15181E'), ('191A1C', P['black0']), ('1E1F22', P['black1']),
    ('2B2B2B', P['gray0']), ('393B40', P['gray2']), ('4E5157', P['gray4']), ('6F737A', P['gray5']),
    ('9DA0A8', blend(P['white0'], P['gray5'], 0.6)), ('BBBBBB', P['white0']), ('DFE1E5', P['white2']),
    ('FFFFFF', P['white3']),
]
ACCENTS = ['blue0', 'blue1', 'blue2', 'cyan', 'green', 'yellow', 'orange', 'red', 'magenta']


def rgb(h): return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
def hexc(t): return ''.join('%02X' % round(max(0, min(1, x)) * 255) for x in t)
def lum(h):
    r, g, b = rgb(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def neutral(h):
    L = lum(h)
    pts = sorted((lum(s), d) for s, d in NEUTRAL_RAMP)
    for (l0, d0), (l1, d1) in zip(pts, pts[1:]):
        if l0 <= L <= l1:
            t = 0 if l1 == l0 else (L - l0) / (l1 - l0)
            return blend(d1, d0, t)
    return pts[-1][1]


def chromatic(h):
    hue, light, sat = colorsys.rgb_to_hls(*rgb(h))
    def hue_dist(name):
        ah = colorsys.rgb_to_hls(*rgb(P[name]))[0]
        d = abs(ah - hue)
        return min(d, 1 - d)
    acc = min(ACCENTS, key=hue_dist)
    if acc.startswith('blue'):  # pick the blue whose brightness is closest
        acc = min(('blue0', 'blue1', 'blue2'), key=lambda n: abs(lum(P[n]) - lum(h)))
    target = lum(h)
    if target >= lum(P[acc]) * 0.9:
        return P[acc]
    lo, hi = 0.0, 1.0  # blend accent over the editor bg until luminance matches
    for _ in range(30):
        mid = (lo + hi) / 2
        if lum(blend(P[acc], P['gray0'], mid)) < target: lo = mid
        else: hi = mid
    base = P['gray0'] if target >= lum(P['gray0']) else P['black0']
    return blend(P[acc], base, lo)


def remap_hex(value):
    h = value.lstrip('#').upper()
    alpha = h[6:] if len(h) == 8 else ''
    h = h[:6]
    if h in LITERAL: out = LITERAL[h]
    else:
        _, light, sat = colorsys.rgb_to_hls(*rgb(h))
        out = neutral(h) if sat < 0.18 or light < 0.06 or light > 0.95 else chromatic(h)
    return '#' + out + alpha


def walk(node, named_keys):
    if isinstance(node, dict):
        return {k: walk(v, named_keys) for k, v in node.items()}
    if isinstance(node, list):
        return [walk(v, named_keys) for v in node]
    if isinstance(node, str) and node.startswith('#') and len(node) in (7, 9):
        try:
            int(node[1:], 16)
        except ValueError:
            return node
        return remap_hex(node)
    return node


def main():
    with zipfile.ZipFile(JAR) as z:
        theme = json.load(io.TextIOWrapper(z.open(SRC), 'utf-8'))
    colors = theme.get('colors', {})
    for k, v in list(colors.items()):
        if k in NAMED:
            colors[k] = '#' + NAMED[k]
    unnamed = {k: v for k, v in colors.items() if k not in NAMED}
    theme['colors'] = {**walk(unnamed, set()), **{k: v for k, v in colors.items() if k in NAMED}}
    theme['ui'] = walk(theme['ui'], set())
    if 'icons' in theme:
        theme['icons'] = walk(theme['icons'], set())
    theme['name'] = 'Nordic'
    theme['author'] = 'sfra6651'
    theme['editorScheme'] = 'Nordic'
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(theme, f, indent=2)
        f.write('\n')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
