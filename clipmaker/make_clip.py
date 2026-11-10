"""Monad dramatic 10s TikTok clip v2 — product 'comes alive' then settles.
Usage: python make_clip.py --images URL_OR_PATH[,URL2...] --headline "Could be worse." --out out.mp4
Picks the image where the product is fully in frame. 1080x1920, 30fps, with sound."""
import argparse, io, math, random, subprocess, urllib.request, wave
from collections import deque
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("--images", required=True); ap.add_argument("--headline", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--hook", default="WAIT FOR IT…")
a = ap.parse_args()
W, H, FPS, DUR = 1080, 1920, 30, 10.0
N = int(FPS * DUR)
NAVY = (11, 31, 68); RED = (200, 16, 46); GOLD = (184, 137, 43); WHITE = (255, 255, 255)
random.seed(3); rng = np.random.default_rng(3)
def font(names, size):
    for n in names:
        for d in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/truetype/liberation/", "/usr/share/fonts/truetype/"):
            try: return ImageFont.truetype(d + n, size)
            except OSError: pass
    return ImageFont.load_default()
SERIF = ["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"]; SANS = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]

def load(src):
    if src.startswith("http"):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert("RGB")
    return Image.open(src).convert("RGB")

def cutout(im):
    w0, h0 = im.size; arr = np.asarray(im).astype(np.int16)
    nw = arr.min(axis=2) > 228; bg = np.zeros((h0, w0), bool); q = deque()
    for x in range(w0):
        for y in (0, h0 - 1):
            if nw[y, x] and not bg[y, x]: bg[y, x] = True; q.append((y, x))
    for y in range(h0):
        for x in (0, w0 - 1):
            if nw[y, x] and not bg[y, x]: bg[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = y+dy, x+dx
            if 0 <= ny < h0 and 0 <= nx < w0 and nw[ny, nx] and not bg[ny, nx]: bg[ny, nx] = True; q.append((ny, nx))
    al = Image.fromarray(np.where(bg, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    p = im.convert("RGBA"); p.putalpha(al)
    bb = p.getbbox(); margin = min(bb[0], bb[1], w0 - bb[2], h0 - bb[3])
    fill = (bb[2]-bb[0])*(bb[3]-bb[1]) / (w0*h0)
    crop = np.asarray(al.crop(bb)); solid = (crop > 128).mean()
    if solid < 0.72:   # white product on white background: keep the photo as a premium card instead of cutting it out
        card = im.convert('RGBA'); m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w0-1, h0-1], radius=int(w0*0.06), fill=255); card.putalpha(m)
        return card, 50, 0.5
    return p.crop(bb), margin, fill

best = None
for idx, s in enumerate(a.images.split(",")):
    try:
        p, m, f = cutout(load(s.strip()))
        score = (m > 6) * 10 - idx * 0.8 + f   # fully in frame first, prefer front views (listed first), then biggest
        if best is None or score > best[0]: best = (score, p)
    except Exception as e: print("skip", s, e)
prod = best[1]
sc = min(820 / prod.size[0], 980 / prod.size[1])
prod = prod.resize((int(prod.size[0]*sc), int(prod.size[1]*sc)), Image.LANCZOS)
PA = prod.getchannel("A")
sil = Image.new("RGBA", prod.size, (6, 10, 22, 255)); sil.putalpha(PA)
rim = Image.new("RGBA", prod.size, GOLD + (255,)); rim.putalpha(PA.filter(ImageFilter.GaussianBlur(22)).point(lambda v: min(255, int(v*1.6))))

def eo(t): return 1 - (1 - t) ** 3
def eob(t, s=2.0): t -= 1; return t*t*((s+1)*t + s) + 1
def cl(v, lo=0, hi=1): return max(lo, min(hi, v))
def sg(t, x0, x1): return cl((t - x0) / (x1 - x0))

yy = np.linspace(0, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
rad = np.sqrt(xx**2 + ((yy - 0.47) * 1.5)**2)
def bg(light):
    k = np.clip(1 - rad * 0.95, 0, 1) * light
    arr = np.stack([4 + (NAVY[i] * 1.6) * k + (GOLD[i] * 0.25) * k**4 for i in range(3)], axis=2)
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))
BGS = {round(l, 2): bg(l) for l in np.linspace(0, 1, 21)}
def getbg(l): return BGS[round(round(l * 20) / 20, 2)].copy()

B = 60; bx = rng.uniform(0, W, B); by = rng.uniform(0, H, B); br = rng.uniform(6, 26, B); bs = rng.uniform(10, 50, B)
P = 120; pang = rng.uniform(0, 2*math.pi, P); pspd = rng.uniform(400, 1300, P); psz = rng.uniform(3, 9, P)
pcol = [GOLD if random.random() < .65 else (WHITE if random.random() < .6 else RED) for _ in range(P)]

def draw_text(d, y, txt, f, fill, stroke=6):
    tw = d.textlength(txt, font=f); d.text(((W - tw)/2, y), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=(5, 10, 25))

def wrap(txt, f, maxw, d):
    out, cur = [], ""
    for wd in txt.split():
        t2 = (cur + " " + wd).strip()
        if d.textlength(t2, font=f) <= maxw: cur = t2
        else: out.append(cur); cur = wd
    return out + [cur]

# ---- audio ----
sr = 44100; tt = np.arange(int(sr*DUR)) / sr; au = np.zeros_like(tt); nz = rng.standard_normal(len(tt))
def env(t0, at, dc): return np.where(tt >= t0, np.exp(-(tt - t0) / dc), 0) * np.clip((tt - t0) / at, 0, 1)
au += 0.30 * nz * (np.clip((tt - 0.1) / 1.1, 0, 1) ** 3) * (tt < 1.2)             # riser
au += 0.08 * np.sin(2*np.pi*(40 + 30*tt)*tt) * (tt < 1.2)
au += 1.0 * np.sin(2*np.pi*(60 - 25*np.clip(tt-1.2, 0, 1))*tt) * env(1.2, .004, .7)  # boom
au += 0.3 * nz * env(1.2, .001, .15)
for k, t0 in enumerate((3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)): au += 0.35 * np.sin(2*np.pi*70*tt) * env(t0, .003, .16) + 0.05 * nz * env(t0 + .25, .001, .04)
for f0 in (659, 988, 1319): au += 0.1 * np.sin(2*np.pi*f0*tt) * env(8.4, .01, 1.1)
au = (au / np.abs(au).max() * 0.92 * 32767).astype(np.int16)
with wave.open(a.out + ".wav", "wb") as wf: wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(au.tobytes())

fh = font(SERIF, 104); fk = font(SANS, 46)
pr = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", a.out + ".v.mp4"], stdin=subprocess.PIPE)
CY = H * 0.50
for fr in range(N):
    t = fr / FPS
    light = sg(t, 1.2, 1.5) * (0.75 + 0.25 * (1 - sg(t, 6.5, 8.0)))
    frame = getbg(max(light, 0.08 * sg(t, 0, 1.2)))
    d = ImageDraw.Draw(frame, "RGBA")
    # bokeh dust
    for i in range(B):
        y = (by[i] - bs[i] * t) % H; x = bx[i] + 12 * math.sin(t + i)
        al = int((40 + 50 * light) * (0.4 + 0.6 * math.sin(t * 1.3 + i) ** 2))
        d.ellipse([x - br[i], y - br[i], x + br[i], y + br[i]], fill=GOLD + (al,))
    # turntable wobble + hop (alive 2.6-6.6), settle after
    alive = sg(t, 2.4, 2.8) * (1 - sg(t, 6.2, 7.6))
    ph = (t - 2.4) * math.pi * 2.0
    hop = abs(math.sin(ph)) * alive
    turn = math.cos(ph * 0.5) * 0.18 * alive                     # fake 3D turn
    sqx = (1 - abs(turn)) * (1 - 0.05 * hop); sqy = 1 + 0.08 * hop
    rot = 6 * math.sin(ph) * alive
    zoom = 1.0 + 0.06 * sg(t, 7.0, 10.0)                          # slow push-in at the end
    if t < 1.2: zoom *= 0.92 + 0.08 * eo(sg(t, 0, 1.2))
    shake = 22 * (1 - sg(t, 1.2, 1.7)); ox, oy = random.uniform(-shake, shake), random.uniform(-shake, shake)
    pw, ph_ = max(2, int(prod.size[0] * sqx * zoom)), max(2, int(prod.size[1] * sqy * zoom))
    cx, cy = W/2 + ox, CY - 80 * hop + oy
    # shadow
    sh = Image.new("L", (W, H), 0); sd = ImageDraw.Draw(sh); sw = pw * 0.7 * (1 - 0.3*hop)
    sd.ellipse([W/2 - sw/2, CY + ph_/2 - 20, W/2 + sw/2, CY + ph_/2 + 50], fill=int(170 * (0.3 + 0.7*light) * (1 - 0.4*hop)))
    frame.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(28)))
    # rim glow
    g = rim.resize((int(pw * 1.08), int(ph_ * 1.06))).rotate(rot, expand=True)
    gi = (0.9 if t < 1.2 else 0.35 + 0.5 * light * (0.6 + 0.4 * math.sin(t * 6) * alive))
    g.putalpha(g.getchannel("A").point(lambda v: int(v * gi)))
    frame.paste(g, (int(cx - g.size[0]/2), int(cy - g.size[1]/2)), g)
    # product: silhouette before the hit, revealed after
    pimg = prod.resize((pw, ph_), Image.BILINEAR)
    if t < 1.5:
        rv = sg(t, 1.2, 1.5)
        pimg = Image.blend(sil.resize((pw, ph_)), pimg, rv) if rv > 0 else sil.resize((pw, ph_))
        pimg.putalpha(PA.resize((pw, ph_)))
    pimg = pimg.rotate(rot, resample=Image.BICUBIC, expand=True)
    frame.paste(pimg, (int(cx - pimg.size[0]/2), int(cy - pimg.size[1]/2)), pimg)
    d = ImageDraw.Draw(frame, "RGBA")
    # light sweep across product while alive
    sw_t = (t - 2.6) % 1.6 / 1.6
    if alive > 0.2 and sw_t < 0.5:
        lx = cx - pw/2 + (pw + 300) * (sw_t / 0.5) - 150
        lay = Image.new("L", (W, H), 0); ld = ImageDraw.Draw(lay)
        ld.polygon([(lx, cy - ph_/2), (lx + 90, cy - ph_/2), (lx - 60, cy + ph_/2), (lx - 150, cy + ph_/2)], fill=int(110 * alive))
        mask = Image.new("L", (W, H), 0); mask.paste(PA.resize((pw, ph_)).rotate(rot, expand=True), (int(cx - pimg.size[0]/2), int(cy - pimg.size[1]/2)))
        lay = Image.fromarray(np.minimum(np.asarray(lay.filter(ImageFilter.GaussianBlur(12))), np.asarray(mask)))
        frame.paste(WHITE, (0, 0), lay); d = ImageDraw.Draw(frame, "RGBA")
    # spark burst on hit, then they fall and settle
    pt = t - 1.2
    if 0 < pt < 7:
        fade = 1 - sg(t, 6.8, 8.2)
        for i in range(P):
            dist = pspd[i] / 1.6 * (1 - math.exp(-pt * 1.6))
            x = W/2 + math.cos(pang[i]) * dist; y = min(CY + math.sin(pang[i]) * dist + 90 * pt**2, CY + ph_/2 + 40 + (i % 25))
            s = psz[i] * fade
            if s > .5: d.ellipse([x - s, y - s, x + s, y + s], fill=pcol[i] + (int(255 * fade),))
    # hook text before hit
    if 0.25 < t < 1.2:
        k = sg(t, 0.25, 0.5); draw_text(d, H*0.18, a.hook, fk, WHITE + (int(255*k),), 4)
    # headline: words slam in on the beats
    if t > 3.0:
        lines = wrap(a.headline.upper(), fh, 980, d); y0 = 150; wi = 0
        for li, line in enumerate(lines):
            words = line.split(); x = (W - d.textlength(line, font=fh)) / 2
            for wd in words:
                ts = 3.0 + wi * 0.5; wi += 1
                if t >= ts:
                    k = eob(sg(t, ts, ts + 0.22), 3.0); f2 = font(SERIF, max(10, int(104 * (0.3 + 0.7 * k))))
                    ww = d.textlength(wd, font=fh); w2 = d.textlength(wd, font=f2)
                    d.text((x + (ww - w2)/2, y0 + li*118 + (104 - f2.size)/2), wd, font=f2, fill=WHITE, stroke_width=6, stroke_fill=(5, 10, 25))
                x += d.textlength(wd + " ", font=fh)
        uw = 700 * eo(sg(t, 3.0 + wi*0.5, 3.4 + wi*0.5)); yb = y0 + len(lines)*118 + 18
        if uw > 1: d.rectangle([W/2 - uw/2, yb, W/2 + uw/2, yb + 12], fill=RED)
    # end card
    if t > 8.2:
        k = sg(t, 8.2, 8.7); top = H - int(420 * eo(k))
        d.rectangle([0, top, W, H], fill=NAVY + (240,)); d.rectangle([0, top, W, top + 8], fill=RED)
        if k > 0.5:
            rx, ry, rr = 160, top + 210, 95
            d.ellipse([rx-rr, ry-rr, rx+rr, ry+rr], fill=NAVY, outline=RED, width=16)
            d.ellipse([rx-rr+22, ry-rr+22, rx+rr-22, ry+rr-22], outline=WHITE, width=3)
            fm = font(SERIF, 90); d.text((rx - d.textlength("M", font=fm)/2, ry - 60), "M", font=fm, fill=WHITE)
            d.text((300, top + 95), "MONAD", font=font(SERIF, 76), fill=WHITE)
            d.text((302, top + 190), "PROPER BRITISH GIFTS", font=font(SANS, 34), fill=GOLD)
            d.text((302, top + 255), "Tap the link in bio  →", font=font(SANS, 42), fill=WHITE)
    # flash
    fl = 1 - sg(t, 1.2, 1.55)
    if 1.2 <= t and fl > 0: frame = Image.blend(frame, Image.new("RGB", (W, H), (255, 246, 225)), 0.9 * fl)
    # vignette + letterbox feel
    pr.stdin.write(frame.tobytes())
pr.stdin.close(); pr.wait()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.out + ".v.mp4", "-i", a.out + ".wav", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], check=True)
print("done", a.out)
