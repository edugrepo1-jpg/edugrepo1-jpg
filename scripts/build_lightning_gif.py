#!/usr/bin/env python3
"""Render original lightning art as an animated transparent GIF for GitHub."""
from io import BytesIO
from pathlib import Path
import sys
import cairosvg
from PIL import Image

W,H=106,104
BOLT=(
'<path d="M575 16L547 73h24l-16 41 58-64h-30l18-34z" fill="#facc15" stroke="#f59e0b" stroke-width="2" stroke-linejoin="round"/>'
'<path d="M577 25l-17 43h20l-12 30 34-42h-24l12-31z" fill="#fff7c2" opacity=".92"/>')
SPARKS=[
'M532 16l-8 18h7l-4 15 16-22h-9l6-11z',
'M614 26l-11 20h7l-5 14 18-24h-10l7-10z',
'M528 87l-9 15h7l-3 11 15-20h-8l5-6z',
'M624 82l-8 14h7l-3 10 14-19h-9l5-5z',
'M652 50l-5 11h6l-3 10 12-16h-7l4-5z']
COLORS=[(0,0,0),(250,204,21),(245,158,11),(255,247,194),(255,226,85),(255,255,224)]
PHASES=[(2,3,4,8,12,14,17),(3,4,8,9,13,15,17),(2,5,6,9,12,16),
(4,5,10,11,14,18),(3,6,8,13,16,18)]
BRIGHT=[.45,.65,1,.5,1,1,.75,1,1,1,1,.7,1,1,.85,1,1,.9,1,.6]

def render_rgba(n):
    art=f'<g opacity="{BRIGHT[n]}">{BOLT}</g>'
    for i,p in enumerate(SPARKS):
        if n in PHASES[i]:
            opacity='1' if n in (2,3,4,5,6,8,9) else '.78'
            art+=f'<path d="{p}" fill="#ffe255" opacity="{opacity}"/>'
    markup=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="512 0 166 140" width="{W}" height="{H}">{art}</svg>'
    img=Image.open(BytesIO(cairosvg.svg2png(bytestring=markup.encode('utf-8'),output_width=W,output_height=H))).convert('RGBA')

    return img

def render(n):
    img=render_rgba(n)
    px=img.load()
    pixels=bytearray(W*H)
    for y in range(H):
        for x in range(W):
            r,g,b,a=px[x,y]
            if a<65:continue
            pixels[y*W+x]=min(range(1,len(COLORS)),key=lambda j:sum((v-z)**2 for v,z in zip((r,g,b),COLORS[j])))
    frame=Image.frombytes('P',(W,H),bytes(pixels))
    palette=bytes(c for rgb in COLORS for c in rgb)
    frame.putpalette(palette+bytes(768-len(palette)))
    return frame

def main():
    output=Path(sys.argv[1] if len(sys.argv)>1 else 'dist')
    output.mkdir(parents=True,exist_ok=True)
    frames=[render(i) for i in range(20)]
    file=output/'animated-lightning-transparent.gif'
    frames[0].save(file,save_all=True,append_images=frames[1:],duration=150,
                   loop=0,transparency=0,background=0,disposal=2,optimize=False)
    with Image.open(file) as check:
        assert check.n_frames==20
        assert check.info['transparency']==0
        for n in (0,4,10,19):
            check.seek(n)
            assert check.convert('RGBA').getpixel((0,0))[3]==0
    # APNG keeps true RGBA pixels instead of GIF's 1-bit palette
    # transparency, preventing dark/palette-colored boxes around the bolt.
    png=output/'animated-lightning-transparent.png'
    rgba_frames=[render_rgba(i) for i in range(20)]
    rgba_frames[0].save(
        png,format='PNG',save_all=True,append_images=rgba_frames[1:],
        duration=150,loop=0,disposal=2,blend=0,optimize=False
    )
    with Image.open(png) as check:
        assert check.n_frames==20 and check.is_animated
        for n in (0,4,10,19):
            check.seek(n)
            frame=check.convert('RGBA')
            assert frame.getpixel((0,0))[3]==0
            assert frame.getpixel((W-1,H-1))[3]==0
    print(f"Transparent animated PNG: {png} ({png.stat().st_size} bytes, 20 frames)")
    print(f"Animated transparent GIF: {file} ({file.stat().st_size} bytes, 20 frames)")

if __name__=='__main__':
    main()
