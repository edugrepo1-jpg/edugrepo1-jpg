#!/usr/bin/env python3
"""Style Platane/snk SVGs without changing any GitHub contribution values."""
from pathlib import Path
from datetime import datetime, timedelta, date, timezone
import re
import sys

CELLS = re.compile(r'<rect class="c(?: c[0-9a-z]+)?" x="([0-9.]+)" y="([0-9.]+)"[^>]*/>')
SNAKE = re.compile(r'((?:<rect class="s s[0-9a-z]+"[^>]*/>)+)')
PROGRESS = re.compile(r'<rect class="u u[0-9a-z]+"[^>]*/>')


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
        lambda m: '<g clip-path="url(#snake-cells)">' + m.group(1) + '</g>',
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
    svg = svg.replace('</style>', animation + '</style>', 1)
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
    svg = svg.replace('</svg>', ending + '</svg>', 1)
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
