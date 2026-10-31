"""
The possessions, drawn with OpenCV on the person's real image: black eyes, no face, melting, a grin that
isn't theirs, a girl behind them, their double… and the hit (zoom, shake, red).
Nothing is recorded or sent anywhere: it all happens in the computer's memory.
"""
import math
import random

import cv2
import numpy as np

from domain.rules.possessions import POST, PRE
from domain.services.possession_service import PossessionService


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ pinceles
def soft_ellipse(shape, center, axes, angle=0.0, blur=0.35):
    """0..1 elliptical mask with a feathered edge."""
    m = np.zeros(shape[:2], np.float32)
    ax = (max(1, int(axes[0])), max(1, int(axes[1])))
    cv2.ellipse(m, (int(center[0]), int(center[1])), ax, angle, 0, 360, 1.0, -1, cv2.LINE_AA)
    k = int(max(ax) * blur) * 2 + 1
    if k > 2:
        m = cv2.GaussianBlur(m, (k, k), 0)
    return m


def blend(img, color_img, mask):
    m = mask[..., None]
    return (img.astype(np.float32) * (1 - m) + np.asarray(color_img, np.float32) * m).astype(np.uint8)


_CACHE = {}


def _vignette_and_grain(shape):
    key = shape[:2]
    if key not in _CACHE:
        H, W = key
        yy, xx = np.ogrid[:H, :W]
        r = (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.2
        g = np.random.default_rng(5)
        _CACHE[key] = (r.astype(np.float32), [g.normal(0, 1, (H, W, 1)).astype(np.float32) for _ in range(4)])
    return _CACHE[key]


def grade(img, k, t, tint=(0.9, 1.05, 0.85)):
    """Horror-movie look: less colour, a cold/greenish tone, vignette, grain and flickering light."""
    f = img.astype(np.float32)
    gray = f.mean(axis=2, keepdims=True)
    f = f * (1 - 0.65 * k) + gray * (0.65 * k)
    r, grains = _vignette_and_grain(img.shape)
    vig = np.clip(1 - 0.75 * k * r, 0.05, 1)[..., None]
    flicker = 1 - 0.25 * k * (random.random() < 0.08)
    f *= np.array(tint, np.float32) ** k * vig * (flicker * (1 - 0.35 * k))
    f += grains[random.randrange(4)] * (9 * k)
    return np.clip(f, 0, 255).astype(np.uint8)


def black_eyes(img, face, amount, glint=True, veins=True):
    if amount <= 0:
        return img
    d = face.d
    m = np.zeros(img.shape[:2], np.float32)
    sock = np.zeros(img.shape[:2], np.float32)
    for e in face.eyes:
        m = np.maximum(m, soft_ellipse(img.shape, e, (d * 0.26 * (0.35 + 0.65 * amount), d * 0.17 * (0.5 + 0.5 * amount)),
                                       face.angle, 0.25))
        sock = np.maximum(sock, soft_ellipse(img.shape, e, (d * 0.48, d * 0.36), face.angle, 0.8))
    out = blend(img, (0, 0, 0), sock * 0.55 * amount)
    out = blend(out, (2, 0, 4), np.clip(m * 1.3 * amount, 0, 1))
    if veins and amount > 0.5:
        r = random.Random(int(d))
        for e in face.eyes:
            for _ in range(7):
                a = r.uniform(0, 2 * math.pi)
                length = d * r.uniform(0.35, 0.75)
                p0 = e + np.array([math.cos(a), math.sin(a)]) * d * 0.2
                p1 = p0 + np.array([math.cos(a + r.uniform(-.4, .4)), math.sin(a + r.uniform(-.4, .4))]) * length * (amount - 0.5) * 2
                cv2.line(out, tuple(map(int, p0)), tuple(map(int, p1)), (20, 10, 40), max(1, int(d / 40)), cv2.LINE_AA)
    if glint and amount > 0.85:
        for e in face.eyes:
            cv2.circle(out, (int(e[0] + d * 0.05), int(e[1] - d * 0.04)), max(1, int(d * 0.03)), (40, 40, 220), -1, cv2.LINE_AA)
    return out


def gaping_mouth(img, face, amount, teeth=True):
    if amount <= 0:
        return img
    d = face.d
    c = face.mouth + face.down * d * 0.25 * amount
    axes = (d * (0.32 + 0.3 * amount), d * (0.1 + 1.0 * amount))
    out = blend(img, (0, 0, 0), soft_ellipse(img.shape, c, (axes[0] * 1.35, axes[1] * 1.2), face.angle, 0.9) * 0.6)
    out = blend(out, (8, 0, 10), soft_ellipse(img.shape, c, axes, face.angle, 0.15))
    if teeth and amount > 0.3:
        n = 7
        for k in range(n):
            x = c[0] - axes[0] * 0.8 + 1.6 * axes[0] * (k + 0.5) / n
            top = c[1] - axes[1] * 0.92 * math.sqrt(max(0, 1 - ((x - c[0]) / axes[0]) ** 2))
            bot = c[1] + axes[1] * 0.92 * math.sqrt(max(0, 1 - ((x - c[0]) / axes[0]) ** 2))
            w, h = axes[0] / n * 0.8, d * 0.28 * amount
            for y0, sgn in ((top, 1), (bot, -1)):
                pts = np.array([[x - w, y0], [x + w, y0], [x, y0 + sgn * h]], np.int32)
                cv2.fillConvexPoly(out, pts, (190, 205, 210), cv2.LINE_AA)
    return out


def faceless(img, face, amount):
    if amount <= 0:
        return img
    d = face.d
    k = int(d * 1.1) * 2 + 1
    smooth = cv2.GaussianBlur(img, (k, k), 0)
    c = face.center
    skin = img[int(max(0, c[1] - d * .3)):int(c[1] + d * .3), int(max(0, c[0] - d * .4)):int(c[0] + d * .4)]
    col = skin.reshape(-1, 3).mean(axis=0) if skin.size else np.array([150, 160, 190])
    smooth = (smooth.astype(np.float32) * 0.5 + col * 0.5).astype(np.uint8)
    m = soft_ellipse(img.shape, c, (d * 1.12, d * 1.55), face.angle, 0.45)
    return blend(img, smooth, m * min(1, amount * 1.15))


def melt(img, face, amount, t):
    if amount <= 0:
        return img
    H, W = img.shape[:2]
    d = face.d
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, top = face.center[0], face.mid[1] - d * 1.2
    col = np.exp(-((xx - cx) / (d * 1.5)) ** 2)
    ramp = np.clip((yy - top) / (d * 3.5), 0, 1) ** 1.3
    drip = 1 + 0.5 * np.sin(xx / (d * 0.18) + 1.7) * np.sin(xx / (d * 0.07))
    dy = amount * d * 2.4 * col * ramp * drip
    dx = amount * d * 0.12 * np.sin(yy / (d * 0.25) + t * 5) * col
    out = cv2.remap(img, (xx - dx).astype(np.float32), (yy - dy).astype(np.float32), cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REFLECT)
    sick = out.astype(np.float32) * np.array([0.75, 1.05, 0.7], np.float32)
    m = np.clip(col * ramp * amount * 1.4, 0, 1)
    return blend(out, np.clip(sick, 0, 255), m * 0.7)


def grin(img, face, amount):
    if amount <= 0:
        return img
    d = face.d
    c = face.mouth
    half = d * (0.3 + 0.95 * amount)
    curve = d * (0.15 + 0.65 * amount)
    thick = d * (0.06 + 0.3 * amount)
    xs = np.linspace(-1, 1, 40)
    rot = np.array([[math.cos(math.radians(face.angle)), -math.sin(math.radians(face.angle))],
                    [math.sin(math.radians(face.angle)), math.cos(math.radians(face.angle))]])
    upper = [c + rot @ np.array([x * half, -curve * x * x + thick * 0.2 * (1 - x * x)]) for x in xs]
    lower = [c + rot @ np.array([x * half, -curve * x * x + thick * (1 - x * x)]) for x in xs[::-1]]
    poly = np.array(upper + lower, np.int32)
    m = np.zeros(img.shape[:2], np.float32)
    cv2.fillPoly(m, [poly], 1.0, cv2.LINE_AA)
    shadow = cv2.GaussianBlur(m, (0, 0), max(1, d * 0.12))
    out = blend(img, (0, 0, 0), shadow * 0.55 * amount)
    out = blend(out, (10, 0, 12), cv2.GaussianBlur(m, (0, 0), 1.2) * min(1, amount * 1.4))
    if amount > 0.35:   # dientes
        for k in range(16):
            x = -0.9 + 1.8 * (k + 0.5) / 16
            y_top = -curve * x * x + thick * 0.2 * (1 - x * x)
            y_bot = -curve * x * x + thick * (1 - x * x)
            w = half * 1.8 / 16 * 0.45
            for y0, sgn in ((y_top, 1), (y_bot, -1)):
                h = (y_bot - y_top) * 0.45
                pts = [c + rot @ np.array([x * half - w, y0]), c + rot @ np.array([x * half + w, y0]),
                       c + rot @ np.array([x * half, y0 + sgn * h])]
                cv2.fillConvexPoly(out, np.array(pts, np.int32), (175, 195, 200), cv2.LINE_AA)
    return out


_GHOST = {}


def ghost_face(size, mouth=0.15):
    """A pale girl with black hair, hand-drawn in code. Returns BGRA."""
    key = (size, round(mouth, 1))
    if key in _GHOST:
        return _GHOST[key]
    S = size
    g = np.zeros((int(S * 2.1), S, 4), np.uint8)
    cx = S // 2
    # hair: a black mass + falling strands
    cv2.ellipse(g, (cx, int(S * 0.55)), (int(S * 0.5), int(S * 0.55)), 0, 0, 360, (12, 8, 10, 255), -1, cv2.LINE_AA)
    r = random.Random(7)
    for _ in range(60):
        x = cx + r.uniform(-0.48, 0.48) * S
        cv2.line(g, (int(x), int(S * 0.5)), (int(x + r.uniform(-.05, .05) * S), int(S * r.uniform(1.4, 2.05))),
                 (10, 6, 8, 255), max(2, S // 28), cv2.LINE_AA)
    # pale, slightly bluish face
    cv2.ellipse(g, (cx, int(S * 0.68)), (int(S * 0.27), int(S * 0.36)), 0, 0, 360, (228, 222, 214, 255), -1, cv2.LINE_AA)
    cv2.ellipse(g, (cx, int(S * 0.44)), (int(S * 0.32), int(S * 0.14)), 0, 180, 360, (14, 9, 11, 255), -1, cv2.LINE_AA)  # flequillo
    for sx in (-1, 1):
        e = (cx + sx * int(S * 0.11), int(S * 0.64))
        cv2.ellipse(g, e, (int(S * 0.075), int(S * 0.055)), 0, 0, 360, (5, 2, 5, 255), -1, cv2.LINE_AA)
        cv2.line(g, (e[0], e[1] + int(S * 0.04)), (e[0] + sx * 2, e[1] + int(S * 0.2)), (20, 10, 30, 255), max(1, S // 60), cv2.LINE_AA)
    # shadows: the face is not flat white, it has bones and dark circles
    yy, xx = np.mgrid[0:g.shape[0], 0:S].astype(np.float32)
    rad = np.sqrt(((xx - cx) / (S * 0.27)) ** 2 + ((yy - S * 0.68) / (S * 0.36)) ** 2)
    shade = np.clip(1.05 - 0.55 * rad ** 2.2, 0.35, 1)
    tex = 1 - 0.08 * cv2.GaussianBlur(np.random.default_rng(3).random(g.shape[:2]).astype(np.float32), (0, 0), 2)
    g[..., :3] = np.clip(g[..., :3] * (shade * tex)[..., None], 0, 255).astype(np.uint8)
    for sx in (-1, 1):
        cv2.ellipse(g, (cx + sx * int(S * 0.11), int(S * 0.66)), (int(S * 0.11), int(S * 0.09)), 0, 0, 360,
                    (70, 60, 70, 255), -1, cv2.LINE_AA)
        cv2.ellipse(g, (cx + sx * int(S * 0.11), int(S * 0.64)), (int(S * 0.075), int(S * 0.055)), 0, 0, 360,
                    (5, 2, 5, 255), -1, cv2.LINE_AA)
    mh = int(S * (0.02 + 0.16 * mouth))
    cv2.ellipse(g, (cx, int(S * 0.86)), (int(S * (0.05 + 0.05 * mouth)), mh), 0, 0, 360, (8, 2, 8, 255), -1, cv2.LINE_AA)
    g = cv2.GaussianBlur(g, (0, 0), max(1, S / 160))
    _GHOST[key] = g
    return g


def paste_rgba(img, rgba, x, y, alpha=1.0):
    H, W = img.shape[:2]
    h, w = rgba.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return img
    sub = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = sub[..., 3:4].astype(np.float32) / 255 * alpha
    img[y0:y1, x0:x1] = (img[y0:y1, x0:x1] * (1 - a) + sub[..., :3] * a).astype(np.uint8)
    return img


def ghostify(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g = np.clip(g * 1.25 + 35, 0, 255)
    return np.stack([g * 1.05, g, g * 0.92], axis=2).clip(0, 255).astype(np.uint8)


def push_in(img, face, k):
    """The 'camera' slowly pushes in on their face during the build-up (so the effect is clearly visible)."""
    if face is None or not face.ok or k <= 0:
        return img
    H, W = img.shape[:2]
    zmax = max(1.0, min(2.3, 0.5 * H / (4.2 * face.d)))
    z = 1 + (zmax - 1) * k
    w, h = W / z, H / z
    x0 = min(max(0, face.center[0] - w / 2), W - w)
    y0 = min(max(0, face.center[1] - h * 0.45), H - h)
    return cv2.resize(img[int(y0):int(y0 + h), int(x0):int(x0 + w)], (W, H), interpolation=cv2.INTER_LINEAR)


# ------------------------------------------------------------------ the hit
def lunge(img, face, q, red=True, zoom=True):
    """Violent zoom on the face + shake + chromatic aberration + flashes."""
    H, W = img.shape[:2]
    if not zoom:
        out = np.roll(img, (random.randint(-12, 12), random.randint(-12, 12)), axis=(0, 1))
        s = int(4 + 14 * (1 - q))
        b, g, r = cv2.split(out)
        out = cv2.merge([np.roll(b, -s, axis=1), g, np.roll(r, s, axis=1)])
        if red and q < 0.3 and int(q * 30) % 2 == 0:
            out = blend(out, (0, 0, 160), np.full(out.shape[:2], 0.35, np.float32))
        return out
    c = face.center if face is not None and face.ok else np.array([W / 2, H / 2])
    d = face.d if face is not None and face.ok else W / 12
    k = ease(q * 3.2)
    size_h = max(H * 0.3, (1 - k) * min(H, d * 9) + k * d * 3.6)
    size_w = size_h * W / H
    jit = d * 0.35 * (1 - q * 0.6)
    cx = c[0] + random.uniform(-jit, jit)
    cy = c[1] + random.uniform(-jit, jit)
    pad = int(max(size_w, size_h))
    big = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REFLECT)
    x0, y0 = int(cx - size_w / 2) + pad, int(cy - size_h / 2) + pad
    crop = big[y0:y0 + int(size_h), x0:x0 + int(size_w)]
    out = cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR)
    s = int(6 + 18 * (1 - q))
    b, g, r = cv2.split(out)
    out = cv2.merge([np.roll(b, -s, axis=1), g, np.roll(r, s, axis=1)])
    if red and q < 0.45 and int(q * 30) % 2 == 0:
        out = blend(out, (0, 0, 200), np.full(out.shape[:2], 0.45, np.float32))
    if q < 0.04:
        out = 255 - out
    return out


# ------------------------------------------------------------------ each possession
def render(effect, frame, face, t, extra=None):
    """Returns the possessed frame. `t` in seconds since the scare started.
    `extra` (only for 'double'): (delayed frame, its face)."""
    p = min(1.0, t / PRE)
    jumping = t >= PRE
    q = (t - PRE) / POST if jumping else 0.0
    k = ease(p)
    img = frame
    zoom = 0.0 if jumping else ease(p * 1.1) * 0.9
    if effect == "black_eyes":
        img = black_eyes(img, face, ease(p * 1.25))
        if jumping:
            img = gaping_mouth(img, face, ease(q * 4))
    elif effect == "faceless":
        img = faceless(img, face, ease(p * 1.3))
        if jumping:
            img = gaping_mouth(img, face, ease(q * 3.5), teeth=True)
    elif effect == "melt":
        img = melt(img, face, ease(p) * 0.9 + (q * 0.6 if jumping else 0), t)
        if jumping or p > 0.7:
            img = black_eyes(img, face, ease((p - 0.7) * 3.3) if not jumping else 1.0, veins=False)
    elif effect == "grin":
        img = grin(img, face, ease(p * 1.15))
        if p > 0.6:
            img = black_eyes(img, face, ease((p - 0.6) * 2.5), veins=False)
    elif effect == "behind_you":
        img = img.copy()
        if not jumping:
            size = int(face.d * 3.4)
            g = ghost_face(size)
            H, W = img.shape[:2]
            side = -1 if face.center[0] > W / 2 else 1          # peeks out from the side with more room
            reach = face.extent[1] if side > 0 else face.extent[0]
            gx = int(face.center[0] + side * (reach + face.d * 0.3 + size * 0.5) - size / 2)
            gy = int(face.mid[1] - face.d * 2.3)
            appear = ease((p - 0.25) / 0.5)
            alpha = appear * (0.55 + 0.45 * (random.random() > 0.12))
            dark = img.copy()
            paste_rgba(dark, g, gx, gy, 1.0)
            img = blend(img, dark, np.full(img.shape[:2], alpha * 0.9, np.float32))
    elif effect == "double" and extra is not None:
        late, lface = extra
        H, W = img.shape[:2]
        ghost = ghostify(late)
        if lface is not None and lface.ok:
            ghost = black_eyes(ghost, lface, ease(p * 1.4), veins=False)
        shift = int(W * (0.3 - 0.2 * k))
        M = np.float32([[1, 0, shift], [0, 1, 0]])
        moved = cv2.warpAffine(ghost, M, (W, H), borderMode=cv2.BORDER_CONSTANT)
        mask = (cv2.cvtColor(moved, cv2.COLOR_BGR2GRAY) > 0).astype(np.float32)
        if lface is not None and lface.ok:             # only THEIR silhouette, not the whole room
            band = np.zeros((H, W), np.float32)
            cx = int(lface.center[0] + shift)
            cv2.rectangle(band, (int(cx - lface.d * 3.2), int(lface.mid[1] - lface.d * 2.4)), (int(cx + lface.d * 3.2), H), 1.0, -1)
            band = cv2.GaussianBlur(band, (0, 0), lface.d * 0.9)
            mask *= band
        mask *= 0.3 + 0.5 * k
        img = blend(img, moved, mask)
        if jumping and lface is not None and lface.ok:
            ghost = gaping_mouth(black_eyes(ghostify(late), lface, 1.0), lface, ease(q * 4))
            return lunge(grade(ghost, 1.0, t), lface, q)
    if effect != "double":
        img = push_in(img, face, zoom)
    img = grade(img, 0.35 + 0.65 * k if not jumping else 1.0, t)
    if jumping:
        if effect == "behind_you":
            H, W = img.shape[:2]
            size = int(H * (0.7 + 0.6 * ease(q * 3)))
            g = ghost_face(size, mouth=min(1.0, q * 4))
            base = (img * 0.35).astype(np.uint8)
            jit = int(H * 0.03 * (1 - q))
            paste_rgba(base, g, W // 2 - size // 2 + random.randint(-jit, jit),
                       int(H * 0.5 - size * 0.75) + random.randint(-jit, jit))
            return grade(lunge(base, None, q, zoom=False), 0.8, t)
        img = lunge(img, face, q)
    return img


class OpenCvPossessionService(PossessionService):
    def render(self, effect, frame, face, t, extra=None):
        return render(effect, frame, face, t, extra)

    def possess_photo(self, image_rgb, face):
        bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        out = black_eyes(bgr, face, 1.0)
        out = gaping_mouth(out, face, 0.55)
        return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
