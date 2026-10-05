#!/usr/bin/env python3
"""Draw original editorial slide references; no third-party template artwork."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "ppt_skill/assets"
FONTS = Path("C:/Windows/Fonts")


def font(size, bold=False):
    candidates = [FONTS / ("arialbd.ttf" if bold else "arial.ttf"),
                  Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
                       "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError("Install Arial or DejaVu Sans before regenerating references")


def main():
    directory = ASSETS / "render"
    directory.mkdir(parents=True, exist_ok=True)
    recipes = [
        ("editorial", "Editorial clarity", "One claim.\nA clear next move.", "#F5F3EB", "#151A17", "#176B60"),
        ("signal", "Signal / dark", "Less noise.\nMore signal.", "#101713", "#F3F5EA", "#CDF56B"),
        ("evidence", "Evidence / comparison", "The evidence\nchanges the choice.", "#F0F4F3", "#183B3A", "#267D75"),
        ("diagram", "System / flow", "Make the system\nvisible.", "#101622", "#F5F7FA", "#79BCFF"),
        ("data", "Data / hierarchy", "Show the change.\nKeep the context.", "#F9F5ED", "#211B17", "#C67643"),
        ("gallery", "Portfolio / restraint", "Let the work\nlead the story.", "#ECEBE4", "#252B26", "#425F4A"),
    ]
    credits = []
    for index, (slug, name, headline, bg, ink, accent) in enumerate(recipes):
        image = Image.new("RGB", (1200, 675), bg)
        d = ImageDraw.Draw(image)
        d.text((65, 42), "AWESOME SKILLS / DESIGN REFERENCE", font=font(15, True), fill=accent)
        d.text((65, 95), headline, font=font(63, True), fill=ink, spacing=8)
        d.text((65, 275), "Original design studies for editable presentation layouts.", font=font(21), fill=ink)
        if slug == "editorial":
            d.rectangle((65, 346, 505, 568), fill=accent)
            d.text((90, 368), "01", font=font(88, True), fill=bg)
            d.text((90, 485), "A measured opening", font=font(25), fill=bg)
            for y, text in [(356,"A deliberate hierarchy"),(422,"A shared alignment grid"),(488,"Enough space to breathe")]:
                d.line((580,y+13,620,y+13),fill=accent,width=5)
                d.text((648,y),text,font=font(26),fill=ink)
        elif slug == "signal":
            d.text((65,340),"38%",font=font(150,True),fill=accent)
            d.text((70,520),"Illustrative metric — not a real performance claim",font=font(18),fill=ink)
            for x,y in [(880,345),(940,440),(820,530)]:
                d.ellipse((x-20,y-20,x+20,y+20),fill=accent)
                d.line((830,405,x,y),fill=ink,width=3)
        elif slug == "evidence":
            for x,title,copy in [(65,"Before","Fragmented inputs"),(610,"After","One checked source register")]:
                d.rounded_rectangle((x,342,x+520,566),radius=12,outline=accent,width=2)
                d.text((x+28,370),title,font=font(30,True),fill=accent)
                d.text((x+28,446),copy,font=font(23),fill=ink)
        elif slug == "diagram":
            for i,word in enumerate(["Inspect","Build","Verify"]):
                x=65+i*370
                d.rounded_rectangle((x,373,x+285,506),radius=15,outline=accent,width=3)
                d.text((x+33,415),word,font=font(31,True),fill=ink)
                if i<2:d.line((x+290,439,x+360,439),fill=accent,width=4)
        elif slug == "data":
            for i,(label,width) in enumerate([("Baseline",415),("Iteration",570),("Measured",760)]):
                y=350+i*73
                d.text((65,y+8),label,font=font(23),fill=ink)
                d.rectangle((255,y,255+width,y+40),fill=accent)
            d.text((65,590),"Zero baseline · explicit units · illustrative data",font=font(17),fill=ink)
        else:
            for i in range(3):
                x=65+i*370
                d.rectangle((x,344,x+320,535),fill=accent if i==0 else "#D1D6CD")
                d.text((x+22,365),"%02d"%(i+1),font=font(45,True),fill=bg if i==0 else ink)
                d.text((x,550),["The subject","The detail","The context"][i],font=font(23),fill=ink)
        d.line((65,632,1135,632),fill=accent,width=1)
        d.text((65,643),name.upper(),font=font(12,True),fill=ink)
        d.text((1070,643),"%02d / 06"%(index+1),font=font(12),fill=ink)
        path=directory/(slug+".jpg")
        image.save(path,quality=90)
        credits.append({"file":"render/"+path.name,"title":name,"source":"repository:tools/build_reference_assets.py",
                        "creator":"Awesome Skills contributors","license":"MIT","native_file_included":False,
                        "reuse":"Original layout reference; recreate as native editable objects, not a flattened slide."})
    sheet = Image.new("RGB",(1200,810),"#E7EAE3")
    for index,recipe in enumerate(recipes):
        with Image.open(directory/(recipe[0]+".jpg")) as im:
            im.thumbnail((570,321)); x=20+(index%2)*600;y=15+(index//2)*263
            im=im.resize((448,252));sheet.paste(im,(x,y))
    sheet.save(ASSETS/"template-sheet.jpg",quality=90)
    sheet.save(ASSETS/"preview-sheet.jpg",quality=90)
    (ASSETS/"credits.json").write_text(json.dumps(credits,indent=2)+"\n",encoding="utf-8")
    print("Created six original slide-design references and two contact sheets")


if __name__ == "__main__":
    main()
