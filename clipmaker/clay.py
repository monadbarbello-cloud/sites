"""Mr & Mrs Bulldog — clay-3D style fun Monad clip. python bulldogs.py --out v.mp4 --wav a.wav"""
import argparse, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--wav", required=True)
ap.add_argument("--frames", default=""); ap.add_argument("--lines", default="{}"); a = ap.parse_args()
import json
LN = {"title1": "A PROPER BRITISH", "title2": "NIGHT OUT", "honk": "PARP PARP!", "mr1": "Evenin', Mrs B!", "mrs": "Ooh, Mr Bulldog!", "mr2": "Fancy a cuppa, love?", "bye": "Ta-ra!"}
LN.update(json.loads(a.lines))
W, H, FPS, T, CARD = 1080, 1920, 30, 15.0, 3.0
NAVY = (1, 33, 105); RED = (200, 16, 46); WHITE = (255, 255, 255); GOLD = (232, 186, 74)
rng = np.random.default_rng(11)
def font(size, serif=False):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if serif else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(p, size)
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def smooth(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def back(x): x = min(1, max(0, x)); c = 2.2; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ---------- clay-3D shaded ellipsoid sprites ----------
LIGHT = np.array([-0.45, -0.6, 0.66]); LIGHT /= np.linalg.norm(LIGHT)
_cache = {}
_tr = np.random.default_rng(5); _n = _tr.normal(0, 1, (256, 256)).astype(np.float32)
TEXI = Image.fromarray(((_n - _n.min()) / (_n.max() - _n.min()) * 255).astype(np.uint8)).resize((1024, 1024), Image.BICUBIC).filter(ImageFilter.GaussianBlur(3))
TEX = (np.asarray(TEXI).astype(np.float32) / 255 - 0.5) * 2
yy_, xx_ = np.mgrid[0:1024, 0:1024].astype(np.float32)
for _ in range(40):  # thumbprints
    cx_, cy_, r_ = _tr.uniform(0, 1024), _tr.uniform(0, 1024), _tr.uniform(25, 60); dd = np.hypot(xx_ - cx_, yy_ - cy_)
    TEX += np.sin(dd * 0.9) * np.clip(1 - dd / r_, 0, 1) * 0.5
FRAME = [0]
def sprite(rx, ry, col, gloss=0.35):
    rx, ry = max(2, int(rx)), max(2, int(ry)); key = (rx, ry, col, gloss)
    if key in _cache: return _cache[key]
    ys, xs = np.mgrid[-ry:ry + 1, -rx:rx + 1].astype(np.float32)
    nx, ny = xs / rx, ys / ry; r2 = nx ** 2 + ny ** 2; nz = np.sqrt(np.clip(1 - r2, 0, 1))
    dif = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
    rz = 2 * dif * nz - LIGHT[2]; spec = np.clip(rz, 0, 1) ** 24 * gloss
    rim = (1 - nz) ** 3 * 0.35
    c = np.array(col, np.float32)[None, None]
    oy_, ox_ = (hash((rx, ry, col)) % 700), (hash((ry, rx, col)) % 700)
    tex = TEX[oy_:oy_ + 2 * ry + 1, ox_:ox_ + 2 * rx + 1]
    if tex.shape != nx.shape: tex = np.resize(tex, nx.shape)
    shade = (0.38 + 0.72 * dif + 0.2 * tex)[..., None] * np.array([1.06, 1.0, 0.9])[None, None]
    rgb = c * shade * (1 - rim[..., None]) + 255 * spec[..., None] * 0.25
    alpha = np.clip((1 - np.sqrt(r2)) * max(rx, ry) * 1.2, 0, 1) * 255
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), "RGBA")
    if len(_cache) > 4000: _cache.clear()
    _cache[key] = im; return im
def ell(im, cx, cy, rx, ry, col, ang=0, gloss=0.35):
    j = hash((int(cx) // 7, int(cy) // 7, FRAME[0])) % 5 - 2; cx += j * 0.8; cy += (hash((FRAME[0], int(rx))) % 3 - 1) * 0.8
    sp = sprite(rx, ry, col, gloss)
    if ang: sp = sp.rotate(ang, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))
SHADOW = Image.new("RGBA", (400, 120), (0, 0, 0, 0)); ImageDraw.Draw(SHADOW).ellipse([20, 20, 380, 100], fill=(0, 0, 0, 150))
SHADOW = SHADOW.filter(ImageFilter.GaussianBlur(14))
def shadow(im, cx, cy, w):
    s = SHADOW.resize((int(w), int(w * 0.3))); im.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))

def darker(c, k=0.7): return tuple(int(v * k) for v in c)
def lighter(c, k=0.35): return tuple(int(v + (255 - v) * k) for v in c)

# ---------- bulldog head ----------
def head(im, cx, cy, s, fur, female=False, look=(0, 0), blush=0.0, mouth=0.0, hat=None, tilt=0.0):
    # build on a local layer so we can tilt the whole head
    S = int(330 * s); L = Image.new("RGBA", (S * 2, S * 2), (0, 0, 0, 0)); ox = oy = S
    def E(x, y, rx, ry, col, ang=0, gloss=0.35): ell(L, ox + x * s, oy + y * s, rx * s, ry * s, col, ang, gloss)
    d = ImageDraw.Draw(L)
    E(-100, -70, 40, 30, darker(fur, 0.6), 35); E(100, -70, 40, 30, darker(fur, 0.6), -35)            # ears
    E(0, 0, 125, 110, fur)                                                                              # skull
    for k in range(3):                                                                                  # brow wrinkles
        d.arc([ox - 50 * s, oy - (78 - k * 12) * s, ox + 50 * s, oy - (40 - k * 12) * s], 200, 340, fill=darker(fur, 0.62), width=max(2, int(4 * s)))
    E(0, 88, 66, 34 + 18 * mouth, darker(fur, 0.8))                                                    # underbite jaw
    if mouth > 0.05:
        E(0, 80 + 10 * mouth, 40, 10 + 26 * mouth, (70, 20, 30), gloss=0.1); E(0, 92 + 16 * mouth, 22, 8 + 10 * mouth, (235, 110, 130))
    for sx in (-1, 1):                                                                                  # teeth
        tx = ox + sx * 30 * s; ty = oy + (70 - 6 * mouth) * s
        d.polygon([(tx - 8 * s, ty + 12 * s), (tx + 8 * s, ty + 12 * s), (tx, ty - 6 * s)], fill=(250, 248, 235))
    E(-46, 48, 62, 50, lighter(fur, 0.25)); E(46, 48, 62, 50, lighter(fur, 0.25))                      # jowls
    d = ImageDraw.Draw(L)
    for sx in (-1, 1):
        for k in range(3): d.ellipse([ox + sx * (40 + k * 12) * s - 3 * s, oy + (44 + k * 9) * s - 3 * s, ox + sx * (40 + k * 12) * s + 3 * s, oy + (44 + k * 9) * s + 3 * s], fill=darker(fur, 0.55))
    E(0, 14, 36, 24, (35, 28, 30), gloss=0.9)                                                           # nose
    for sx in (-1, 1):                                                                                  # eyes
        E(sx * 52, -24, 24, 24, (252, 252, 248), gloss=0.6); E(sx * 52 + look[0] * 9, -24 + look[1] * 9, 13, 13, (25, 18, 15), gloss=0.9)
        ell(L, ox + (sx * 52 + look[0] * 9 - 5) * s, oy + (-30 + look[1] * 9) * s, 4 * s, 4 * s, WHITE, gloss=0)
        if female:
            d = ImageDraw.Draw(L)
            for k in range(3):
                bx = ox + (sx * 52 + sx * (k - 1) * 10) * s; by = oy - 46 * s
                d.line([(bx, by), (bx + sx * (k - 1) * 6 * s, by - 14 * s)], fill=(20, 15, 15), width=max(2, int(4 * s)))
    if blush > 0:
        bl = Image.new("RGBA", L.size, (0, 0, 0, 0)); bd = ImageDraw.Draw(bl)
        for sx in (-1, 1): bd.ellipse([ox + (sx * 78 - 26) * s, oy + 8 * s, ox + (sx * 78 + 26) * s, oy + 36 * s], fill=(255, 90, 120, int(150 * blush)))
        L.alpha_composite(bl.filter(ImageFilter.GaussianBlur(6 * s)))
    if hat == "bowler":
        E(0, -98, 120, 22, (28, 26, 30), gloss=0.5); E(0, -138, 78, 58, (32, 30, 36), gloss=0.6)
        d = ImageDraw.Draw(L); d.rectangle([ox - 76 * s, oy - 112 * s, ox + 76 * s, oy - 98 * s], fill=RED)
    if hat == "lady":
        E(0, -100, 135, 26, (235, 120, 170), gloss=0.4); E(-10, -135, 80, 45, (240, 140, 185), gloss=0.4)
        for k, (fx, fy) in enumerate([(55, -150), (75, -128), (40, -125)]): E(fx, fy, 20, 20, [(255, 250, 250), (255, 220, 90), (255, 255, 255)][k], gloss=0.3)
        E(64, -138, 9, 9, (255, 200, 60))
    if tilt: L = L.rotate(tilt, resample=Image.BICUBIC)
    im.alpha_composite(L, (int(cx - ox), int(cy - oy)))

# ---------- Mrs Bulldog (walking, full body) ----------
def mrs(im, x, y, t, s, walking=True, look=(0, 0), blush=0, mouth=0, wave_=0.0):
    fur = (245, 236, 222); dress = (90, 140, 230)
    ph = t * 9 if walking else 0; bob = abs(math.sin(ph)) * 14 * s if walking else 0; sway = math.sin(ph) * 5 if walking else 0
    shadow(im, x, y, 260 * s)
    for k, sx in enumerate((-1, 1)):                                                     # legs
        lift = max(0, math.sin(ph + k * math.pi)) * 22 * s if walking else 0
        ell(im, x + sx * 45 * s, y - 40 * s - lift, 30 * s, 42 * s, fur); ell(im, x + sx * 50 * s, y - 10 * s - lift, 38 * s, 20 * s, lighter(fur, 0.2))
    by = y - 170 * s - bob
    ell(im, x, by, 125 * s, 120 * s, dress, sway)                                       # dress body
    d = ImageDraw.Draw(im)
    for (dx, dy) in [(-60, -40), (20, -70), (60, 10), (-20, 30), (-70, 60), (50, 80), (0, -10)]:
        ell(im, x + dx * s, by + dy * s, 11 * s, 11 * s, WHITE, gloss=0.2)
    ell(im, x, by - 92 * s, 90 * s, 22 * s, (255, 250, 245), gloss=0.5)                 # collar
    for k in range(7): ell(im, x - 66 * s + k * 22 * s, by - 82 * s + abs(k - 3) * -3 * s, 9 * s, 9 * s, (250, 245, 240), gloss=1.0)  # pearls
    # arms + handbag
    ell(im, x - 128 * s, by + 10 * s, 28 * s, 60 * s, fur, -10 + sway)
    ell(im, x - 140 * s, by + 80 * s, 46 * s, 36 * s, RED, gloss=0.6); d = ImageDraw.Draw(im)
    d.arc([x - 170 * s, by + 20 * s, x - 110 * s, by + 80 * s], 180, 360, fill=(120, 10, 25), width=int(7 * s))
    wa = -60 * smooth(wave_) + 8 * math.sin(t * 14) * smooth(wave_)
    ell(im, x + 125 * s, by + 10 * s - 50 * s * smooth(wave_), 28 * s, 60 * s, fur, 10 + wa)
    head(im, x, by - 190 * s, s * 1.0, fur, female=True, look=look, blush=blush, mouth=mouth, hat="lady", tilt=sway * 0.8)

# ---------- the van with Mr Bulldog ----------
def van(im, x, y, t, s, moving, mr_look=(0, 0), mr_mouth=0, hat_lift=0, passenger=False, p_blush=0, flag=True):
    bounce = (math.sin(t * 22) * 4 if moving else 0) * s
    shadow(im, x + 300 * s, y + 10 * s, 640 * s)
    body = Image.new("RGBA", (int(640 * s), int(420 * s)), (0, 0, 0, 0)); bw, bh = body.size
    # shaded body via vertical gradient + highlight band
    g = np.linspace(0, 1, bh)[:, None]; base = np.array(RED, np.float32)
    col = base * (1.12 - 0.5 * g) + 35 * np.exp(-((g - 0.2) / 0.08) ** 2)
    arr = np.repeat(col[:, None, :], bw, 1) * (1 + 0.16 * TEX[:bh, :bw, None]); arr = np.clip(arr, 0, 255)
    mask = Image.new("L", body.size, 0); md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 120 * s, bw, bh - 40 * s], radius=int(60 * s), fill=255)         # cargo box
    md.rounded_rectangle([int(bw * 0.58), 20 * s, bw - 10 * s, bh - 40 * s], radius=int(90 * s), fill=255)  # cab
    body = Image.fromarray(np.dstack([arr, np.array(mask)]).astype(np.uint8), "RGBA")
    bx, by = int(x), int(y - bh + bounce)
    im.alpha_composite(body, (bx, by)); d = ImageDraw.Draw(im)
    # windscreen / windows
    wx0, wy0 = bx + bw * 0.62, by + 50 * s
    d.rounded_rectangle([wx0, wy0, bx + bw - 40 * s, by + 190 * s], radius=int(40 * s), fill=(150, 200, 235))
    # Mr Bulldog in the cab (and Mrs as passenger)
    if passenger:
        head(im, wx0 + 60 * s, by + 150 * s, 0.5 * s, (245, 236, 222), female=True, look=(1, -0.3), blush=p_blush, mouth=0.4, hat="lady")
    head(im, bx + bw * 0.80, by + 135 * s - hat_lift * 0, 0.62 * s, (205, 155, 105), look=mr_look, mouth=mr_mouth, hat=None)
    # bowler hat that lifts
    hx, hy = bx + bw * 0.80, by + 135 * s - 0.62 * s * 100 - hat_lift * 70 * s
    ell(im, hx, hy, 0.62 * s * 120, 0.62 * s * 22, (28, 26, 30), -hat_lift * 15, 0.5); ell(im, hx, hy - 25 * s, 0.62 * s * 78, 0.62 * s * 58, (32, 30, 36), -hat_lift * 15, 0.6)
    d = ImageDraw.Draw(im)
    # glass glare over window
    gl = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).polygon([(wx0 + 20 * s, wy0), (wx0 + 70 * s, wy0), (wx0 + 10 * s, by + 190 * s), (wx0 - 20 * s, by + 190 * s)], fill=(255, 255, 255, 60)); im.alpha_composite(gl)
    d = ImageDraw.Draw(im)
    # side: Union Jack stripe + MONAD roundel
    d.rectangle([bx + 20 * s, by + 250 * s, bx + bw * 0.58, by + 270 * s], fill=WHITE); d.rectangle([bx + 20 * s, by + 256 * s, bx + bw * 0.58, by + 264 * s], fill=NAVY)
    rcx, rcy = bx + 180 * s, by + 205 * s
    ell(im, rcx, rcy, 72 * s, 72 * s, RED, gloss=0.5); ell(im, rcx, rcy, 56 * s, 56 * s, NAVY, gloss=0.5)
    d = ImageDraw.Draw(im); fm = font(int(64 * s), True); mw = d.textlength("M", font=fm); d.text((rcx - mw / 2, rcy - 40 * s), "M", font=fm, fill=WHITE)
    ft = font(int(44 * s), True); d.text((bx + 270 * s, by + 168 * s), "MONAD", font=ft, fill=WHITE)
    fs = font(int(20 * s)); d.text((bx + 272 * s, by + 220 * s), "PROPER BRITISH GIFTS", font=fs, fill=GOLD)
    # headlight glow + bumper
    hl = Image.new("RGBA", im.size, (0, 0, 0, 0)); hd = ImageDraw.Draw(hl)
    hd.polygon([(bx + bw - 10 * s, by + 280 * s), (bx + bw + 500 * s, by + 200 * s), (bx + bw + 500 * s, by + 420 * s)], fill=(255, 240, 180, 50))
    im.alpha_composite(hl.filter(ImageFilter.GaussianBlur(20)))
    ell(im, bx + bw - 18 * s, by + 285 * s, 18 * s, 22 * s, (255, 245, 200), gloss=1.0)
    ell(im, bx + bw / 2, by + bh - 45 * s, bw / 2, 16 * s, (190, 190, 200), gloss=0.9)
    # wheels with rotating hubs
    rot = x * 0.02
    for wxx in (bx + 140 * s, bx + bw - 140 * s):
        wyy = by + bh - 40 * s - bounce
        ell(im, wxx, wyy, 66 * s, 66 * s, (30, 30, 34), gloss=0.4); ell(im, wxx, wyy, 34 * s, 34 * s, (200, 200, 210), gloss=0.9)
        d = ImageDraw.Draw(im)
        for k in range(4):
            an = rot + k * math.pi / 2; d.line([(wxx, wyy), (wxx + 30 * s * math.cos(an), wyy + 30 * s * math.sin(an))], fill=(90, 90, 100), width=int(6 * s))
    # little Union Jack on the roof aerial
    if flag:
        px, py = bx + bw * 0.68, by + 25 * s; d.line([(px, py), (px, py - 150 * s)], fill=(235, 235, 240), width=int(8 * s))
        fw_, fh_ = int(120 * s), int(64 * s); fl = Image.new("RGBA", (fw_, fh_), NAVY); fd = ImageDraw.Draw(fl)
        fd.line([(0, 0), (fw_, fh_)], fill=WHITE, width=int(12 * s)); fd.line([(0, fh_), (fw_, 0)], fill=WHITE, width=int(12 * s))
        fd.line([(0, 0), (fw_, fh_)], fill=RED, width=int(4 * s)); fd.line([(0, fh_), (fw_, 0)], fill=RED, width=int(4 * s))
        fd.rectangle([fw_ / 2 - 9 * s, 0, fw_ / 2 + 9 * s, fh_], fill=WHITE); fd.rectangle([0, fh_ / 2 - 9 * s, fw_, fh_ / 2 + 9 * s], fill=WHITE)
        fd.rectangle([fw_ / 2 - 5 * s, 0, fw_ / 2 + 5 * s, fh_], fill=RED); fd.rectangle([0, fh_ / 2 - 5 * s, fw_, fh_ / 2 + 5 * s], fill=RED)
        arr = np.asarray(fl).copy(); out = np.zeros((fh_ + 30, fw_, 4), np.uint8)
        for c in range(fw_): o = int(15 + 10 * math.sin(c / fw_ * 6 - t * (14 if moving else 6)) * (c / fw_)); out[o:o + fh_, c] = arr[:, c]
        im.alpha_composite(Image.fromarray(out, "RGBA").transpose(Image.FLIP_LEFT_RIGHT), (int(px - fw_), int(py - 150 * s - 15)))

# ---------- background ----------
def build_bg():
    g = np.linspace(0, 1, H)[:, None]
    sky = np.array([10, 12, 45]) * (1 - g) + np.array([70, 40, 95]) * g
    bg = Image.fromarray(np.repeat(sky[:, None, :], W, 1).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(bg)
    for i in range(90): sx, sy = rng.uniform(0, W), rng.uniform(0, 800); d.ellipse([sx, sy, sx + 3, sy + 3], fill=(255, 255, 255, 170))
    ell(bg, 860, 230, 70, 70, (250, 245, 220), gloss=0.1)                                               # moon
    # terraced houses
    cols = [(150, 70, 55), (170, 90, 60), (130, 60, 50), (160, 80, 70), (140, 75, 55)]
    for i in range(5):
        x0 = i * 220 - 10; c = cols[i]
        d.rectangle([x0, 900, x0 + 220, 1300], fill=c); d.rectangle([x0 + 200, 900, x0 + 220, 1300], fill=darker(c, 0.75))
        d.polygon([(x0 - 10, 905), (x0 + 110, 820), (x0 + 230, 905)], fill=(60, 55, 70))
        d.rectangle([x0 + 150, 780, x0 + 185, 860], fill=darker(c, 0.8))
        for (wx, wy) in ((x0 + 30, 960), (x0 + 125, 960), (x0 + 30, 1110)):
            d.rectangle([wx - 6, wy - 6, wx + 66, wy + 96], fill=(240, 235, 225)); d.rectangle([wx, wy, wx + 60, wy + 90], fill=(255, 205, 110))
            d.line([(wx + 30, wy), (wx + 30, wy + 90)], fill=(240, 235, 225), width=4); d.line([(wx, wy + 45), (wx + 60, wy + 45)], fill=(240, 235, 225), width=4)
        d.rectangle([x0 + 125, 1120, x0 + 185, 1300], fill=[NAVY, (20, 90, 50), RED, (30, 30, 30), (80, 40, 110)][i])
        d.ellipse([x0 + 168, 1205, x0 + 176, 1213], fill=GOLD)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    for i in range(5):
        for (wx, wy) in ((i * 220 + 20, 960), (i * 220 + 115, 960), (i * 220 + 20, 1110)): gd.rectangle([wx - 20, wy - 20, wx + 80, wy + 110], fill=(255, 190, 90, 60))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(25))); d = ImageDraw.Draw(bg)
    d.rectangle([0, 1300, W, 1380], fill=(150, 150, 155)); d.rectangle([0, 1380, W, 1395], fill=(110, 110, 115))     # back pavement + kerb
    road = np.linspace(0, 1, 330)[:, None] * 25 + 50; d2 = np.repeat(np.repeat(road[:, None], W, 1), 3, 2)
    bg.alpha_composite(Image.fromarray(np.dstack([d2, np.full((330, W), 255)]).astype(np.uint8), "RGBA"), (0, 1395)); d = ImageDraw.Draw(bg)
    for x in range(0, W, 180): d.rectangle([x, 1555, x + 100, 1567], fill=(235, 235, 220))
    d.rectangle([0, 1725, W, 1745], fill=(120, 120, 125)); d.rectangle([0, 1745, W, H], fill=(165, 165, 170))      # front pavement
    for x in range(0, W, 120): d.line([(x, 1745), (x - 30, H)], fill=(145, 145, 150), width=3)
    # lamp posts
    for lx in (90, 990):
        d.rectangle([lx - 8, 1000, lx + 8, 1310], fill=(30, 35, 40)); ell(bg, lx, 990, 26, 34, (255, 230, 150), gloss=0.2)
        lg = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(lg).ellipse([lx - 140, 860, lx + 140, 1120], fill=(255, 210, 120, 70)); bg.alpha_composite(lg.filter(ImageFilter.GaussianBlur(30)))
    # bunting between houses
    d = ImageDraw.Draw(bg); pts = [(x, 870 + 50 * math.sin(math.pi * x / W)) for x in range(-20, W + 40, 54)]
    d.line(pts, fill=(230, 230, 230), width=3)
    for j, (px, py) in enumerate(pts[:-1]): d.polygon([(px, py), (px + 46, py + 3), (px + 23, py + 56)], fill=(RED, WHITE, NAVY)[j % 3])
    return bg
_bg = np.asarray(build_bg().filter(ImageFilter.GaussianBlur(2.2))).astype(np.float32)
_tb = np.asarray(TEXI.resize((W, H))).astype(np.float32) / 255 - 0.5
_bg[..., :3] *= (1 + 0.22 * _tb[..., None]) * np.array([1.06, 1.0, 0.9])
BG = Image.fromarray(np.clip(_bg, 0, 255).astype(np.uint8), 'RGBA')

BURSTS = []
for i in range(22):
    ts = 0.2 + i * 0.62 + rng.uniform(-0.15, 0.15); BURSTS.append((ts, rng.uniform(140, 940), rng.uniform(200, 700), [RED, WHITE, (60, 110, 255), GOLD, (255, 120, 200)][i % 5],
                   rng.uniform(0, 2 * math.pi, 70), rng.uniform(200, 420, 70)))
BURSTS.append((10.2, 540, 430, GOLD, rng.uniform(0, 2 * math.pi, 140), rng.uniform(300, 650, 140)))  # big one
def fireworks(im, t):
    fw = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(fw); fl = 0
    for ts, cx, cy, col, ang, spd in BURSTS:
        dt = t - ts
        if dt < -0.5 or dt > 2.0: continue
        if dt < 0: ry = cy + (-dt) * 1000; fd.ellipse([cx - 5, ry - 5, cx + 5, ry + 5], fill=(255, 220, 160, 255)); continue
        fl = max(fl, 1 - dt * 3); fade = max(0, 1 - dt / 1.9)
        for k in range(len(ang)):
            r = spd[k] * (1 - math.exp(-dt * 2.6)) / 2.6 * 1.7; gy = 70 * dt * dt
            x, y = cx + math.cos(ang[k]) * r, cy + math.sin(ang[k]) * r + gy; x2, y2 = cx + math.cos(ang[k]) * r * 0.8, cy + math.sin(ang[k]) * r * 0.8 + gy
            fd.line([(x2, y2), (x, y)], fill=col + (int(255 * fade),), width=5)
    im.alpha_composite(fw.filter(ImageFilter.GaussianBlur(14))); im.alpha_composite(fw)
    if fl > 0: im.alpha_composite(Image.new("RGBA", (W, H), (255, 230, 210, int(28 * fl))))

def heart(im, x, y, s, al=255):
    ell(im, x - 22 * s, y, 26 * s, 26 * s, (235, 30, 70), gloss=0.7); ell(im, x + 22 * s, y, 26 * s, 26 * s, (235, 30, 70), gloss=0.7)
    l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(l).polygon([(x - 46 * s, y + 6 * s), (x + 46 * s, y + 6 * s), (x, y + 58 * s)], fill=(210, 25, 60, al)); im.alpha_composite(l)

def bubble(im, x, y, txt, k, tail_x, tail_y, size=50):
    if k <= 0: return
    sc = back(k / 1.0) if k < 1 else 1; f = font(int(size * sc)); d = ImageDraw.Draw(im)
    tw = d.textlength(txt, font=f)
    while tw > W - 160 and size > 26: size -= 4; f = font(int(size * sc)); tw = d.textlength(txt, font=f)
    x = min(max(x, tw / 2 + 50), W - tw / 2 - 50); bw, bh = tw + 70 * sc, size * sc + 56 * sc
    l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(l)
    ld.rounded_rectangle([x - bw / 2 + 6, y - bh / 2 + 10, x + bw / 2 + 6, y + bh / 2 + 10], radius=int(40 * sc), fill=(0, 0, 0, 90))
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(6))); d = ImageDraw.Draw(im)
    d.polygon([(x - 30 * sc, y + bh / 2 - 6), (x + 20 * sc, y + bh / 2 - 6), (tail_x, tail_y)], fill=WHITE)
    d.rounded_rectangle([x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2], radius=int(40 * sc), fill=WHITE, outline=NAVY, width=5)
    d.text((x - tw / 2, y - size * sc / 2 - 4), txt, font=f, fill=NAVY)

def title(im, t):
    k = (t - 0.3) / 0.35
    if k <= 0 or t > 3.2: return
    al = 1 if t < 2.8 else max(0, (3.2 - t) / 0.4)
    for i, (ln, sz, col) in enumerate([(LN["title1"], 70, WHITE), (LN["title2"], 120, GOLD)]):
        kk = k - i * 0.8;
        if kk <= 0: continue
        sc = back(kk) if kk < 1 else 1; f = font(int(sz * sc), True); d = ImageDraw.Draw(im); tw = d.textlength(ln, font=f)
        y = 210 + i * 110
        l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(l).text(((W - tw) / 2 + 5, y + 7), ln, font=f, fill=(0, 0, 0, int(200 * al))); im.alpha_composite(l.filter(ImageFilter.GaussianBlur(5)))
        l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(l).text(((W - tw) / 2, y), ln, font=f, fill=col + (int(255 * al),)); im.alpha_composite(l)

def exhaust(im, x, y, t):
    l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(l)
    for k in range(6):
        ph = (t * 1.6 + k / 6) % 1; px = x - ph * 160; py = y - ph * 60; r = 12 + ph * 36
        ld.ellipse([px - r, py - r, px + r, py + r], fill=(220, 220, 230, int(160 * (1 - ph))))
    im.alpha_composite(l.filter(ImageFilter.GaussianBlur(6)))

# ---------- timeline ----------
VIG = Image.new('L', (W, H), 0); _vd = ImageDraw.Draw(VIG)
for _i in range(30): _vd.ellipse([-260 + _i * 12, -380 + _i * 16, W + 260 - _i * 12, H + 380 - _i * 16], fill=int(255 * _i / 30))
VIG = VIG.filter(ImageFilter.GaussianBlur(70))
def frame(t):
    im = BG.copy(); fireworks(im, t)
    # van path
    if t < 6.0: vx = -1000 + 890 * smooth(t / 6.0) ** 0.8; moving = t < 5.8
    elif t < 12.6: vx = -110; moving = False
    else: vx = -110 + 1650 * ((t - 12.6) / 2.4) ** 1.8; moving = True
    vy = 1690; s_van = 1.3
    honk = (6.2 <= t < 6.6) or (6.8 <= t < 7.2) or (13.0 <= t < 13.4)
    hat = smooth((t - 7.4) / 0.3) * (1 - smooth((t - 8.6) / 0.3))
    passenger = t >= 12.1
    # Mrs path: walk in from right on front pavement
    if t < 3.0: mx = 1450
    elif t < 7.0: mx = 1450 - 560 * ((t - 3.0) / 4.0)
    else: mx = 890
    walking = 3.0 <= t < 7.0
    look_up = 10.0 <= t < 11.8
    jump = (t - 11.6) / 0.6  # Mrs hops into the van
    if moving: exhaust(im, vx + 10, vy - 60, t)
    van(im, vx, vy, t, s_van, moving, mr_look=(0, -1) if look_up else ((1, 0.4) if 6 < t < 12 else (1, 0)),
        mr_mouth=0.8 if honk or (7.4 < t < 8.8) else (0.5 if look_up else 0.15), hat_lift=hat, passenger=passenger, p_blush=1 if passenger else 0)
    if not passenger:
        if 0 <= jump < 1:
            jx = mx + (vx + 560 - mx) * smooth(jump); jy = 1880 - 500 * math.sin(math.pi * jump) - 200 * smooth(jump); s = 1.0 - 0.45 * smooth(jump)
            mrs(im, jx, jy, t, s * 1.15, walking=False, look=(-1, 0), blush=1, mouth=0.6)
        else:
            blush = smooth((t - 8.6) / 0.4)
            mrs(im, mx, 1880, t, 1.15, walking=walking, look=(0, -1) if look_up else (-1, 0.2) if t > 6 else (-1, 0),
                blush=blush, mouth=0.7 if (8.8 < t < 10) or look_up else 0.2, wave_=smooth((t - 8.6) / 0.3) * (1 - smooth((t - 9.8) / 0.3)))
    # speech bubbles
    if honk: bubble(im, min(W - 230, vx + 720), vy - 760, LN["honk"], (t % 1 + 0.3) * 3 if t < 7.3 else (t - 13.0) * 4, min(W - 120, vx + 760), vy - 560, 60)
    if 7.4 < t < 9.0: bubble(im, 520, 640, LN["mr1"], (t - 7.4) * 3, vx + 660, 1150, 56)
    if 8.9 < t < 10.4: bubble(im, 560, 900, LN["mrs"], (t - 8.9) * 3, mx - 40, 1330, 56)
    if 10.4 < t < 11.8: bubble(im, 540, 1000, LN["mr2"], (t - 10.4) * 3, vx + 660, 1150, 52)
    if 13.4 < t < 15: bubble(im, 560, 820, LN["bye"], (t - 13.4) * 3, min(W - 80, vx + 700), vy - 560, 70)
    # hearts
    if 8.8 < t < 12:
        for k in range(6):
            ph = (t - 8.8 - k * 0.45)
            if 0 < ph < 2.4: heart(im, mx - 60 + 140 * math.sin(k * 2.1) + 20 * math.sin(ph * 4), 1320 - ph * 330, 0.6 + 0.2 * (k % 2))
    if t > 12.8:
        for k in range(5):
            ph = t - 12.8 - k * 0.3
            if 0 < ph < 2: heart(im, vx + 560 + 60 * math.sin(k * 1.7 + ph * 3), vy - 600 - ph * 260, 0.5)
    title(im, t)
    # gentle camera push + vignette + fade to card
    z = 1.0 + 0.04 * t / T; w2, h2 = W / z, H / z
    out = im.crop((int((W - w2) / 2), int((H - h2) / 2), int((W + w2) / 2), int((H + h2) / 2))).resize((W, H), Image.BILINEAR).convert("RGB")
    out = Image.composite(out, Image.new('RGB', (W, H), (20, 12, 8)), VIG)
    if T - t < 0.2: out = Image.blend(out, Image.new("RGB", (W, H), WHITE), (0.2 - (T - t)) / 0.2 * 0.85)
    return out

if a.frames:
    fr = [frame(float(x)).resize((360, 640)) for x in a.frames.split(",")]
    o = Image.new("RGB", (360 * len(fr), 640)); [o.paste(f, (i * 360, 0)) for i, f in enumerate(fr)]; o.save(a.out); raise SystemExit

p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
buf = None
for f in range(int(T * FPS)):
    if f % 2 == 0: FRAME[0] = f; buf = np.asarray(frame(f / FPS)).tobytes()
    p.stdin.write(buf)
p.stdin.close(); p.wait()

# ---------- jaunty music-hall soundtrack ----------
SR = 44100; dur = T + CARD; n = int(SR * dur); A = np.zeros(n)
def tt(sec): return np.arange(int(sec * SR)) / SR
def add(sig, st, vol=1.0):
    s = int(st * SR); e = min(n, s + len(sig))
    if 0 <= s < n: A[s:e] += vol * sig[:e - s]
def tone(f, sec, kind="brass"):
    x = tt(sec); env = np.minimum(1, x / 0.02) * np.exp(-x * (3 if kind == "pluck" else 1.6))
    if kind == "brass": return env * sum(np.sin(2 * math.pi * f * h * x) / h for h in range(1, 7)) * 0.13
    if kind == "tuba": return env * (np.sin(2 * math.pi * f * x) + 0.4 * np.sin(4 * math.pi * f * x)) * 0.3
    return env * (np.sin(2 * math.pi * f * x) + 0.5 * np.sin(6 * math.pi * f * x)) * 0.12
NOTE = {n_: 440 * 2 ** ((i - 9) / 12) for i, n_ in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}
def nf(nm, oc=4): return NOTE[nm] * 2 ** (oc - 4)
beat = 0.3; chords = [("F", "A", "C"), ("C", "E", "G"), ("F", "A", "C"), ("A#", "D", "F"), ("F", "A", "C"), ("C", "E", "G"), ("F", "A", "C"), ("C", "E", "G")]
mel = ["C5", "A", "C5", "F5", "E5", "D5", "C5", "A", "G", "A", "A#", "D5", "C5", "A", "G", "F", "A", "C5", "F5", "G5", "A5", "G5", "F5", "D5", "C5", "D5", "E5", "G5", "F5", "-", "F5", "-"]
def mf(m): return nf(m[:-1], 5) if m[-1] == "5" else nf(m, 4)
t0 = 0.0; i = 0
while t0 < T + 1.2:
    ch = chords[(i // 4) % len(chords)]
    if i % 2 == 0: add(tone(nf(ch[0], 2) if i % 4 == 0 else nf(ch[2], 2), beat * 0.9, "tuba"), t0)
    else:
        for c in ch: add(tone(nf(c, 4), beat * 0.6, "pluck"), t0, 0.9)
    m = mel[i % len(mel)]
    if m != "-" and t0 > 0.6: add(tone(mf(m), beat * 0.95, "brass"), t0, 0.55)
    if i % 4 == 0: add(np.random.default_rng(i).normal(0, 1, int(0.08 * SR)) * np.exp(-tt(0.08) * 50) * 0.25, t0)
    t0 += beat; i += 1
def honk_s(sec=0.35):
    x = tt(sec); sq = np.sign(np.sin(2 * math.pi * 330 * x)) + np.sign(np.sin(2 * math.pi * 415 * x)); return sq * np.minimum(1, x / 0.01) * np.minimum(1, (sec - x) / 0.03) * 0.15
for h in (6.2, 6.8, 13.0): add(honk_s(), h)
def pop(sec=0.12): x = tt(sec); return np.sin(2 * math.pi * (900 + 1800 * x / sec) * x) * np.exp(-x * 30) * 0.35
def boing(sec=0.5): x = tt(sec); return np.sin(2 * math.pi * np.cumsum(300 + 250 * np.sin(x * 40) * np.exp(-x * 5)) / SR) * np.exp(-x * 5) * 0.4
for k in range(6): add(pop(), 8.8 + k * 0.45)
add(boing(), 11.6); add(pop(), 7.4); add(pop(), 8.9); add(pop(), 10.4); add(pop(), 13.4)
for ts, *_ in BURSTS:
    x = tt(0.9); add((np.sin(2 * math.pi * (60 * np.exp(-x * 4) + 40) * x) * np.exp(-x * 4) + rng.normal(0, 1, len(x)) * np.exp(-x * 25) * 0.3) * 0.35, ts)
    add((rng.random(int(SR)) > 0.996) * rng.normal(0, 1, int(SR)) * np.exp(-tt(1.0) * 2.5) * 0.4, ts + 0.05)
# finale on card: tada chord
for f in (nf("F", 4), nf("A", 4), nf("C", 5), nf("F", 5)): add(tone(f, CARD, "brass") * 1.4, T)
add(tone(nf("F", 2), CARD, "tuba"), T)
A = np.tanh(A * 1.1) * 0.85; fd = int(1.0 * SR); A[-fd:] *= np.linspace(1, 0, fd)
with wave.open(a.wav, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((A * 32767).astype(np.int16).tobytes())
print("done")
