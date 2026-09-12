"""Render conceptual animations; no experimental data is used.
Requires Pillow and ffmpeg. Run from the repository root.
"""
from pathlib import Path
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / 'deploy/vercel/film'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
W, H, FPS, SECONDS = 960, 540, 24, 12
INK, MUTED, BLUE = '#171a20', '#5c5e62', '#3457b1'

def frame(kind, t):
    im = Image.new('RGB', (W,H), '#f4f4f4')
    d = ImageDraw.Draw(im)
    def text(x,y,s,size=24,color=INK):
        d.text((x,y),s,font=ImageFont.truetype(FONT,size),fill=color)
    text(48,32,'AEGISLAND / EXPLAINED',16,MUTED)
    if kind == 'uncertainty':
        text(48,80,'Confidence can miss the error.',36)
        text(48,143,'Reported uncertainty versus actual error',22,MUTED)
        d.line((80,300,880,300),fill='#a6a7aa',width=2)
        d.rounded_rectangle((300,254,580,346),radius=8,fill='#dce4f8')
        d.line((440,236,440,364),fill=BLUE,width=4)
        text(300,384,'Reported interval',22,BLUE)
        progress = min(1,max(0,(t-2)/7))
        x = 465 + 290*(progress*progress*(3-2*progress))
        d.ellipse((x-12,288,x+12,312),fill=INK)
        text(min(x-62,755),207,'Actual error',22)
        text(48,457,'Error grows. The reported interval stays the same.',25)
    else:
        text(48,80,'Freeze first. Then evaluate.',36)
        steps = [('01','Freeze','Candidate + thresholds'),('02','Evaluate','Separate test data'),('03','Preserve','Keep every verdict')]
        active=min(2,int(t/4))
        for i,(num,title,desc) in enumerate(steps):
            x=48+i*294
            d.rounded_rectangle((x,187,x+270,368),radius=8,fill='#ffffff',outline=BLUE if i==active else '#d0d1d2',width=3 if i==active else 1)
            text(x+20,209,num,20,BLUE)
            text(x+20,254,title,30)
            text(x+20,313,desc,17,MUTED)
            if i<2: text(x+275,261,'›',24,MUTED)
        captions=['Set the rules before inspecting test evidence.','Evaluate without refitting to the test data.','A later success does not erase an earlier failure.']
        text(48,422,captions[active],25)
        d.rounded_rectangle((48,477,912,482),radius=2,fill='#d0d1d2')
        d.rounded_rectangle((48,477,48+max(3,int(864*t/12)),482),radius=2,fill=BLUE)
    text(48,510,'Concept illustration · not experimental results · no audio',14,MUTED)
    return im

OUT.mkdir(parents=True,exist_ok=True)
for kind in ['uncertainty','evaluation']:
    frame(kind,6).save(OUT / f'{kind}-poster.jpg',quality=88)
    proc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','960x540','-r',str(FPS),'-i','-','-an','-c:v','libx264','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/f'{kind}-explainer.mp4')],stdin=subprocess.PIPE)
    for f in range(FPS*SECONDS): proc.stdin.write(frame(kind,f/FPS).tobytes())
    proc.stdin.close()
    assert proc.wait()==0
    print(kind,(OUT/f'{kind}-explainer.mp4').stat().st_size)
