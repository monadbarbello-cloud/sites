"""EPIC patriotic Monad film. Writes video-only scenes + a full soundtrack (incl. 3s for brand end card).
python epic.py --out scenes.mp4 --wav music.wav"""
import argparse, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--wav", required=True)
a = ap.parse_args()
W, H, FPS = 1080, 1920, 30
NAVY = (1, 33, 105); RED = (200, 16, 46); WHITE = (255, 255, 255); GOLD = (232, 186, 74)
SCN = [("arrows", 4.6), ("dover", 4.6), ("london", 5.2)]
TOTAL = sum(d for _, d in SCN); CARD = 3.0
rng = np.random.default_rng(3)

def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try: return ImageFont.truetype(p, size)
        except OSError: pass
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def back(x):  # overshoot
    x = min(1, max(0, x)); c = 1.9; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def grad(cols, h=H):
    ys = np.linspace(0, 1, h); out = np.zeros((h, 3))
    for c in range(3): out[:, c] = np.interp(ys, [p for p, _ in cols], [col[c] for _, col in cols])
    return Image.fromarray(np.repeat(out[:, None, :], W, 1).astype(np.uint8)).convert("RGBA")

# ---------- flag ----------
def union_jack(w=900, h=450):
    s = 3; im = Image.new("RGB", (w*s, h*s), NAVY); d = ImageDraw.Draw(im); W2, H2 = w*s, h*s; t = H2 / 30
    d.line([(0, 0), (W2, H2)], fill=WHITE, width=int(6*t)); d.line([(0, H2), (W2, 0)], fill=WHITE, width=int(6*t))
    for (x0, y0, x1, y1, sg) in [(0, 0, W2, H2, 1), (0, H2, W2, 0, -1)]:
        dx, dy = x1-x0, y1-y0; L = math.hypot(dx, dy); nx, ny = -dy/L, dx/L; mx, my = (x0+x1)/2, (y0+y1)/2
        for seg, off in (([(x0, y0), (mx, my)], 1), ([(mx, my), (x1, y1)], -1)):
            o = off*sg*t; d.line([(p[0]+nx*o, p[1]+ny*o) for p in seg], fill=RED, width=int(2*t))
    d.rectangle([W2/2-5*t, 0, W2/2+5*t, H2], fill=WHITE); d.rectangle([0, H2/2-5*t, W2, H2/2+5*t], fill=WHITE)
    d.rectangle([W2/2-3*t, 0, W2/2+3*t, H2], fill=RED); d.rectangle([0, H2/2-3*t, W2, H2/2+3*t], fill=RED)
    return np.asarray(im.resize((w, h), Image.LANCZOS)).astype(np.float32)
FLAG = union_jack()
def wave_flag(t, amp=34):
    fh, fw, _ = FLAG.shape; xs = np.arange(fw); ph = xs/fw*2.8*math.pi - t*6.0
    dy = amp*np.sin(ph)*(xs/fw)**0.8; shade = 1 + 0.38*np.cos(ph)*(xs/fw)**0.6
    out = np.zeros((fh+2*amp+4, fw, 4), np.float32)
    for x in range(fw):
        o = int(amp+2+dy[x]); out[o:o+fh, x, :3] = np.clip(FLAG[:, x, :]*shade[x], 0, 255); out[o:o+fh, x, 3] = 255
    return Image.fromarray(out.astype(np.uint8), "RGBA")

# ---------- shared FX ----------
EMB = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(20, 70), rng.uniform(2, 6), rng.uniform(0, 6)) for _ in range(70)]
def embers(im, t, col=GOLD):
    l = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    for x, y, sp, r, ph in EMB:
        yy = (y - t*sp*4) % H; xx = x + 30*math.sin(t*1.3 + ph); al = int(150 + 100*math.sin(t*5 + ph))
        d.ellipse([xx-r, yy-r, xx+r, yy+r], fill=col + (max(0, al),))
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(2))); im.alpha_composite(l)

def glow_text(im, txt, cx, cy, size, k, col=WHITE, gold=False):
    """slam-in text: scales from 2.4x with overshoot, RGB split as it lands, glow"""
    if k <= 0: return
    s = 1 + 1.4*(1 - back(k/1.0)) if k < 1 else 1; f = font(int(size*s))
    l = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(l); tw = d.textlength(txt, font=f)
    x, y = cx - tw/2, cy - size*s/2; al = int(255*min(1, k*3))
    split = int(18*(1 - min(1, k)))
    if split:
        d.text((x - split, y), txt, font=f, fill=(255, 30, 60, al//2)); d.text((x + split, y), txt, font=f, fill=(40, 90, 255, al//2))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(glow).text((x, y), txt, font=f, fill=(GOLD if gold else (255, 255, 255)) + (int(al*0.8),))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(22)))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).text((x+5, y+7), txt, font=f, fill=(0, 0, 0, int(al*0.7)))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5))); im.alpha_composite(l)
    top = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(top).text((x, y), txt, font=f, fill=(GOLD if gold else col) + (al,))
    im.alpha_composite(top)

def rays(im, cx, cy, t, col=(255, 225, 150), n=18, al=70):
    l = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(l); R = 2600
    for i in range(n):
        a0 = i/n*2*math.pi + t*0.15; w_ = 0.06 + 0.03*math.sin(i*3.1)
        d.polygon([(cx, cy), (cx + R*math.cos(a0), cy + R*math.sin(a0)), (cx + R*math.cos(a0+w_), cy + R*math.sin(a0+w_))], fill=col + (al,))
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(25)))

def flare(im, sx, sy):
    l = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(l); cx, cy = W/2, H/2
    for f, r, c in ((0.4, 60, (255, 200, 120, 60)), (0.8, 30, (120, 200, 255, 70)), (1.3, 110, (255, 120, 80, 35)), (1.7, 45, (200, 255, 200, 50))):
        x, y = sx + (cx - sx)*f*2, sy + (cy - sy)*f*2; d.ellipse([x-r, y-r, x+r, y+r], fill=c)
    d.line([(0, sy), (W, sy)], fill=(255, 220, 180, 90), width=6)
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(6)))

# ---------- Scene 1: Red Arrows flypast ----------
CLOUDS = [(rng.uniform(-200, W), rng.uniform(1550, 2000), rng.uniform(160, 380)) for _ in range(26)]
def jet(d, x, y, sc=1.0, ang=-0.5):
    pts = [(0, -38), (7, -10), (40, 10), (40, 16), (7, 10), (5, 28), (14, 36), (-14, 36), (-5, 28), (-7, 10), (-40, 16), (-40, 10), (-7, -10)]
    ca, sa = math.cos(ang), math.sin(ang)
    d.polygon([(x + sc*(px*ca - py*sa), y + sc*(px*sa + py*ca)) for px, py in pts], fill=(200, 20, 35));
    d.polygon([(x + sc*(px*ca - py*sa), y + sc*(px*sa + py*ca)) for px, py in [(0, -30), (3, -12), (-3, -12)]], fill=(240, 240, 255))
def arrows(t, T):
    im = grad([(0, (8, 20, 70)), (0.55, (40, 90, 170)), (0.8, (250, 160, 90)), (1, (255, 210, 150))])
    rays(im, W/2, 1300, t, al=45)
    d = ImageDraw.Draw(im)
    # formation flies bottom-left -> top-right, diagonal
    p = t / T; lx, ly = -300 + 1700*p, 1750 - 1500*p
    nrm = math.hypot(1700, -1500); ux, uy = 1700/nrm, -1500/nrm; px_, py_ = -uy, ux
    ang = math.atan2(ux, -uy)
    offs = [(0, 0)] + [(s*k*120, k*130) for k in range(1, 5) for s in (-1, 1)]  # (side, back)
    order = sorted(range(9), key=lambda i: offs[i][0]); cols = {}
    for rank, i in enumerate(order): cols[i] = (RED if rank < 3 else WHITE if rank < 6 else (30, 70, 200))
    trail = Image.new("RGBA", (W, H), (0, 0, 0, 0)); td = ImageDraw.Draw(trail); pos = []
    for i, (ox, oy) in enumerate(offs):
        jx = lx - ux*oy + px_*ox; jy = ly - uy*oy + py_*ox; pos.append((jx, jy))
        tail = [(jx - ux*k*14 + px_*5*math.sin(k*0.3 + i), jy - uy*k*14 + py_*5*math.sin(k*0.3 + i)) for k in range(2, 160)]
        td.line(tail, fill=cols[i] + (210,), width=46, joint="curve")
    im.alpha_composite(trail.filter(ImageFilter.GaussianBlur(14))); im.alpha_composite(trail.filter(ImageFilter.GaussianBlur(4)))
    d = ImageDraw.Draw(im)
    for jx, jy in pos: jet(d, jx, jy, 2.1, ang)
    # clouds over bottom
    cl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); cd = ImageDraw.Draw(cl)
    for x, y, r in CLOUDS: xx = (x - t*40) % (W + 400) - 200; cd.ellipse([xx-r, y-r*0.5, xx+r, y+r*0.5], fill=(255, 235, 215, 235))
    im.alpha_composite(cl.filter(ImageFilter.GaussianBlur(20)))
    glow_text(im, "BRITANNIA", W/2, 330, 122, (t - 1.2)/0.35, gold=True)
    glow_text(im, "RULES.", W/2, 500, 120, (t - 1.9)/0.35)
    return im, [1.2, 1.9]

# ---------- Scene 2: Dover + giant flag ----------
def dover(t, T):
    im = grad([(0, (30, 50, 110)), (0.35, (255, 150, 90)), (0.55, (255, 210, 150)), (0.56, (60, 110, 160)), (1, (10, 30, 60))])
    sy = 1080 - 140*ease(t/T); rays(im, 760, sy, t, al=60)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for r, al in ((380, 50), (240, 90), (130, 255)): gd.ellipse([760-r, sy-r, 760+r, sy+r], fill=(255, 238, 180, al))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(24))); d = ImageDraw.Draw(im)
    for i in range(110):
        yy = 1085 + (i*37 % 830); xx = 760 + math.sin(i*1.7 + t*2.4)*(30 + (yy-1080)*0.7)
        d.line([(xx-40, yy), (xx+40, yy)], fill=(255, 225, 170, 140), width=3)
    d.polygon([(0, 930), (150, 890), (300, 930), (420, 900), (520, 960), (580, 1150), (0, 1240)], fill=(246, 242, 228))
    d.polygon([(0, 885), (160, 845), (310, 890), (430, 860), (520, 930), (420, 900), (300, 930), (150, 890), (0, 930)], fill=(70, 125, 60))
    for k in range(10): d.line([(50 + k*52, 930), (80 + k*48, 1180)], fill=(214, 208, 190), width=4)
    # camera push on the flag
    z = 1 + 0.25*ease(t/T)
    fl = wave_flag(t).resize((int(980*z), int(980*z*0.55)), Image.LANCZOS)
    d.rectangle([60, 1120, 82, 1920], fill=(60, 50, 40)); d.ellipse([54, 1104, 88, 1138], fill=GOLD)
    im.alpha_composite(fl, (82, int(1130 - 40*z)))
    flare(im, 760, sy)
    embers(im, t)
    glow_text(im, "THIS IS", W/2, 300, 120, (t - 0.5)/0.3)
    glow_text(im, "BRITAIN.", W/2, 460, 150, (t - 1.1)/0.35, gold=True)
    return im, [0.5, 1.1]

# ---------- Scene 3: London fireworks ----------
BURSTS = []
for i in range(14):
    ts = 0.15 + i*0.36; cx, cy = rng.uniform(150, 930), rng.uniform(250, 900)
    col = [RED, WHITE, (40, 90, 255), GOLD][i % 4]; n = 90
    ang = rng.uniform(0, 2*math.pi, n); spd = rng.uniform(250, 520, n)
    BURSTS.append((ts, cx, cy, col, ang, spd))
SKY_L = None
def london(t, T):
    im = grad([(0, (5, 5, 25)), (0.5, (25, 20, 60)), (0.66, (70, 40, 90)), (0.67, (15, 15, 30)), (1, (5, 5, 15))])
    fw = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(fw); flash = 0
    for ts, cx, cy, col, ang, spd in BURSTS:
        dt = t - ts
        if dt < -0.5 or dt > 2.2: continue
        if dt < 0:  # rising rocket
            ry = cy + (-dt)*900; fd.ellipse([cx-5, ry-5, cx+5, ry+5], fill=(255, 220, 160, 255)); continue
        flash = max(flash, max(0, 1 - dt*4))
        fade = max(0, 1 - dt/2.0)
        for k in range(len(ang)):
            r = spd[k]*(1 - math.exp(-dt*2.4))/2.4*1.6
            x = cx + math.cos(ang[k])*r; y = cy + math.sin(ang[k])*r + 60*dt*dt
            x2 = cx + math.cos(ang[k])*r*0.82; y2 = cy + math.sin(ang[k])*r*0.82 + 60*dt*dt
            fd.line([(x2, y2), (x, y)], fill=col + (int(255*fade),), width=5)
    im.alpha_composite(fw.filter(ImageFilter.GaussianBlur(16))); im.alpha_composite(fw.filter(ImageFilter.GaussianBlur(3))); im.alpha_composite(fw)
    if flash: im.alpha_composite(Image.new("RGBA", (W, H), (255, 220, 200, int(40*flash))))
    d = ImageDraw.Draw(im); sil = (12, 10, 25)
    # Houses of Parliament + Elizabeth Tower silhouette
    d.rectangle([0, 1180, W, 1290], fill=sil)
    for x in range(0, W, 70): d.polygon([(x, 1180), (x + 35, 1120), (x + 70, 1180)], fill=sil); d.rectangle([x + 30, 1090, x + 40, 1180], fill=sil)
    bx = 640; d.rectangle([bx, 620, bx + 170, 1290], fill=sil); d.polygon([(bx - 12, 620), (bx + 85, 380), (bx + 182, 620)], fill=sil)
    d.line([(bx + 85, 380), (bx + 85, 310)], fill=sil, width=9)
    cg = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(cg).ellipse([bx + 10, 660, bx + 160, 810], fill=(255, 230, 150, 200))
    im.alpha_composite(cg.filter(ImageFilter.GaussianBlur(20))); d = ImageDraw.Draw(im)
    d.ellipse([bx + 22, 672, bx + 148, 798], fill=(255, 238, 180))
    for hh, ln, wd in ((-0.3, 38, 7), (0.0, 54, 5)): d.line([(bx + 85, 735), (bx + 85 + ln*math.sin(hh), 735 - ln*math.cos(hh))], fill=sil, width=wd)
    for wy in range(1200, 1280, 30):
        for wx in range(20, W, 46):
            if (wx*3 + wy) % 7 < 4: d.rectangle([wx, wy, wx + 14, wy + 16], fill=(255, 200, 110))
    # Thames reflection
    ref = im.crop((0, 300, W, 1290)).transpose(Image.FLIP_TOP_BOTTOM).resize((W, 630)).filter(ImageFilter.GaussianBlur(7))
    ref = ImageChops.multiply(ref, Image.new("RGBA", ref.size, (150, 150, 200, 255))); im.alpha_composite(ref, (0, 1290))
    d = ImageDraw.Draw(im)
    for i in range(90):
        yy = 1300 + (i*29 % 620); xx = (i*97 + t*30) % W; d.line([(xx - 30, yy), (xx + 30, yy)], fill=(0, 0, 10, 120), width=3)
    embers(im, t, col=(255, 200, 120))
    glow_text(im, "LAND OF", W/2, 1470, 110, (t - 0.6)/0.3)
    glow_text(im, "HOPE & GLORY", W/2, 1620, 96, (t - 1.2)/0.35, gold=True)
    return im, [0.6, 1.2]

FUNCS = {"arrows": arrows, "dover": dover, "london": london}
NOISE = [Image.fromarray(rng.integers(0, 40, (H//2, W//2), dtype=np.uint8)).resize((W, H)).convert("L") for _ in range(6)]
VIG = Image.new("L", (W, H), 0); vd = ImageDraw.Draw(VIG)
for i in range(40): vd.ellipse([-300 + i*12, -400 + i*16, W + 300 - i*12, H + 400 - i*16], fill=int(255*i/40))
VIG = VIG.filter(ImageFilter.GaussianBlur(60))
BLACK = Image.new("RGB", (W, H), (0, 0, 0))

def post(im, t, T, slams, fi, first):
    # camera: slow push + shake on slams
    z = 1.04 + 0.06*(t/T); sx = sy = 0
    for s in slams:
        dt = t - s - 0.33
        if 0 <= dt < 0.35: amp = 22*(1 - dt/0.35); sx += amp*math.sin(dt*90); sy += amp*math.cos(dt*77); z += 0.04*(1 - dt/0.35)
    w2, h2 = W/z, H/z; x0 = (W - w2)/2 + sx; y0 = (H - h2)/2 + sy
    im = im.crop((int(x0), int(y0), int(x0 + w2), int(y0 + h2))).resize((W, H), Image.BILINEAR).convert("RGB")
    im = Image.composite(im, BLACK, VIG)                      # vignette
    im = ImageChops.add(im, Image.merge("RGB", [NOISE[fi % 6]]*3), scale=1.0, offset=-12)  # film grain
    # white flash at scene start, fade out at scene end
    if not first and t < 0.25: im = Image.blend(im, Image.new("RGB", (W, H), WHITE), 1 - t/0.25)
    if T - t < 0.12: im = Image.blend(im, Image.new("RGB", (W, H), WHITE), (0.12 - (T - t))/0.12*0.9)
    return im

p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
fi = 0; slam_times = []; t0 = 0
for si, (name, T) in enumerate(SCN):
    for f in range(int(T*FPS)):
        t = f/FPS; im, slams = FUNCS[name](t, T)
        if f == 0: slam_times += [t0 + s + 0.33 for s in slams]
        p.stdin.write(np.asarray(post(im, t, T, slams, fi, si == 0)).tobytes()); fi += 1
    t0 += T
p.stdin.close(); p.wait()

# ---------- epic soundtrack ----------
SR = 44100; dur = TOTAL + CARD; n = int(SR*dur); L = np.zeros(n)
def add(sig, st, vol=1.0):
    s = int(st*SR); e = min(n, s + len(sig));
    if s < n: L[s:e] += vol*sig[:e-s]
def tt(sec): return np.arange(int(sec*SR))/SR
def brass(f, sec):
    x = tt(sec); env = np.minimum(1, x/0.08)*np.minimum(1, (sec - x)/0.15)*(0.85 + 0.15*np.sin(x*5))
    return env*sum(np.sin(2*math.pi*f*h*x + 0.3*h)/h**0.9 for h in range(1, 9))*0.12
def boom(sec=1.6):
    x = tt(sec); f = 90*np.exp(-x*3) + 32
    return (np.sin(2*math.pi*np.cumsum(f)/SR)*np.exp(-x*2.2) + rng.normal(0, 1, len(x))*np.exp(-x*18)*0.5)
def drum(sec=0.5):
    x = tt(sec); return np.sin(2*math.pi*(70*np.exp(-x*8) + 45)*x)*np.exp(-x*9) + rng.normal(0, 1, len(x))*np.exp(-x*40)*0.4
def whoosh(sec=0.9):
    x = tt(sec); nz = rng.normal(0, 1, len(x)); nz = np.convolve(nz, np.ones(25)/25, "same"); return nz*(x/sec)**2*1.6
def crackle(sec=1.2):
    x = tt(sec); return (rng.random(len(x)) > 0.995)*rng.normal(0, 1, len(x))*np.exp(-x*2)
# drone
x = tt(dur); L += 0.08*(np.sin(2*math.pi*65.4*x) + 0.6*np.sin(2*math.pi*98*x))*np.minimum(1, x/2)
# chord progression in C, swelling brass: C - F - G - Am - F - G - C
prog = [(261.6, 329.6, 392.0), (349.2, 440.0, 523.3), (392.0, 493.9, 587.3), (440.0, 523.3, 659.3), (349.2, 440.0, 523.3), (392.0, 493.9, 587.3), (523.3, 659.3, 784.0)]
step = TOTAL/len(prog)
for i, ch in enumerate(prog):
    for k, f in enumerate(ch): add(brass(f/2 if k == 0 else f, step*1.02), i*step, 0.9 if i < 6 else 1.2)
    add(brass(ch[0]/4, step*1.02), i*step, 0.8)
# heroic melody on top
mel = [(784, .5), (784, .25), (880, .25), (784, .5), (659, .5), (698, .5), (784, .5), (880, 1), (988, .5), (1047, 1.5)]
for rep in range(2):
    pos = 1.0 + rep*7.0
    for f, b in mel: add(brass(f, b*0.55), pos, 0.7); pos += b*0.55
# taiko pulse building
bt = 0.42
for i, b in enumerate(np.arange(0, TOTAL, bt)): add(drum(), b, 0.6 + 0.5*(b/TOTAL) + (0.3 if i % 4 == 0 else 0))
for s in slam_times: add(boom(), s - 0.02, 1.1)
c = 0
for _, T in SCN[:-1]: c += T; add(whoosh(), c - 0.85, 0.9); add(boom(1.2), c, 0.8)
for ts, *_ in BURSTS: add(boom(0.8), SCN[0][1] + SCN[1][1] + ts, 0.35); add(crackle(), SCN[0][1] + SCN[1][1] + ts + 0.05, 0.6)
# finale on brand card
add(whoosh(), TOTAL - 0.85, 1.0); add(boom(2.5), TOTAL, 1.4)
for f in (523.3, 659.3, 784.0, 1046.5): add(brass(f, CARD), TOTAL, 1.0)
L = np.tanh(L*0.9)*0.85; fade = int(1.2*SR); L[-fade:] *= np.linspace(1, 0, fade)
with wave.open(a.wav, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((L*32767).astype(np.int16).tobytes())
print("done", TOTAL, slam_times)
