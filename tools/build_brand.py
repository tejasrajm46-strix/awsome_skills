#!/usr/bin/env python3
"""Build the approved original Relay S identity using OFL Geist outlines."""
from pathlib import Path
import argparse
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets"
MARK = "M80 32H224V80H80V104H176L224 152V176L176 224H32V176H176V152H80L32 104V80Z"


def outline(font, text, x, baseline, size, color, tracking=0):
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font['head'].unitsPerEm
    result = []
    for char in text:
        name = cmap[ord(char)]
        pen = SVGPathPen(glyphs)
        transform = TransformPen(pen, (scale, 0, 0, -scale, x, baseline))
        glyphs[name].draw(transform)
        if pen.getCommands():
            result.append('<path fill="%s" d="%s"/>' % (color, __import__('re').sub(r'(-?\d+\.\d+)', lambda m: ('%.2f' % float(m[0])).rstrip('0').rstrip('.'), pen.getCommands())))
        x += glyphs[name].width * scale + tracking
    return ''.join(result)


def svg(width, height, title, body):
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img"><title>%s</title>%s</svg>\n' % (width,height,width,height,title,body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--font', default='docs/assets/fonts/Geist.ttf')
    args = ap.parse_args()
    face = TTFont(ROOT / args.font)
    face = instantiateVariableFont(face, {'wght': 650}) if 'fvar' in face else face
    ASSETS.mkdir(parents=True, exist_ok=True)
    for suffix, color in [('', '#CDF56B'), ('-black','#111412'), ('-white','#F5F6EE')]:
        (ASSETS/('logo'+suffix+'.svg')).write_text(svg(256,256,'Awesome Skills — Relay S',
            '<path fill="%s" d="%s"/>'%(color,MARK)),encoding='utf8')
    body = '<g transform="translate(0 12) scale(.68)"><path fill="#CDF56B" d="%s"/></g>'%MARK
    body += outline(face,'awesome skills',202,128,79,'#F5F6EE',-2)
    (ASSETS/'brand-lockup.svg').write_text(svg(800,190,'Awesome Skills — original Relay S identity',body),encoding='utf8')
    stacked='<g transform="translate(142 0) scale(.65)"><path fill="#CDF56B" d="%s"/></g>'%MARK
    stacked+=outline(face,'awesome skills',26,234,54,'#F5F6EE',-1)
    (ASSETS/'brand-stacked.svg').write_text(svg(450,270,'Awesome Skills — stacked identity',stacked),encoding='utf8')
    light=body.replace('#F5F6EE','#111412').replace('#CDF56B','#176B60')
    (ASSETS/'brand-lockup-light.svg').write_text(svg(800,190,'Awesome Skills — light identity',light),encoding='utf8')
    hero='<rect width="1600" height="800" rx="36" fill="#111412"/>'
    hero+='<path d="M1040 0V800 M0 658H1600" stroke="#29322B" stroke-width="1"/>'
    hero+='<g transform="translate(76 55) scale(.34)"><path fill="#CDF56B" d="%s"/></g>'%MARK
    hero+=outline(face,'awesome skills',184,116,42,'#F5F6EE',-1)
    hero+=outline(face,'FROM INTENT',80,302,105,'#F5F6EE',-3)
    hero+=outline(face,'TO ARTIFACT.',80,423,105,'#CDF56B',-3)
    hero+=outline(face,'Five focused skills. One shared research pipeline.',84,498,28,'#B9C5B8')
    hero+=outline(face,'Editable by design. Checked before delivery.',84,543,28,'#B9C5B8')
    for i,(name,ext,col) in enumerate([('PowerPoint','.pptx','#FE9A7C'),('Word','.docx','#7FB9FF'),('PDF','.pdf','#E3B8FD'),('Excel','.xlsx','#8BDEB2'),('Poster','.png','#CDF56B')]):
        y=160+i*87
        hero+='<rect x="1090" y="%d" width="420" height="70" rx="14" fill="#1C251E" stroke="#344136"/>'%y
        hero+='<rect x="1109" y="%d" width="5" height="30" rx="2" fill="%s"/>'%(y+20,col)
        hero+=outline(face,name,1136,y+44,27,'#F5F6EE')+outline(face,ext,1400,y+43,19,col)
    hero+=outline(face,'OPEN SOURCE / AGENT READY',84,720,20,'#CDF56B',1)
    hero+=outline(face,'READ. BUILD. VERIFY.',1078,720,20,'#B9C5B8',1)
    (ASSETS/'hero-multiskill.svg').write_text(svg(1600,800,'Awesome Skills — from intent to artifact',hero),encoding='utf8')
    print('Built Relay S masters, outlined lockups and repository hero')


if __name__=='__main__':
    main()
