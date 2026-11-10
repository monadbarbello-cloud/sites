"""Add the Monad branded ending to any clip.
Usage: python brand.py --video URL_OR_PATH --out out.mp4 [--strap "Proper British. Properly Monad."]
Makes it 1080x1920 (blurred fill if needed), then a 3s end card: roundel logo, MONAD, strapline, link in bio."""
import argparse, math, os, subprocess, tempfile, urllib.request
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("--video", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--strap", default="Proper British. Properly Monad.")
ap.add_argument("--sub", default="Gifts with a stiff upper lip")
a = ap.parse_args()
W, H, FPS, CARD = 1080, 1920, 30, 3.0
NAVY = (11, 31, 68); RED = (200, 16, 46); GOLD = (184, 137, 43); WHITE = (255, 255, 255)
tmp = tempfile.mkdtemp()
def font(names, size):
    for n in names:
        for d in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/truetype/liberation/"):
            try: return ImageFont.truetype(d + n, size)
            except OSError: pass
    return ImageFont.load_default()
SERIF = ["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"]; SANS = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]

src = a.video
if src.startswith("http"):
    p = os.path.join(tmp, "in.mp4")
    req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
    open(p, "wb").write(urllib.request.urlopen(req, timeout=120).read()); src = p

def has_audio(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", f], capture_output=True, text=True)
    return bool(r.stdout.strip())

# 1) main part -> 1080x1920, blurred fill behind, 30fps, stereo audio
main = os.path.join(tmp, "main.mp4")
vf = (f"[0:v]split=2[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:2,eq=brightness=-0.15[bg];"
      f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={FPS},setsar=1,format=yuv420p[v]")
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src]
if not has_audio(src): cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
cmd += ["-filter_complex", vf, "-map", "[v]", "-map", "0:a" if has_audio(src) else "1:a", "-shortest",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "aac", "-ar", "44100", "-ac", "2", main]
subprocess.run(cmd, check=True)

# 2) end card frames
def card(t):
    im = Image.new("RGB", (W, H), NAVY); d = ImageDraw.Draw(im)
    for i in range(0, H, 6):  # soft vignette
        k = abs(i - H/2) / (H/2); d.line([(0, i), (W, i)], fill=tuple(int(c * (1 - 0.35*k)) for c in NAVY), width=6)
    e = lambda x: 1 - (1 - min(1, max(0, x))) ** 3
    s = 0.6 + 0.4 * e(t / 0.5) + (0.04 * math.sin(t * 6) * max(0, 1 - t)) # pop in
    cx, cy, r = W/2, 700, int(250 * s)
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=NAVY, outline=RED, width=int(46*s))
    d.ellipse([cx-r+int(62*s), cy-r+int(62*s), cx+r-int(62*s), cy+r-int(62*s)], outline=WHITE, width=max(2, int(8*s)))
    fm = font(SERIF, int(280*s)); mw = d.textlength("M", font=fm); d.text((cx - mw/2, cy - 190*s), "M", font=fm, fill=WHITE)
    fe = font(SANS, int(30*s)); ew = d.textlength("EST. 2026", font=fe); d.text((cx - ew/2, cy + 110*s), "EST. 2026", font=fe, fill=WHITE)
    a1 = e((t - 0.35) / 0.4)
    if a1 > 0:
        ft = font(SERIF, 120); tw = d.textlength("MONAD", font=ft); d.text(((W - tw)/2, 1030 + 30*(1-a1)), "MONAD", font=ft, fill=WHITE)
        fg = font(SANS, 40); gw = d.textlength("PROPER BRITISH GIFTS", font=fg); d.text(((W - gw)/2, 1170), "PROPER BRITISH GIFTS", font=fg, fill=GOLD)
    a2 = e((t - 0.8) / 0.4)
    if a2 > 0:
        uw = 600 * a2; d.rectangle([W/2 - uw/2, 1250, W/2 + uw/2, 1262], fill=RED)
        fs = font(SERIF, 70)
        lines = [x.strip() + ("." if not x.strip().endswith((".", "!", "?")) else "") for x in a.strap.replace("! ", "!|").replace(". ", ".|").split("|") if x.strip()]
        for i, ln in enumerate(lines):
            lw = d.textlength(ln, font=fs); d.text(((W - lw)/2, 1310 + i*84), ln, font=fs, fill=WHITE)
        fsub = font(SANS, 38); sw_ = d.textlength(a.sub, font=fsub); d.text(((W - sw_)/2, 1320 + len(lines)*84 + 20), a.sub, font=fsub, fill=(200, 205, 220))
    a3 = e((t - 1.3) / 0.4)
    if a3 > 0:
        fl = font(SANS, 48); txt = "Tap the link in bio  →"; lw = d.textlength(txt, font=fl)
        d.rounded_rectangle([(W - lw)/2 - 40, 1640, (W + lw)/2 + 40, 1740], radius=50, fill=RED)
        d.text(((W - lw)/2, 1663), txt, font=fl, fill=WHITE)
    return im

endc = os.path.join(tmp, "end.mp4")
pr = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-f", "lavfi", "-i", "sine=frequency=988:duration=3:sample_rate=44100",
                       "-filter_complex", "[1:a]volume=0.12,afade=t=out:st=0.6:d=2.2,aformat=channel_layouts=stereo[a]", "-map", "0:v", "-map", "[a]",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", endc], stdin=subprocess.PIPE)
for f in range(int(FPS * CARD)): pr.stdin.write(card(f / FPS).tobytes())
pr.stdin.close(); pr.wait()

# 3) join
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", main, "-i", endc, "-filter_complex",
                "[0:v]setsar=1[v0];[1:v]setsar=1[v1];[v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "aac", "-movflags", "+faststart", a.out], check=True)
print("done", a.out)
