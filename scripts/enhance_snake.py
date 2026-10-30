#!/usr/bin/env python3
"""Style Platane/snk SVGs without changing any GitHub contribution values."""
from pathlib import Path
from datetime import datetime, timedelta, date, timezone
import math
import re
import sys

CELLS = re.compile(r'<rect class="c(?: c[0-9a-z]+)?" x="([0-9.]+)" y="([0-9.]+)"[^>]*/>')
SNAKE = re.compile(r'((?:<rect class="s s[0-9a-z]+"[^>]*/>)+)')
PROGRESS = re.compile(r'<rect class="u u[0-9a-z]+"[^>]*/>')




# Five-by-seven pixel font: each illuminated pixel sits EXACTLY on an
# existing contribution cell (same x/y, size, radius, zero backdrop).
READY_GLYPHS = {
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
}


def build_ready(cells: list[tuple[str, str]], duration_ms: int, dark: bool) -> tuple[str, str]:
    """Build a large READY opening with real calendar-sized square pixels."""
    word = "READY"
    width_in_columns = len(word) * 5 + len(word) - 1
    start_col = (53 - width_in_columns) // 2
    available = set(cells)
    color = "#39d353" if dark else "#2da44e"
    css = []
    letters = []

    for i, char in enumerate(word):
        # The lettering assembles very quickly, holds, and fades away
        # before the snake appears. All phases share snk's native loop.
        enter = 0.12 + i * 0.60
        visible = enter + 0.32
        css.append(
            f"@keyframes arcadeReady{i}{{"
            f"0%,{enter:.2f}%{{opacity:0}}"
            f"{visible:.2f}%,6.35%{{opacity:1}}"
            f"7.10%,100%{{opacity:0}}"
            "}"
            f".arcade-ready-letter-{i}{{opacity:0;"
            f"animation:arcadeReady{i} {duration_ms}ms steps(1,end) infinite}}"
        )
        pixels = []
        for row, bits in enumerate(READY_GLYPHS[char]):
            for col, bit in enumerate(bits):
                if bit != "1":
                    continue
                x = str(2 + 16 * (start_col + 6 * i + col))
                y = str(2 + 16 * row)
                if (x, y) not in available:
                    raise ValueError(f"READY pixel must align with calendar cell: {x}, {y}")
                pixels.append(
                    f'<rect x="{x}" y="{y}" width="12" height="12" rx="2" ry="2"/>'
                )
        letters.append(
            f'<g class="arcade-ready-letter-{i}">' + "".join(pixels) + "</g>"
        )
    markup = (
        f'<g id="arcade-ready" fill="{color}" pointer-events="none">'
        + "".join(letters)
        + "</g>"
    )
    return "".join(css), markup

def enhance(path: Path) -> None:
    svg = path.read_text(encoding="utf-8")
    cells = CELLS.findall(svg)
    if len(cells) < 300:
        raise ValueError(f"Expected a full contribution grid; got {len(cells)} cells in {path}")
    if 'id="snake-cells"' in svg or 'id="arcade-clear"' in svg:
        raise ValueError(f"Refusing to process an already-enhanced SVG: {path}")

    snake_duration = re.search(r'\.s\{[^}]*?\b(\d+)ms\b', svg)
    if not snake_duration:
        raise ValueError(f"Snake animation timing missing in {path}")
    duration_ms = int(snake_duration.group(1))

    # c* keyframes reset the cell color once the snake has eaten it.
    eaten_times = [float(v) for v in re.findall(r'([0-9.]+)%,100%\{fill:var\(--ce\)\}', svg)]
    last_eaten = max(eaten_times, default=80.0)
    show_at = min(max(last_eaten + 0.7, 81.0), 97.0)
    hide_at = max(98.9, min(99.5, show_at + 1.5))

    dark = "dark" in path.stem
    if dark:
        caption, text, subdued = "#142018", "#86efac", "#d1fae5"
    else:
        caption, text, subdued = "#e7f5ec", "#167347", "#23573c"

    square_paths = ''.join(
        f'<rect x="{x}" y="{y}" width="12" height="12" rx="2" ry="2"/>'
        for x, y in cells
    )
    defs = (
        '<defs>'
        '<clipPath id="snake-cells" clipPathUnits="userSpaceOnUse">'
        + square_paths +
        '</clipPath>'
        '</defs>'
    )
    if '</desc>' not in svg or '</style>' not in svg:
        raise ValueError(f"Unexpected SVG structure in {path}")
    svg = svg.replace('</desc>', '</desc>' + defs, 1)

    # Display the entire rolling year with visible month labels, as in GitHub.
    today = datetime.now(timezone.utc).date()
    first = today - timedelta(days=365)
    first -= timedelta(days=(first.weekday() + 1) % 7)  # Sunday column origin
    month = date(first.year, first.month, 1)
    labels = []
    while month <= today:
        week = (month - first).days // 7
        if week >= 0 and week < 53:
            x = 2 + week * 16
            text_color = "#8b949e" if dark else "#57606a"
            labels.append(
                f'<text x="{x}" y="-12" fill="{text_color}" '
                'font-family="Arial, sans-serif" font-size="10" '
                f'font-weight="500">{month.strftime("%b")}</text>'
            )
        month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)

    # The generated path can travel a row beyond the grid. Keep all
    # translated snake segments on valid column/row positions.
    def clamp_segment(match):
        x = max(0, min(832, float(match.group(1))))
        y = max(0, min(96, float(match.group(2))))
        return f'transform:translate({x:g}px,{y:g}px)'

    svg = re.sub(
        r'transform:translate\((-?[0-9.]+)px,(-?[0-9.]+)px\)',
        clamp_segment, svg
    )
    svg = svg.replace('</style>', '</style>' + ''.join(labels), 1)

    # Remove the horizontal progress line below the contribution grid.
    svg = PROGRESS.sub('', svg)
    svg, n = SNAKE.subn(
        lambda m: '<g class="arcade-snake" clip-path="url(#snake-cells)">' + m.group(1) + '</g>',
        svg, count=1
    )
    if n != 1:
        raise ValueError(f"Could not locate snake segments in {path}")

    animation = (
        f'@keyframes arcadeClear{{'
        f'0%,{show_at - 0.35:.2f}%{{opacity:0;transform:translateY(5px) scale(.96)}}'
        f'{show_at:.2f}%,{hide_at - 0.6:.2f}%{{opacity:1;transform:translateY(0) scale(1)}}'
        f'{hide_at:.2f}%,100%{{opacity:0;transform:translateY(-3px) scale(1.02)}}'
        '}'
        f'.arcade-clear{{opacity:0;transform-origin:424px 139px;'
        f'animation:arcadeClear {duration_ms}ms ease-in-out infinite}}'
        '@keyframes arcadeSpark{0%,100%{opacity:.3}50%{opacity:1}}'
        '.arcade-spark{animation:arcadeSpark 600ms steps(2,end) infinite}'
    )
    # Finale: blink the snake, explode into pixels from the center, then
    # pulse a fast green wave OUTWARD through the actual contribution squares.
    # All effects use the same duration as Platane/snk so the loop stays synced.
    blast_at = min(show_at + 0.36, 97.35)
    wave_count = 14
    step = min(0.22, (98.50 - blast_at - 0.40) / (wave_count - 1))
    flash_fill = "#86efac" if dark else "#2da44e"

    animation += (
        f'@keyframes arcadeSnakeBoom{{'
        '0%,7.15%{opacity:0}'
        f'7.19%,{blast_at - 0.24:.2f}%{{opacity:1}}'
        f'{blast_at - 0.16:.2f}%{{opacity:.12}}'
        f'{blast_at - 0.09:.2f}%{{opacity:1}}'
        f'{blast_at:.2f}%,99.90%{{opacity:0}}'
        '100%{opacity:1}}'
        f'.arcade-snake{{animation:arcadeSnakeBoom {duration_ms}ms steps(1,end) infinite}}'
    )

    # An unmistakably circular shockwave, expanding concentrically from
    # the middle of the grid. The existing clip path keeps the rings inside
    # the individual GitHub contribution squares, without a large backdrop.
    ring_shapes = []
    for ring in range(2):
        start = blast_at + ring * 0.23
        spread = min(start + 1.8, 99.1)
        peak = start + 0.26
        anim = f"arcadeShockwave{ring}"
        animation += (
            f'@keyframes {anim}{{'
            f'0%,{start - .03:.2f}%{{opacity:0;transform:scale(.05)}}'
            f'{start:.2f}%{{opacity:.95;transform:scale(.12)}}'
            f'{peak:.2f}%{{opacity:.92;transform:scale(.7)}}'
            f'{spread:.2f}%,100%{{opacity:0;transform:scale(5.3)}}'
            '}'
            f'.arcade-ring-{ring}{{opacity:0;transform-origin:424px 56px;'
            f'transform-box:view-box;animation:{anim} {duration_ms}ms ease-out infinite}}'
        )
        ring_shapes.append(
            f'<circle class="arcade-ring-{ring}" cx="424" cy="56" r="60" '
            f'fill="none" stroke="{flash_fill}" stroke-width="{4 - ring}" '
            'stroke-opacity=".95"/>'
        )

    wave_cells = [[] for _ in range(wave_count)]
    for x, y in cells:
        distance = math.hypot(float(x) + 6 - 424, float(y) + 6 - 56)
        band = min(wave_count - 1, int(distance // 32))
        wave_cells[band].append(
            f'<rect x="{x}" y="{y}" width="12" height="12" rx="2" ry="2"/>'
        )

    wave_layers = []
    for band, rects in enumerate(wave_cells):
        if not rects:
            continue
        hit = blast_at + band * step
        keyframe = f'arcadeWave{band}'
        animation += (
            f'@keyframes {keyframe}{{'
            f'0%,{hit - 0.03:.2f}%{{opacity:0}}'
            f'{hit:.2f}%{{opacity:.97}}'
            f'{hit + 0.13:.2f}%{{opacity:.24}}'
            f'{hit + 0.23:.2f}%{{opacity:.88}}'
            f'{hit + 0.39:.2f}%,100%{{opacity:0}}'
            '}'
            f'.arcade-wave-{band}{{opacity:0;'
            f'animation:{keyframe} {duration_ms}ms steps(2,end) infinite}}'
        )
        wave_layers.append(
            f'<g class="arcade-wave-{band}">' + ''.join(rects) + '</g>'
        )

    burst_pixels = []
    for i in range(12):
        angle = i * math.tau / 12
        dx = round(math.cos(angle) * (55 + (i % 3) * 24))
        dy = round(math.sin(angle) * (35 + (i % 3) * 10))
        keyframe = f'arcadeParticle{i}'
        animation += (
            f'@keyframes {keyframe}{{'
            f'0%,{blast_at - 0.08:.2f}%{{opacity:0;transform:translate(0px,0px) scale(.5)}}'
            f'{blast_at:.2f}%{{opacity:1;transform:translate(0px,0px) scale(1)}}'
            f'{blast_at + 0.83:.2f}%,100%{{opacity:0;'
            f'transform:translate({dx}px,{dy}px) scale(.15)}}'
            '}'
            f'.arcade-pixel-{i}{{opacity:0;transform-origin:424px 56px;'
            f'animation:{keyframe} {duration_ms}ms ease-out infinite}}'
        )
        burst_pixels.append(
            f'<rect class="arcade-pixel-{i}" x="421" y="53" '
            f'width="6" height="6" rx="1" ry="1" fill="{flash_fill}"/>'
        )

    explosion = (
        '<g id="arcade-explosion" clip-path="url(#snake-cells)" '
        f'fill="{flash_fill}" pointer-events="none">'
        + ''.join(ring_shapes)
        + ''.join(wave_layers)
        + ''.join(burst_pixels)
        + '</g>'
    )
    ready_css, ready_markup = build_ready(cells, duration_ms, dark)
    svg = svg.replace('</style>', animation + ready_css + '</style>', 1)
    ending = (
        '<g id="arcade-clear" class="arcade-clear">'
        f'<rect x="289" y="119" width="270" height="38" rx="9" ry="9" fill="{caption}" '
        f'stroke="{text}" stroke-opacity=".85" stroke-width="1.5"/>'
        f'<text x="424" y="136" text-anchor="middle" fill="{text}" '
        'font-family="monospace" font-size="16" font-weight="900" letter-spacing="2">'
        'LEVEL CLEAR!</text>'
        f'<text x="424" y="150" text-anchor="middle" fill="{subdued}" '
        'font-family="monospace" font-size="9" font-weight="700" letter-spacing="1.5">'
        'GG  //  100%  //  +XP</text>'
        f'<rect class="arcade-spark" x="279" y="130" width="5" height="5" fill="{text}"/>'
        f'<rect class="arcade-spark" x="567" y="126" width="5" height="5" fill="{text}"/>'
        f'<rect class="arcade-spark" x="576" y="144" width="3" height="3" fill="{text}"/>'
        '</g>'
    )
    svg = svg.replace('</svg>', ready_markup + explosion + ending + '</svg>', 1)
    path.write_text(svg, encoding="utf-8")
    print(f"Enhanced {path}: cells={len(cells)}, last_eaten={last_eaten:.2f}%, game_clear_at={show_at:.2f}%")


def main() -> None:
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
    files = sorted(folder.glob('*.svg'))
    if not files:
        raise RuntimeError(f"No SVG files found in {folder}")
    for file in files:
        enhance(file)


if __name__ == '__main__':
    main()
