"""
The 20 classic Scare-TV scares, drawn and synthesized from code (`make scares`).

Each scare is a short video (.mp4) + its sound (.wav) with the same name,
made 100% from code: no images or audio from any movie.

Usage:
    make scares                              # builds all 20 into media/
    python manage.py make_scares 03 07       # only scares 03 and 07
    python manage.py make_scares --sounds    # only the sounds (and the live-scare tracks)

Only needed to rebuild them: numpy, pillow, scipy and ffmpeg.
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import signal

from domain.rules import possessions
from infrastructure.services.synth import horror_audio as ha

W, H = 854, 480
FPS = 24
SR = ha.SR          # 44.1 kHz stereo: at 22 kHz mono the scares sounded like a toy
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "media")

rng = np.random.default_rng(1031)


# ---------------------------------------------------------------- fonts
def font(size, serif=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if serif else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default(size=size)


# ---------------------------------------------------------------- image effects
_yy, _xx = np.mgrid[0:H, 0:W]
VIGNETTE = 1 - 0.85 * (((_xx - W / 2) / (W / 1.6)) ** 2 + ((_yy - H / 2) / (H / 1.3)) ** 2)
VIGNETTE = np.clip(VIGNETTE, 0, 1)[..., None]


def blank(v=0.0):
    return np.full((H, W, 3), v, dtype=np.float32)


def grain(f, amt=0.06):
    return f + rng.normal(0, amt, (H, W, 1)).astype(np.float32)


def static(amt=1.0):
    small = rng.random((H // 3 + 1, W // 3 + 1)).astype(np.float32)
    big = np.kron(small, np.ones((3, 3), dtype=np.float32))[:H, :W]
    return np.repeat(big[..., None], 3, axis=2) * amt


def glitch(f, k=0.5):
    out = f.copy()
    for _ in range(int(12 * k)):
        y = rng.integers(0, H - 10)
        h = rng.integers(4, 40)
        out[y:y + h] = np.roll(out[y:y + h], rng.integers(-int(80 * k) - 1, int(80 * k) + 1), axis=1)
    s = int(14 * k)
    if s:
        out[..., 0] = np.roll(out[..., 0], s, axis=1)
        out[..., 2] = np.roll(out[..., 2], -s, axis=1)
    return out


def shake(f, k=10):
    return np.roll(np.roll(f, rng.integers(-k, k + 1), 0), rng.integers(-k, k + 1), 1)


def red(f, k=0.6):
    out = f.copy()
    out[..., 1] *= 1 - k
    out[..., 2] *= 1 - k
    return out


def finish(f, vig=True, g=0.03):
    if vig:
        f = f * VIGNETTE
    f = grain(f, g)
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


def pil(f):
    return Image.fromarray((np.clip(f, 0, 1) * 255).astype(np.uint8))


def arr(img):
    return np.asarray(img.convert("RGB")).astype(np.float32) / 255


def paste_layer(f, layer):
    """Composites a PIL RGBA layer over the numpy frame."""
    a = np.asarray(layer).astype(np.float32) / 255
    alpha = a[..., 3:4]
    return f * (1 - alpha) + a[..., :3] * alpha


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def text_layer(txt, size, color=(230, 230, 230), y=None, serif=True, jitter=0):
    L = layer()
    d = ImageDraw.Draw(L)
    fnt = font(size, serif)
    bbox = d.textbbox((0, 0), txt, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (W - tw) // 2 + (rng.integers(-jitter, jitter + 1) if jitter else 0)
    yy = (H - th) // 2 if y is None else y
    d.text((x, yy), txt, font=fnt, fill=color + (255,))
    return L


# ---------------------------------------------------------------- original creatures
def face(cx, cy, s, mouth="grin", eyes="hollow", skin=(214, 220, 210), cracks=0,
         tilt=0, pupils=(255, 40, 40), blur=1.2, upside=False):
    """An original ghostly face: pale oval, hollow eyes, configurable mouth."""
    s = float(s)
    L = layer()
    d = ImageDraw.Draw(L)
    fw, fh = 270 * s, 350 * s
    d.ellipse([cx - fw / 2, cy - fh / 2, cx + fw / 2, cy + fh / 2], fill=skin + (255,))
    # soft shading: sunken sockets, temples and cheeks (a very blurred layer)
    S = layer()
    sd = ImageDraw.Draw(S)
    for side in (-1, 1):
        ex = cx + side * 62 * s
        sd.ellipse([ex - 62 * s, cy - 120 * s, ex + 62 * s, cy + 30 * s], fill=(20, 20, 25, 170))
        sd.ellipse([cx + side * fw * 0.33 - 30 * s, cy + 20 * s, cx + side * fw * 0.33 + 30 * s, cy + 120 * s],
                   fill=(60, 60, 60, 90))
        # dark tears running down from the eyes
        sd.line([ex + side * 5 * s, cy, ex + side * 12 * s, cy + 110 * s], fill=(15, 10, 10, 160),
                width=max(1, int(9 * s)))
    S = S.filter(ImageFilter.GaussianBlur(float(max(1, 10 * s))))
    edge = Image.new("L", (W, H), 0)
    ImageDraw.Draw(edge).ellipse([cx - fw / 2, cy - fh / 2, cx + fw / 2, cy + fh / 2], fill=255)
    S.putalpha(Image.composite(S.getchannel("A"), Image.new("L", (W, H), 0), edge))
    L = Image.alpha_composite(L, S)
    d = ImageDraw.Draw(L)
    ey = cy - 45 * s
    for side in (-1, 1):
        ex = cx + side * 62 * s
        if eyes == "hollow":
            d.ellipse([ex - 38 * s, ey - 48 * s, ex + 38 * s, ey + 48 * s], fill=(5, 5, 8, 255))
            if pupils:
                d.ellipse([ex - 6 * s, ey - 6 * s, ex + 6 * s, ey + 6 * s], fill=pupils + (255,))
        elif eyes == "wide":
            d.ellipse([ex - 42 * s, ey - 34 * s, ex + 42 * s, ey + 34 * s], fill=(240, 240, 230, 255))
            d.ellipse([ex - 9 * s, ey - 9 * s, ex + 9 * s, ey + 9 * s], fill=(0, 0, 0, 255))
            d.ellipse([ex - 44 * s, ey - 36 * s, ex + 44 * s, ey + 36 * s], outline=(90, 20, 20, 255),
                      width=max(1, int(4 * s)))
        elif eyes == "sewn":
            d.line([ex - 35 * s, ey, ex + 35 * s, ey], fill=(30, 10, 10, 255), width=max(1, int(5 * s)))
            for k in range(-3, 4):
                d.line([ex + k * 10 * s, ey - 10 * s, ex + k * 10 * s, ey + 10 * s], fill=(30, 10, 10, 255),
                       width=max(1, int(3 * s)))
        elif eyes == "glow":
            d.ellipse([ex - 36 * s, ey - 40 * s, ex + 36 * s, ey + 40 * s], fill=(0, 0, 0, 255))
            d.ellipse([ex - 18 * s, ey - 18 * s, ex + 18 * s, ey + 18 * s], fill=(255, 210, 60, 255))
    my = cy + 95 * s
    if mouth == "grin":
        d.chord([cx - 115 * s, my - 70 * s, cx + 115 * s, my + 60 * s], 0, 180, fill=(8, 0, 0, 255))
        for k in range(-5, 6):
            tx = cx + k * 19 * s
            d.polygon([(tx - 8 * s, my - 5 * s), (tx + 8 * s, my - 5 * s), (tx, my + 22 * s)],
                      fill=(235, 230, 200, 255))
            d.polygon([(tx - 6 * s, my + 52 * s), (tx + 6 * s, my + 52 * s), (tx, my + 32 * s)],
                      fill=(225, 220, 190, 255))
    elif mouth == "scream":
        d.ellipse([cx - 45 * s, my - 50 * s, cx + 45 * s, my + 75 * s], fill=(5, 0, 0, 255))
    elif mouth == "stitched":
        d.line([cx - 80 * s, my, cx + 80 * s, my], fill=(40, 10, 10, 255), width=max(1, int(6 * s)))
        for k in range(-7, 8):
            d.line([cx + k * 11 * s - 5 * s, my - 14 * s, cx + k * 11 * s + 5 * s, my + 14 * s],
                   fill=(40, 10, 10, 255), width=max(1, int(3 * s)))
    elif mouth == "teeth":
        d.rectangle([cx - 110 * s, my - 40 * s, cx + 110 * s, my + 60 * s], fill=(10, 0, 0, 255))
        for k in range(-6, 7):
            tx = cx + k * 17 * s
            d.rectangle([tx - 7 * s, my - 40 * s, tx + 7 * s, my - 5 * s], fill=(230, 225, 205, 255))
            d.rectangle([tx - 7 * s, my + 25 * s, tx + 7 * s, my + 60 * s], fill=(220, 215, 195, 255))
    elif mouth == "skull":
        d.polygon([(cx, cy + 20 * s), (cx - 18 * s, cy + 55 * s), (cx + 18 * s, cy + 55 * s)], fill=(5, 5, 5, 255))
        d.chord([cx - 85 * s, my - 30 * s, cx + 85 * s, my + 40 * s], 0, 180, fill=(5, 5, 5, 255))
        for k in range(-4, 5):
            d.line([cx + k * 18 * s, my + 5 * s, cx + k * 18 * s, my + 38 * s], fill=skin + (255,),
                   width=max(1, int(4 * s)))
    for _ in range(cracks):
        x, y = cx + rng.uniform(-0.4, 0.4) * fw, cy + rng.uniform(-0.45, 0.2) * fh
        pts = [(x, y)]
        for _ in range(6):
            x += rng.uniform(-25, 25) * s
            y += rng.uniform(5, 30) * s
            pts.append((x, y))
        d.line(pts, fill=(40, 30, 30, 255), width=max(1, int(3 * s)))
    if tilt:
        L = L.rotate(tilt, center=(cx, cy), resample=Image.BICUBIC)
    if upside:
        L = L.rotate(180, center=(cx, cy), resample=Image.BICUBIC)
    if blur:
        L = L.filter(ImageFilter.GaussianBlur(float(blur)))
    return L


def calavera(cx, cy, s):
    """An original Day of the Dead style skull, with glowing eyes."""
    L = face(cx, cy, s, mouth="skull", eyes="glow", skin=(236, 232, 220), blur=0.8)
    d = ImageDraw.Draw(L)
    for k, col in enumerate([(240, 140, 20), (200, 40, 120), (60, 170, 200)]):
        r = (22 + k * 6) * s
        d.arc([cx - r, cy - 150 * s - r, cx + r, cy - 150 * s + r], 0, 360, fill=col + (255,), width=max(1, int(5 * s)))
    for side in (-1, 1):
        for k in range(6):
            a = k * np.pi / 3
            px = cx + side * 62 * s + np.cos(a) * 52 * s
            py = cy - 45 * s + np.sin(a) * 58 * s
            d.ellipse([px - 6 * s, py - 6 * s, px + 6 * s, py + 6 * s], fill=(240, 150, 20, 255))
    return L


def silhouette(cx, base_y, s, arms=False):
    L = layer()
    d = ImageDraw.Draw(L)
    hh = 420 * s
    d.ellipse([cx - 28 * s, base_y - hh, cx + 28 * s, base_y - hh + 66 * s], fill=(0, 0, 0, 255))
    d.polygon([(cx - 34 * s, base_y - hh + 60 * s), (cx + 34 * s, base_y - hh + 60 * s),
               (cx + 55 * s, base_y), (cx - 55 * s, base_y)], fill=(0, 0, 0, 255))
    if arms:
        for side in (-1, 1):
            d.line([(cx + side * 30 * s, base_y - hh + 80 * s), (cx + side * 70 * s, base_y - hh + 230 * s),
                    (cx + side * 60 * s, base_y - hh + 330 * s)], fill=(0, 0, 0, 255), width=max(2, int(12 * s)))
    for side in (-1, 1):
        d.ellipse([cx + side * 12 * s - 4 * s, base_y - hh + 25 * s, cx + side * 12 * s + 4 * s,
                   base_y - hh + 33 * s], fill=(255, 255, 255, 255))
    return L.filter(ImageFilter.GaussianBlur(1.5))


def hand(x, y, s, flip=False, ang=0):
    L = layer()
    d = ImageDraw.Draw(L)
    col = (190, 195, 185, 255)
    d.rectangle([x - 26 * s, y, x + 26 * s, y + 400 * s], fill=col)
    d.ellipse([x - 40 * s, y - 45 * s, x + 40 * s, y + 35 * s], fill=col)
    for k, (dx, ln) in enumerate([(-30, 95), (-12, 120), (6, 125), (24, 105)]):
        fx = x + dx * s
        d.line([(fx, y - 20 * s), (fx + (k - 1.5) * 9 * s, y - ln * s), (fx + (k - 1.5) * 16 * s, y - (ln + 30) * s)],
               fill=col, width=max(2, int(13 * s)))
        d.ellipse([fx + (k - 1.5) * 16 * s - 5 * s, y - (ln + 36) * s, fx + (k - 1.5) * 16 * s + 5 * s,
                   y - (ln + 24) * s], fill=(60, 40, 40, 255))
    d.line([(x - 40 * s, y), (x - 75 * s, y - 50 * s)], fill=col, width=max(2, int(13 * s)))
    if ang:
        L = L.rotate(ang, center=(x, y), resample=Image.BICUBIC)
    if flip:
        L = L.transpose(Image.FLIP_LEFT_RIGHT)
    return L.filter(ImageFilter.GaussianBlur(1))


def eye(cx, cy, s, open_=1.0, pupil=1.0):
    L = layer()
    d = ImageDraw.Draw(L)
    ew, eh = 300 * s, 160 * s * open_
    d.ellipse([cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2], fill=(235, 225, 215, 255))
    for _k in range(10):
        a = rng.uniform(0, 2 * np.pi)
        d.line([(cx + np.cos(a) * ew * 0.48, cy + np.sin(a) * eh * 0.45),
                (cx + np.cos(a) * ew * 0.25, cy + np.sin(a) * eh * 0.25)], fill=(170, 30, 30, 255), width=2)
    r = 60 * s * min(1, open_ + 0.2)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(40, 70, 40, 255))
    pr = 30 * s * pupil
    d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=(0, 0, 0, 255))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse([cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2], fill=255)
    L.putalpha(Image.composite(L.getchannel("A"), Image.new("L", (W, H), 0), mask))
    return L.filter(ImageFilter.GaussianBlur(1.2))


def spider(cx, cy, s, phase):
    L = layer()
    d = ImageDraw.Draw(L)
    for side in (-1, 1):
        for k in range(4):
            a = (-0.9 + k * 0.6) + 0.25 * np.sin(phase * 3 + k)
            kx = cx + side * np.cos(a) * 120 * s
            ky = cy + np.sin(a) * 120 * s - 40 * s
            fx = cx + side * np.cos(a) * 240 * s
            fy = cy + np.sin(a) * 220 * s + 60 * s
            d.line([(cx, cy), (kx, ky), (fx, fy)], fill=(5, 3, 3, 255), width=max(2, int(10 * s)))
    d.ellipse([cx - 70 * s, cy - 55 * s, cx + 70 * s, cy + 75 * s], fill=(18, 12, 12, 255))
    d.ellipse([cx - 45 * s, cy - 95 * s, cx + 45 * s, cy - 25 * s], fill=(25, 15, 15, 255))
    for k in range(4):
        d.ellipse([cx - 30 * s + k * 18 * s, cy - 70 * s, cx - 22 * s + k * 18 * s, cy - 62 * s],
                  fill=(220, 30, 30, 255))
    return L.filter(ImageFilter.GaussianBlur(0.8))


def jump(t, t0, dur=0.9):
    """Face scale during the final jump: grows fast and stays huge."""
    p = np.clip((t - t0) / dur, 0, 1)
    return 0.45 + 0.8 * (1 - (1 - p) ** 3)


# ---------------------------------------------------------------- the 20 scares (visuals)
def v01(t):  # The Smile: static that opens into a giant smiling face
    if t < 1.2:
        return finish(static(0.55 + 0.2 * np.sin(t * 30)), g=0)
    f = blank(0.03)
    f = paste_layer(f, face(W / 2, H / 2 + 30, jump(t, 1.2), "grin"))
    return finish(glitch(shake(f, 8), 0.4))


def v02(t):  # The Scream
    f = blank(0.02)
    if t < 1.3:
        s = 0.25 + 0.05 * t
        f = paste_layer(f, face(W / 2, H / 2, s, "scream", pupils=None, blur=4))
        f *= 0.35
    else:
        f = paste_layer(f, face(W / 2, H / 2 + 40, jump(t, 1.3, 0.5), "scream", pupils=(255, 255, 255)))
        f = shake(f, 14)
    return finish(f)


def v03(t):  # Eyes in the dark
    f = blank(0.0)
    L = layer()
    d = ImageDraw.Draw(L)
    r2 = np.random.default_rng(3)
    n = int(min(40, t * 22))
    for k in range(n):
        x, y = r2.uniform(40, W - 40), r2.uniform(30, H - 30)
        sc = r2.uniform(0.4, 1.2)
        blink = 1 if (t * 3 + k) % 4 > 0.25 else 0.15
        for side in (-1, 1):
            d.ellipse([x + side * 14 * sc - 7 * sc, y - 4 * sc * blink, x + side * 14 * sc + 7 * sc,
                       y + 4 * sc * blink], fill=(255, 230, 120, 255))
    f = paste_layer(f, L.filter(ImageFilter.GaussianBlur(1.5)))
    if t > 2.0:
        f = paste_layer(f, face(W / 2, H / 2 + 20, jump(t, 2.0, 0.4), "grin", eyes="glow"))
        f = shake(f, 10)
    return finish(f)


def v04(t):  # The Hands
    f = blank(0.04)
    rise = np.clip(t / 1.8, 0, 1)
    for k, x in enumerate([120, 280, 430, 590, 740]):
        y = H + 40 - rise * (260 + 60 * np.sin(k * 2.1)) + 8 * np.sin(t * 9 + k)
        f = paste_layer(f, hand(x, y, 0.8, flip=k % 2 == 1, ang=(k - 2) * 8))
    if t > 2.0:
        sc = jump(t, 2.0, 0.35) * 1.2
        f = paste_layer(f, hand(W / 2, H / 2 - 40 + 130 * sc, sc))
        f = shake(f, 12)
    return finish(red(f, 0.15))


def v05(t):  # The approaching Shadow
    f = blank(0.12)
    steps = [0.25, 0.45, 0.8, 1.4]
    idx = min(int(t / 0.55), 3)
    flick = 0.2 if (t % 0.55) < 0.08 else 1.0
    f *= flick
    if t < 2.2:
        s = steps[idx]
        f = paste_layer(f, silhouette(W / 2 + (idx - 1.5) * 60, H - 10 + 200 * (s - 0.25), s, arms=idx >= 2))
    else:
        f = blank(0.0)
        f = paste_layer(f, face(W / 2, H / 2 + 40, jump(t, 2.2, 0.3), "scream", skin=(40, 40, 45),
                                pupils=(255, 255, 255)))
        f = shake(f, 16)
    return finish(f)


def v06(t):  # It's behind you
    f = blank(0.0)
    msg = TEXTS[6][LANG][1]
    n = int(np.clip(t / 1.6, 0, 1) * len(msg))
    if t < 2.2:
        f = paste_layer(f, text_layer(msg[:n], 60, (200, 20, 20), jitter=2 if t > 1.6 else 0))
    else:
        f = paste_layer(f, face(W / 2, H / 2 + 30, jump(t, 2.2, 0.3), "grin", tilt=-12))
        f = glitch(shake(f, 12), 0.6)
    return finish(f)


def v07(t):  # Glitch Face
    f = blank(0.03)
    s = 0.9 + 0.5 * np.clip((t - 1.0) / 1.5, 0, 1)
    f = paste_layer(f, face(W / 2, H / 2 + 20, s, "grin", eyes="wide", cracks=4))
    k = 0.2 + 1.2 * np.clip((t - 0.5) / 2.0, 0, 1)
    f = glitch(f, k)
    if int(t * 12) % 5 == 0:
        f = 1 - f * 0.8
    return finish(f)


def v08(t):  # The Crack
    f = blank(0.06)
    if t < 2.0:
        L = layer()
        d = ImageDraw.Draw(L)
        r2 = np.random.default_rng(8)
        prog = np.clip(t / 1.8, 0, 1)
        for _ in range(int(14 * prog) + 1):
            x, y = W / 2, H / 2
            pts = [(x, y)]
            a = r2.uniform(0, 2 * np.pi)
            for _ in range(int(10 * prog) + 1):
                a += r2.uniform(-0.5, 0.5)
                x += np.cos(a) * 40
                y += np.sin(a) * 40
                pts.append((x, y))
            d.line(pts, fill=(230, 230, 240, 255), width=3)
        f = paste_layer(f, L)
        f = paste_layer(f, eye(W / 2, H / 2, 0.25 * prog, open_=prog))
    else:
        f = paste_layer(f, eye(W / 2, H / 2, jump(t, 2.0, 0.3) * 1.4, open_=1.0, pupil=0.4))
        f = shake(f, 12)
    return finish(f)


def v09(t):  # Dripping
    f = blank(0.08)
    L = layer()
    d = ImageDraw.Draw(L)
    r2 = np.random.default_rng(9)
    for _k in range(26):
        x = r2.uniform(0, W)
        speed = r2.uniform(120, 300)
        ln = min(H, t * speed)
        w = r2.uniform(6, 18)
        d.rectangle([x - w / 2, 0, x + w / 2, ln], fill=(120, 0, 5, 255))
        d.ellipse([x - w, ln - w, x + w, ln + w], fill=(140, 0, 8, 255))
    f = paste_layer(f, L.filter(ImageFilter.GaussianBlur(1.5)))
    if t > 2.1:
        f = paste_layer(f, face(W / 2, H / 2 + 40, jump(t, 2.1, 0.35), "teeth", eyes="hollow"))
        f = shake(f, 12)
    return finish(f)


def v10(t):  # The Spider
    f = blank(0.0) + VIGNETTE * np.array([0.32, 0.12, 0.1], dtype=np.float32)
    if t < 2.2:
        p = np.clip(t / 2.2, 0, 1)
        for k, (sx, sy) in enumerate([(-150, -150), (W + 150, -120), (-150, H + 150), (W + 150, H + 120)]):
            cx = sx + (W / 2 - sx) * p * 0.55
            cy = sy + (H / 2 - sy) * p * 0.55
            f = paste_layer(f, spider(cx, cy, 0.4, t * 4 + k))
    else:
        f = paste_layer(f, spider(W / 2, H / 2 + 40, jump(t, 2.2, 0.3) * 1.3, t * 8))
        f = shake(f, 14)
    return finish(f)


def v11(t):  # Dead Channel (TV static)
    f = static(0.75)
    if 0.8 < t < 2.3:
        a = 0.25 + 0.4 * ((t - 0.8) / 1.5)
        sil = paste_layer(blank(0.0), silhouette(W / 2, H + 20, 1.0))
        f = f * (1 - a) + sil * a + f * a * 0.3
    if t >= 2.3:
        f = paste_layer(static(0.3), face(W / 2, H / 2 + 40, jump(t, 2.3, 0.3), "scream"))
        f = glitch(shake(f, 10), 0.7)
    return finish(f, g=0)


def v12(t):  # The Eye
    f = blank(0.02)
    op = np.clip((t - 0.3) / 1.6, 0, 1)
    pup = 1.0 - 0.7 * np.clip((t - 2.0) / 0.3, 0, 1)
    s = 1.0 + 1.3 * np.clip((t - 2.0) / 0.35, 0, 1)
    f = paste_layer(f, eye(W / 2, H / 2, s * 1.3, open_=max(0.05, op), pupil=pup))
    if t > 2.0:
        f = shake(f, 10)
    return finish(red(f, 0.1))


def v13(t):  # Sewn Mouth
    f = blank(0.04)
    s = 0.5 + 0.4 * np.clip(t / 2.0, 0, 1)
    mouth = "stitched" if t < 2.1 else "scream"
    sc = s if t < 2.1 else jump(t, 2.1, 0.3)
    f = paste_layer(f, face(W / 2, H / 2 + 30, sc, mouth, eyes="sewn" if t < 2.1 else "hollow",
                            skin=(205, 200, 190)))
    if t > 2.1:
        f = shake(f, 14)
    return finish(f)


def v14(t):  # On the Ceiling (upside-down face)
    f = blank(0.06)
    y = -200 + 330 * np.clip(t / 2.0, 0, 1) ** 2
    if t < 2.1:
        f = paste_layer(f, face(W / 2 + 40 * np.sin(t * 5), y, 0.7, "grin", upside=True))
    else:
        f = paste_layer(f, face(W / 2, H / 2, jump(t, 2.1, 0.3), "grin", upside=True))
        f = shake(f, 12)
    return finish(f)


def v15(t):  # A Thousand Smiles
    f = blank(0.02)
    r2 = np.random.default_rng(15)
    n = int(min(60, (t ** 2) * 9))
    for _k in range(n):
        x, y = r2.uniform(0, W), r2.uniform(0, H)
        sc = r2.uniform(0.12, 0.3)
        f = paste_layer(f, face(x, y, sc, "grin", blur=0.5, pupils=None))
    if t > 2.4:
        f = paste_layer(f * 0.4, face(W / 2, H / 2 + 30, jump(t, 2.4, 0.3), "grin"))
        f = shake(f, 10)
    return finish(f)


def v16(t):  # The Skull (Day of the Dead)
    f = blank(0.0)
    L = layer()
    d = ImageDraw.Draw(L)
    for k in range(9):
        x = 60 + k * 92
        fl = 0.7 + 0.3 * np.sin(t * 13 + k * 1.7)
        d.ellipse([x - 9, H - 120 - 26 * fl, x + 9, H - 92], fill=(255, 190, 70, int(220 * fl)))
        d.rectangle([x - 8, H - 92, x + 8, H - 20], fill=(235, 225, 200, 255))
    f = paste_layer(f, L.filter(ImageFilter.GaussianBlur(2)))
    s = 0.35 + 0.25 * np.clip(t / 2.0, 0, 1) if t < 2.2 else jump(t, 2.2, 0.3)
    f = paste_layer(f, calavera(W / 2, H / 2 - 20 + (0 if t < 2.2 else 40), s))
    if t > 2.2:
        f = shake(f, 12)
    return finish(f)


def v17(t):  # The Bite
    f = blank(0.03)
    if t < 1.5:
        return finish(paste_layer(f, text_layer("...", 80, (120, 120, 120))))
    gap = H / 2 * (1 - np.clip((t - 1.5) / 0.6, 0, 1) ** 2) if t < 2.7 else H / 2 * 0.0
    L = layer()
    d = ImageDraw.Draw(L)
    d.rectangle([0, 0, W, H / 2 - gap], fill=(70, 0, 0, 255))
    d.rectangle([0, H / 2 + gap, W, H], fill=(70, 0, 0, 255))
    for k in range(14):
        x = k * (W / 13)
        d.polygon([(x - 30, H / 2 - gap), (x + 30, H / 2 - gap), (x, H / 2 - gap + 70)], fill=(235, 230, 205, 255))
        d.polygon([(x - 30 + 30, H / 2 + gap), (x + 30 + 30, H / 2 + gap), (x + 30, H / 2 + gap - 70)],
                  fill=(225, 220, 195, 255))
    f = paste_layer(f, L)
    if gap < 20:
        f = shake(f, 16)
    return finish(f)


def v18(t):  # I see you
    f = blank(0.0)
    if t < 2.0:
        words = TEXTS[18][LANG][1]
        w = words[min(2, int(t / 0.6))]
        f = paste_layer(f, text_layer(w, 70, (235, 235, 235), jitter=3))
        f = glitch(f, 0.2)
    else:
        f = paste_layer(f, face(W / 2, H / 2 + 30, jump(t, 2.0, 0.3), "grin", eyes="wide"))
        f = glitch(shake(f, 12), 0.5)
    return finish(f)


def v19(t):  # Flatline
    f = blank(0.0)
    L = layer()
    d = ImageDraw.Draw(L)
    pts = []
    for x in range(0, W, 3):
        tt = x / W * 3 - (t * 1.2)
        ph = tt % 1.0
        y = H / 2
        if t < 1.8 and 0.45 < ph < 0.55:
            y -= 140 * np.sin((ph - 0.45) / 0.1 * np.pi) * (1 if ph < 0.5 else -0.5)
        pts.append((x, y))
    d.line(pts, fill=(40, 255, 120, 255), width=4)
    f = paste_layer(f, L.filter(ImageFilter.GaussianBlur(1)))
    if t > 2.4:
        f = paste_layer(f * 0.3, face(W / 2, H / 2 + 30, jump(t, 2.4, 0.3), "scream", eyes="hollow",
                                      skin=(170, 230, 190)))
        f = shake(f, 12)
    return finish(f)


def v20(t):  # The Flashlight
    f = blank(0.0)
    scene = paste_layer(blank(0.35), face(W * 0.72, H * 0.55, 0.55, "grin", eyes="hollow"))
    lx = W * 0.2 + (W * 0.52) * np.clip(t / 2.0, 0, 1) + 30 * np.sin(t * 7)
    ly = H * 0.5 + 40 * np.sin(t * 3)
    mask = np.clip(1 - np.sqrt((_xx - lx) ** 2 + (_yy - ly) ** 2) / 120, 0, 1)[..., None]
    f = scene * mask
    if t > 2.2:
        f = paste_layer(blank(0.02), face(W / 2, H / 2 + 30, jump(t, 2.2, 0.3), "grin", eyes="hollow"))
        f = shake(f, 14)
    return finish(f, vig=False)


# ---------------------------------------------------------------- sounds
def tt(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, a=0.01, r=0.2):
    e = np.ones(n)
    ai, ri = int(a * SR), int(r * SR)
    if ai:
        e[:ai] = np.linspace(0, 1, ai)
    if ri:
        e[-ri:] *= np.linspace(1, 0, ri)
    return e


def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return signal.lfilter(b, a, x)


def lp(x, f, order=2):
    b, a = signal.butter(order, f / (SR / 2))
    return signal.lfilter(b, a, x)


def noise(sec):
    return rng.normal(0, 1, int(sec * SR))


def saw(freq, sec):
    t = tt(sec)
    ph = np.cumsum(np.broadcast_to(freq, t.shape) / SR)
    return 2 * (ph % 1) - 1


def drone(sec, base=55):
    t = tt(sec)
    return sum(np.sin(2 * np.pi * base * m * t + 0.3 * np.sin(2 * np.pi * 0.2 * t * m)) / m
               for m in (1, 1.01, 1.5, 2.02, 3.0)) * 0.3


def screech(sec, f0=600, f1=2400):
    """Synthetic human scream + stabbing violins (instead of the old sawtooth 'beep')."""
    yell = ha.scream(sec, f_peak=float(np.clip(f1 * 0.38, 520, 1000)), f_start=float(np.clip(f0 * 0.6, 250, 600)),
                     vowel="a" if f1 < 2000 else "i")
    stab = ha.strings_stab(sec, base=float(np.clip(f1 * 0.8, 1200, 2600)))
    return 0.85 * yell + 0.55 * stab


def laugh(sec, pitch=230, rate=6.0, high=False):
    """Synthetic laughter: formant 'ha' bursts with a falling pitch (original, not human)."""
    n = int(sec * SR)
    out = np.zeros(n)
    t0 = 0.0
    k = 0
    while t0 < sec - 0.12:
        d = 0.11 + 0.04 * rng.random()
        f = pitch * (1.0 - 0.25 * k / (sec * rate)) * (1.8 if high else 1)
        burst = saw(np.full(int(d * SR), f) * (1 + 0.05 * np.sin(np.arange(int(d * SR)) / SR * 40)), d)
        burst = 0.7 * bp(burst, 650 * (1.3 if high else 1), 1300 * (1.3 if high else 1)) + \
            0.5 * bp(burst, 2200, 3200) + 0.15 * bp(noise(d), 1500, 6000)
        burst *= np.hanning(len(burst)) ** 0.6
        i = int(t0 * SR)
        out[i:i + len(burst)] += burst[: n - i]
        t0 += 1 / rate + 0.03 * rng.random()
        k += 1
    return np.tanh(1.8 * out)


def heartbeat(sec, bpm=80):
    n = int(sec * SR)
    out = np.zeros(n)
    t = tt(0.18)
    thump = np.sin(2 * np.pi * 52 * t) * np.exp(-t * 28)
    period = 60 / bpm
    x = 0.0
    while x < sec - 0.4:
        for off, g in ((0, 1.0), (0.22, 0.7)):
            i = int((x + off) * SR)
            out[i:i + len(thump)] += g * thump[: n - i]
        x += period
    return out


def whisper(sec):
    x = bp(noise(sec), 1800, 7000)
    t = tt(sec)
    am = np.clip(np.sin(2 * np.pi * 3.3 * t) * np.sin(2 * np.pi * 0.9 * t + 1), 0, 1)
    return x * am * 0.5


class Hit(np.ndarray):
    """Marks a scare hit: sound() adds a reversed swell in front of it, rising up to it."""


def impact(sec=1.4):
    return ha.sub_boom(sec).view(Hit)


def clicks(sec, density=40, f=4000):
    n = int(sec * SR)
    out = np.zeros(n)
    for _ in range(int(sec * density)):
        i = rng.integers(0, n - 200)
        out[i:i + 200] += bp(noise(200 / SR), f * 0.5, min(f * 1.5, SR / 2 - 100)) * np.exp(-np.arange(200) / 30)
    return out


def creak(sec):
    t = tt(sec)
    f = 30 + 25 * np.sin(2 * np.pi * 0.7 * t) + 10 * rng.random(len(t))
    x = saw(f, sec)
    return bp(x, 300, 2500) * 0.8


def bell(sec, f=220):
    t = tt(sec)
    return sum(np.sin(2 * np.pi * f * r * t) * np.exp(-t * (1.2 + r)) / (1 + i)
               for i, r in enumerate((1, 2.76, 5.4, 8.93)))


def beep(sec, f=1000):
    return np.sin(2 * np.pi * f * tt(sec))


JUMPS = []


def at(total, sec, x):
    """Places sound x at second `sec` of a track `total` seconds long."""
    if isinstance(x, Hit):
        JUMPS.append(sec)
    x = np.asarray(x)
    out = np.zeros(int(total * SR))
    i = int(sec * SR)
    out[i:i + len(x)] += x[: len(out) - i]
    return out


DUR = 3.6


def sound(k):
    """Final mix of scare k: recipe + reversed swell before each hit + reverb and stereo."""
    JUMPS.clear()
    s = np.asarray(_recipe(k), dtype=np.float64)
    for j in sorted(set(JUMPS))[:1]:
        if j > 0.5:
            sw = ha.reverse_swell(min(0.9, j))
            end = int(j * SR)
            s[end - len(sw):end] += sw * 0.5 * np.max(np.abs(s))
    return ha.master(s, t60=2.2, wet=0.28)


def _recipe(k):
    T = DUR
    if k == 1:
        s = at(T, 0, lp(noise(1.2), 6000) * 0.25) + at(T, 1.2, impact()) + at(T, 1.25, laugh(2.3))
    elif k == 2:
        s = at(T, 0, drone(1.3, 45) * 0.4) + at(T, 1.3, screech(2.2, 700, 2600)) + at(T, 1.3, impact())
    elif k == 3:
        s = at(T, 0, whisper(2.0)) + at(T, 0, drone(2.0, 40) * 0.3) + at(T, 2.0, impact()) + at(T, 2.0, laugh(1.5, 180))
    elif k == 4:
        s = at(T, 0, creak(2.0) * 0.6 + lp(noise(2.0), 900) * 0.3) + at(T, 2.0, impact()) + at(T, 2.0, screech(1.5, 300, 900))
    elif k == 5:
        s = at(T, 0, heartbeat(2.2, 95)) + at(T, 2.2, impact()) + at(T, 2.2, screech(1.4, 900, 3000))
    elif k == 6:
        s = at(T, 0, whisper(2.2) * 1.3) + at(T, 2.2, impact()) + at(T, 2.25, laugh(1.3, 260))
    elif k == 7:
        b = saw(np.where((tt(T) * 8) % 1 < 0.5, 110, 165), T)
        s = np.tanh(3 * b) * 0.25 + laugh(T, 150, 7.5) * 0.9 + clicks(T, 25, 6000) * 0.4
    elif k == 8:
        s = at(T, 0, clicks(2.0, 30, 7000)) + at(T, 0, drone(2.0, 60) * 0.25) + at(T, 2.0, impact()) + at(T, 2.0, screech(1.3, 1200, 1600))
    elif k == 9:
        drips = sum(at(2.2, x, np.sin(2 * np.pi * 1400 * tt(0.05)) * np.exp(-tt(0.05) * 90)) for x in np.arange(0.1, 2.1, 0.33))
        s = at(T, 0, drips + drone(2.2, 36) * 0.4) + at(T, 2.1, impact()) + at(T, 2.1, laugh(1.5, 120))
    elif k == 10:
        s = at(T, 0, clicks(2.2, 160, 3500)) + at(T, 2.2, impact()) + at(T, 2.2, screech(1.3, 1500, 4000))
    elif k == 11:
        s = at(T, 0, bp(noise(2.3), 300, 8000) * 0.35) + at(T, 0.8, whisper(1.5)) + at(T, 2.3, impact()) + at(T, 2.3, screech(1.2))
    elif k == 12:
        s = at(T, 0, drone(2.0, 32) * 0.5 + creak(2.0) * 0.3) + at(T, 2.0, impact()) + at(T, 2.0, screech(1.5, 200, 700))
    elif k == 13:
        hum = lp(saw(np.full(int(2.1 * SR), 140.0), 2.1), 500) * np.clip(np.sin(2 * np.pi * 1.5 * tt(2.1)), 0.2, 1)
        s = at(T, 0, hum * 0.6) + at(T, 2.1, bp(noise(0.3), 1000, 8000)) + at(T, 2.1, screech(1.4, 500, 1800)) + at(T, 2.1, impact())
    elif k == 14:
        s = at(T, 0, creak(2.1)) + at(T, 0, clicks(2.1, 20, 2500)) + at(T, 2.1, impact()) + at(T, 2.15, laugh(1.4, 300))
    elif k == 15:
        s = at(T, 0.2, laugh(2.2, 320, 9, high=True) * 0.7) + at(T, 0.6, laugh(1.8, 280, 7, high=True) * 0.5) + at(T, 2.4, impact()) + at(T, 2.4, laugh(1.2, 200))
    elif k == 16:
        s = at(T, 0, bell(2.2, 196) * 0.6) + at(T, 0.9, bell(1.4, 146) * 0.5) + at(T, 2.2, impact()) + at(T, 2.2, laugh(1.4, 140))
    elif k == 17:
        chomp = impact(0.4) + bp(noise(0.4), 2000, 6000) * np.exp(-tt(0.4) * 20)
        s = at(T, 0, drone(1.5, 50) * 0.3) + at(T, 1.5, whisper(0.6)) + at(T, 2.1, chomp) + at(T, 2.35, chomp) + at(T, 2.1, screech(1.3, 400, 1200))
    elif k == 18:
        s = at(T, 0, whisper(2.0) * 1.2) + sum(at(T, x, beep(0.05, 90) * 0.6) for x in (0, 0.6, 1.2)) + at(T, 2.0, impact()) + at(T, 2.05, laugh(1.5, 240))
    elif k == 19:
        beeps = sum(at(T, x, beep(0.12)) for x in np.arange(0.0, 1.8, 0.55))
        s = beeps * 0.4 + at(T, 1.8, beep(0.6) * 0.4) + at(T, 2.4, impact()) + at(T, 2.4, screech(1.1, 800, 2800))
    elif k == 20:
        steps = sum(at(2.2, x, lp(noise(0.12), 400) * np.exp(-tt(0.12) * 30)) for x in np.arange(0, 2.2, 0.45))
        s = at(T, 0, steps * 1.5 + heartbeat(2.2, 110) * 0.6) + at(T, 2.2, impact()) + at(T, 2.2, laugh(1.3, 210))
    return s


# Scares with text: one version per language (picked with --lang)
LANG = "es"
TEXTS = {
    6: {"es": ("esta_detras_de_ti", "ESTÁ DETRÁS DE TI"), "en": ("its_behind_you", "IT'S BEHIND YOU")},
    18: {"es": ("te_estoy_viendo", ["TE", "TE ESTOY", "TE ESTOY VIENDO"]), "en": ("i_see_you", ["I", "I SEE", "I SEE YOU"])},
}

NAMES = {
    1: "the_smile", 2: "the_scream", 3: "eyes_in_the_dark", 4: "the_hands", 5: "the_shadow",
    6: "esta_detras_de_ti", 7: "glitch_face", 8: "the_crack", 9: "dripping", 10: "the_spider",
    11: "dead_channel", 12: "the_eye", 13: "sewn_mouth", 14: "on_the_ceiling", 15: "thousand_smiles",
    16: "the_skull", 17: "the_bite", 18: "te_estoy_viendo", 19: "flatline", 20: "the_flashlight",
}
VISUALS = {i: globals()[f"v{i:02d}"] for i in NAMES}


def write_wav(path, x):
    ha.write_wav(path, x, SR)


def write_mp4(path, func):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    thumb = None
    for i in range(int(DUR * FPS)):
        frame = func(i / FPS)
        if i == int(DUR * FPS) - 10:
            thumb = frame
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()
    return thumb


def catalog(lang, path):
    """Contact sheet with one frame of each scare, read from the generated videos."""
    import cv2

    files = []
    for i in NAMES:
        stem = f"{i:02d}_{TEXTS[i][lang][0]}.{lang}" if i in TEXTS else f"{i:02d}_{NAMES[i]}"
        files.append(stem)
    sheet = Image.new("RGB", (5 * 284, 4 * 180), (10, 10, 10))
    d = ImageDraw.Draw(sheet)
    for k, stem in enumerate(files):
        cap = cv2.VideoCapture(os.path.join(OUT, stem + ".mp4"))
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(DUR * FPS) - 10)
        ok, fr = cap.read()
        cap.release()
        if not ok:
            continue
        im = Image.fromarray(fr[..., ::-1]).resize((284, 160))
        x, y = (k % 5) * 284, (k // 5) * 180
        sheet.paste(im, (x, y))
        d.text((x + 4, y + 162), stem.split(".")[0], fill=(240, 160, 40), font=font(13))
    sheet.save(path, quality=85)


def live_tracks():
    """Soundtracks of the LIVE scares (the ones using the victim's real face)."""
    os.makedirs(os.path.join(OUT, "live"), exist_ok=True)
    for e in possessions.EFFECTS:
        print(f"  building live sound {e} ...")
        ha.write_wav(os.path.join(OUT, "live", e + ".wav"), ha.live_track(e, possessions.PRE, possessions.POST))


def jumps_file():
    """media/_jumps.json: the second each scare jumps (to measure the victim's jump at that moment)."""
    import json

    out = {}
    for i in NAMES:
        JUMPS.clear()
        _recipe(i)
        j = round(min(JUMPS), 2) if JUMPS else 0.0
        stems = [f"{i:02d}_{n}.{lang}" for lang, (n, _) in TEXTS[i].items()] if i in TEXTS else [f"{i:02d}_{NAMES[i]}"]
        for stem in stems:
            out[stem] = j
    with open(os.path.join(OUT, "_jumps.json"), "w") as f:
        json.dump(out, f, indent=1)


def sounds_only():
    """Rebuilds only the audio of the 20 scares (fast, videos untouched)."""
    for i in NAMES:
        stems = [f"{i:02d}_{n}.{lang}" for lang, (n, _) in TEXTS[i].items()] if i in TEXTS else [f"{i:02d}_{NAMES[i]}"]
        for stem in stems:
            write_wav(os.path.join(OUT, stem + ".wav"), sound(i))
    live_tracks()
    jumps_file()


def main(argv=None):
    global LANG
    argv = sys.argv[1:] if argv is None else argv
    os.makedirs(OUT, exist_ok=True)
    if argv == ["--sounds"]:
        sounds_only()
        print("Done: sounds rebuilt in", OUT)
        return
    wanted = [int(a) for a in argv] or list(NAMES)
    for i in wanted:
        if i in TEXTS:
            for lang, (name, _) in TEXTS[i].items():
                LANG = lang
                stem = f"{i:02d}_{name}.{lang}"
                print(f"  building scare {stem} ...")
                write_mp4(os.path.join(OUT, stem + ".mp4"), VISUALS[i])
                write_wav(os.path.join(OUT, stem + ".wav"), sound(i))
            continue
        stem = f"{i:02d}_{NAMES[i]}"
        print(f"  building scare {stem} ...")
        write_mp4(os.path.join(OUT, stem + ".mp4"), VISUALS[i])
        write_wav(os.path.join(OUT, stem + ".wav"), sound(i))
    live_tracks()
    jumps_file()
    catalog("es", os.path.join(OUT, "_catalog_es.jpg"))
    catalog("en", os.path.join(OUT, "_catalog_en.jpg"))
    # translucent ghost for "mirror mode" (appears behind the victim)
    g = face(W / 2, H / 2, 1.2, "scream", eyes="hollow", skin=(200, 210, 215), blur=3)
    g = g.crop(g.getbbox())
    a = g.getchannel("A").point(lambda v: int(v * 0.8))
    g.putalpha(a)
    g.save(os.path.join(OUT, "_mirror_ghost.png"))
    print("Done. Scares in", OUT)

