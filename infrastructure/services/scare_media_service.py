"""
Turns the imagined photos into scares (video + sound) and stores everything in the Scare-TV 2 folder:
darkness, a flashlight sweeping the scene and revealing pieces of it… then suddenly the whole photo, with a
zoom on the face, shaking, a red flash and a scream.
"""
import json
import os
import shutil
import subprocess

import numpy as np

from domain.rules.face_geometry import Face
from domain.rules.realistic_scares import JUMP, SCARES, plausible_face
from domain.services.scare_media_service import ScareMediaService
from infrastructure.services.synth import horror_audio as ha

W, H, FPS, DUR = 854, 480, 24, 3.6


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def cover_resize(img, w, h):
    import cv2

    ih, iw = img.shape[:2]
    k = max(w / iw, h / ih)
    r = cv2.resize(img, (int(iw * k) + 1, int(ih * k) + 1), interpolation=cv2.INTER_LANCZOS4)
    y0, x0 = (r.shape[0] - h) // 2, (r.shape[1] - w) // 2
    return r[y0:y0 + h, x0:x0 + w]


def frame_at(base, t, rng, focus=None):
    """base: the photo at 854x480 (RGB). focus: relative (x, y, face size), or None. Returns the frame at second t."""

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    grain = rng.normal(0, 10, (H, W, 1)).astype(np.float32)
    if t < JUMP:
        p = t / JUMP
        # a flashlight sweeping the scene: you see a piece… and never what is in the centre
        cx = W * (0.15 + 0.7 * (0.5 + 0.5 * np.sin(t * 1.7)))
        cy = H * (0.55 + 0.15 * np.sin(t * 2.3))
        r = W * 0.16
        spot = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))
        flicker = 0.0 if rng.random() < 0.06 else 1.0
        light = (0.05 + 0.4 * spot * flicker) * (0.6 + 0.4 * p)
        z = 1.0 + 0.06 * p
        img = cover_resize(base, int(W * z), int(H * z))
        img = img[(img.shape[0] - H) // 2:(img.shape[0] - H) // 2 + H, (img.shape[1] - W) // 2:(img.shape[1] - W) // 2 + W]
        out = img.astype(np.float32) * light[..., None] + grain * 0.6
    else:
        q = t - JUMP
        zmax = 1.42 if not focus else float(np.clip(0.2 / max(focus[2], 1e-3), 1.42, 3.2))   # small face → more zoom
        z = 1.12 + (zmax - 1.12) * ease(q * 4)
        jit = int(30 * max(0.0, 1 - q * 1.3))
        img = cover_resize(base, int(W * z), int(H * z))
        fx, fy = (focus[0], focus[1]) if focus else (0.5, 0.5)
        y0 = int(fy * img.shape[0] - H * 0.45) + rng.integers(-jit, jit + 1)
        x0 = int(fx * img.shape[1] - W / 2) + rng.integers(-jit, jit + 1)
        y0, x0 = int(np.clip(y0, 0, img.shape[0] - H)), int(np.clip(x0, 0, img.shape[1] - W))
        out = img[y0:y0 + H, x0:x0 + W].astype(np.float32)
        s = int(4 + 12 * max(0.0, 1 - q))
        out = np.stack([np.roll(out[..., 0], s, axis=1), out[..., 1], np.roll(out[..., 2], -s, axis=1)], axis=2)
        out = out * 1.15 + grain
        if q < 0.45 and int(q * 24) % 2 == 0:
            out = out * 0.6 + np.array([200, 0, 10], np.float32) * 0.4
        if q < 0.05:
            out = 255 - out
        if rng.random() < 0.25:            # old tape lines
            y, hgt = int(rng.integers(0, H - 8)), int(rng.integers(2, 7))
            out[y:y + hgt] = np.roll(out[y:y + hgt], int(rng.integers(-40, 40)), axis=1)
    vig = 1 - 0.7 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.2
    out *= np.clip(vig, 0.1, 1)[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def write_video(path, base, seed, focus=None):
    rng = np.random.default_rng(seed)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(frame_at(base, i / FPS, rng, focus).tobytes())
    p.stdin.close()
    p.wait()


def write_video_cv(path, base, seed, focus=None):
    """Without ffmpeg: OpenCV writes the mp4 directly."""
    import cv2

    rng = np.random.default_rng(seed)
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for i in range(int(DUR * FPS)):
        w.write(cv2.cvtColor(frame_at(base, i / FPS, rng, focus), cv2.COLOR_RGB2BGR))
    w.release()


def scare_sound(kind, seed):
    ha.rng = np.random.default_rng(seed)
    T = DUR
    tension = ha.drone(JUMP, 36) * 0.6 + ha.heartbeat(JUMP, 92) * 0.6 + ha.whisper_noise(JUMP) * 0.25
    x = ha.at(T, 0, tension)
    x += ha.at(T, JUMP - 0.9, ha.reverse_swell(0.9)) * 0.5
    x += ha.at(T, JUMP, ha.jump_hit(T - JUMP, kind))
    return ha.master(x)


def contact_sheet(OUT):
    """Catalog: on top what SD-Turbo imagined, below the same photo after YOLO-pose possessed it."""
    from PIL import Image

    names = [n for n, _, _ in SCARES if os.path.exists(os.path.join(OUT, f"_{n}.png"))]
    if not names:
        return
    tw, th = 256, 144
    sheet = Image.new("RGB", (tw * len(names), th * 2))
    for k, n in enumerate(names):
        raw = os.path.join(OUT, f"_{n}_imagined.png")
        if os.path.exists(raw):
            sheet.paste(Image.open(raw).convert("RGB").resize((tw, th)), (k * tw, 0))
        sheet.paste(Image.open(os.path.join(OUT, f"_{n}.png")).convert("RGB").resize((tw, th)), (k * tw, th))
    sheet.save(os.path.join(OUT, "_catalog_real.jpg"), quality=85)




def _read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class FileScareMediaService(ScareMediaService):
    def __init__(self, detector=None, live_tracks_dir=None, ghost_png=None):
        self.detector = detector              # the same YOLO-pose that triggers the scares
        self.live_tracks_dir = live_tracks_dir
        self.ghost_png = ghost_png

    # ---- fotos
    def find_face(self, image_rgb):
        import cv2

        if self.detector is None:
            return None
        kp, box = self.detector.person(cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR), conf=0.25, imgsz=640)
        face = Face(kp, box) if box is not None else None
        return face if plausible_face(face, kp, image_rgb.shape[1]) else None

    def has_photo(self, folder, name):
        return os.path.exists(os.path.join(folder, f"_{name}_imagined.png"))

    def save_photos(self, folder, name, raw, possessed, focus):
        from PIL import Image

        os.makedirs(folder, exist_ok=True)
        Image.fromarray(raw).save(os.path.join(folder, f"_{name}_imagined.png"))
        Image.fromarray(possessed).save(os.path.join(folder, f"_{name}.png"))
        faces = _read_json(os.path.join(folder, "_faces.json"))
        faces[name] = focus
        with open(os.path.join(folder, "_faces.json"), "w") as f:
            json.dump(faces, f, indent=1)

    def faces(self, folder):
        return _read_json(os.path.join(folder, "_faces.json"))

    def version(self, folder):
        p = os.path.join(folder, "_version.txt")
        return open(p).read().strip() if os.path.exists(p) else ""

    def set_version(self, folder, version):
        with open(os.path.join(folder, "_version.txt"), "w") as f:
            f.write(version)

    # ---- scares
    def build_scare(self, folder, stem, image_rgb, kind, seed, focus=None):
        base = cover_resize(image_rgb, W, H).astype(np.float32)
        gray = base.mean(axis=2, keepdims=True)
        base = base * 0.55 + gray * 0.45                                    # menos color
        base = np.clip((base / 255.0) ** 1.25 * 255 * np.array([0.92, 1.0, 0.95]), 0, 255).astype(np.uint8)   # shadow, cold tone
        (write_video if shutil.which("ffmpeg") else write_video_cv)(os.path.join(folder, stem + ".mp4"), base, seed, focus)
        ha.write_wav(os.path.join(folder, stem + ".wav"), scare_sound(kind, 100 + seed))

    def load_photo(self, folder, name):
        from PIL import Image

        return np.asarray(Image.open(os.path.join(folder, f"_{name}.png")).convert("RGB"))

    def finish(self, folder, built):
        jumps = {stem: JUMP for stem in built}
        with open(os.path.join(folder, "_jumps.json"), "w") as f:
            json.dump(jumps, f, indent=1)
        old = os.path.join(folder, "_old")              # scares from older versions: moved aside, never deleted
        for fname in os.listdir(folder):
            stem, ext = os.path.splitext(fname)
            if fname.startswith("real_") and ext in (".mp4", ".wav") and stem not in jumps:
                os.makedirs(old, exist_ok=True)
                shutil.move(os.path.join(folder, fname), os.path.join(old, fname))
        if self.live_tracks_dir and os.path.isdir(self.live_tracks_dir):   # live scares use their sound tracks from here
            shutil.copytree(self.live_tracks_dir, os.path.join(folder, "live"), dirs_exist_ok=True)
        if self.ghost_png and os.path.exists(self.ghost_png):
            shutil.copy(self.ghost_png, os.path.join(folder, "_mirror_ghost.png"))
        contact_sheet(folder)
