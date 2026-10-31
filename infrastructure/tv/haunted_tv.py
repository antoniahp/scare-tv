"""
The haunted TV (driving adapter): the webcam watches, YOLO-pose detects the person and the TV becomes a
mirror… and possesses them. It talks to the domain through commands and queries (CQRS): start the night,
record arrivals and scares, mark false alarms, finish the night and summarize it.
"""
import glob
import os
import random
import shutil
import subprocess
import sys
import threading
import time
from collections import deque

import cv2
import numpy as np
import pygame
from django.conf import settings

from application.commands.finish_night.command import FinishNightCommand
from application.commands.finish_night.command_dto import FinishNightCommandDTO
from application.commands.mark_false_alarm.command import MarkFalseAlarmCommand
from application.commands.mark_false_alarm.command_dto import MarkFalseAlarmCommandDTO
from application.commands.prepare_voices.command import PrepareVoicesCommand
from application.commands.prepare_voices.command_dto import PrepareVoicesCommandDTO
from application.commands.record_arrival.command import RecordArrivalCommand
from application.commands.record_arrival.command_dto import RecordArrivalCommandDTO
from application.commands.record_scare.command import RecordScareCommand
from application.commands.record_scare.command_dto import RecordScareCommandDTO
from application.commands.start_night.command import StartNightCommand
from application.commands.start_night.command_dto import StartNightCommandDTO
from infrastructure.services.production_uploader import ProductionUploader, upload_url
from application.queries.get_night_summary.query import GetNightSummaryQuery
from application.queries.get_night_summary.query_dto import GetNightSummaryQueryDTO
from domain.exceptions import NoScaresAvailable, NothingToMark
from domain.rules import possessions as P
from domain.rules.face_geometry import Face, lerp_face
from domain.rules.flinch import Flinch, score10
from domain.rules.night_summary import as_markdown
from infrastructure import dependencies
from infrastructure.repositories.file_scare_catalog_repository import GIF_EXT, VIDEO_EXT
from infrastructure.services.opencv_possession_service import blend, ease, grade
from infrastructure.tv.drawing import cover, cv_to_surface, load_font, render_text
from infrastructure.tv.pumpkin_bait import PumpkinBait


class ScareTV:
    def __init__(self, args):
        self.args = args
        self.audio = self._init_audio()
        pygame.init()
        pygame.mouse.set_visible(False)
        flags = pygame.FULLSCREEN if not args.windowed else 0
        size = (0, 0) if not args.windowed else (960, 540)
        try:
            self.screen = pygame.display.set_mode(size, flags, display=args.display)
        except pygame.error:
            print(f"[warning] Display {args.display} does not exist. Using the main one.")
            self.screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Scare-TV")
        self.size = self.screen.get_size()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 26, bold=True)
        self.muted = False
        self.debug = args.debug
        self.running = True

        self.repositories = dependencies.get_repositories()
        self.scares = self.repositories.catalog.load(args.media, args.lang)
        if not self.scares:
            raise NoScaresAvailable(args.media)
        self.queue = []
        print(f"{len(self.scares)} scares loaded.")

        overlay = os.path.join(args.media, "_mirror_ghost.png")
        self.ghost_overlay = pygame.image.load(overlay).convert_alpha() if os.path.exists(overlay) else None
        self.f_scare = load_font(max(28, int(self.size[1] * 0.1)))
        self.f_small = load_font(max(18, int(self.size[1] * 0.045)))

        self.idle = None
        self.bait = None
        if args.idle not in ("pumpkin", "black") and os.path.exists(args.idle):
            self.idle, self.idle_pos = cover(pygame.image.load(args.idle).convert(), self.size)
        elif args.idle == "pumpkin":
            self.bait = PumpkinBait(self.size, args.lang)
        self.count = 0
        self.t_start = time.time()
        self.night = None
        if args.log:                          # the night log: numbers only (local database)
            media_name = os.path.basename(os.path.normpath(str(args.media)))
            self.night = StartNightCommand(self.repositories).execute(StartNightCommandDTO(lang=args.lang, media=media_name))
        # ...and a copy of every record in the production database (Render), in the background
        self.uploader = ProductionUploader(upload_url() if args.log and getattr(args, "upload", True) else None)
        if self.uploader.enabled:
            self.uploader.night(self.night)
            print(f"Night log: also sent to {self.uploader.base} (numbers only)", flush=True)
        self.arrived_t = None
        self.arrival = None                   # the person in front of the TV right now (their scares hang from it)
        self.present = False
        self.trigger = "auto"

        self.cap = cv2.VideoCapture(int(args.camera) if str(args.camera).isdigit() else args.camera)
        if not self.cap.isOpened():
            sys.exit("Cannot open the camera. On a Mac: System Settings > Privacy & Security > Camera > allow your Terminal.")
        self.detector = dependencies.get_person_detector(args.detector, args.model, args.conf, args.motion)
        self.possession = dependencies.get_possession_service()
        self.voices = dependencies.get_voice_service(log=lambda m: print(m, flush=True))
        self.pose_ok = self.detector.pose                      # knows where the eyes are (measures jumps, ambushes)
        self.live_ok = self.pose_ok and args.live_chance > 0
        self.buffer = deque(maxlen=40)      # ~2 s of recent frames (for the 'double')
        self.last_face = None
        self.last_face_t = 0.0
        self.effects = []
        self._procs = []
        self.sfx = sorted(glob.glob(os.path.join(args.media, "sfx", "*.wav")) + glob.glob(os.path.join(args.media, "sfx", "*.mp3")))
        if self.live_ok:
            threading.Thread(target=self._prepare_live_audio, daemon=True).start()
            print(f"Live scares: YES ({int(args.live_chance * 100)} % of the time). Effects: {', '.join(P.EFFECTS)}")
        elif self.detector.kind == "yolo":
            print("Live scares: no (a pose model is needed, e.g. --model yolo11n-pose.pt)")
        print(f"Detector: {self.detector.kind}. Waiting for victims... (SPACE = test, L = live, ESC = quit)")

    def _prepare_live_audio(self):
        """Live-scare sound tracks + voices. In the background so startup is not delayed."""
        try:
            self._build_live_audio()
        except Exception as e:  # noqa: BLE001  (scares still work without voices)
            print(f"[warning] Could not prepare the voices ({e}). Try: make install", flush=True)

    def _build_live_audio(self):
        from infrastructure.services.synth import horror_audio as ha

        live = os.path.join(self.args.media, "live")
        os.makedirs(live, exist_ok=True)
        for e in P.EFFECTS:
            p = os.path.join(live, e + ".wav")
            if not os.path.exists(p):
                ha.write_wav(p, ha.live_track(e, P.PRE, P.POST))
        PrepareVoicesCommand(self.voices).execute(PrepareVoicesCommandDTO(folder=str(self.args.media), lang=self.args.lang))

    # ------------------------------------------------------------------ helpers
    def next_scare(self):
        if self.args.order == "sequence":
            if not self.queue:
                self.queue = list(self.scares)
            return self.queue.pop(0)
        if not self.queue:  # random, no repeats until the list runs out
            self.queue = random.sample(self.scares, len(self.scares))
        return self.queue.pop()

    def handle_events(self):
        """Returns 'test', 'next' or None. Handles quit, debug and mute."""
        action = None
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    self.running = False
                elif e.key == pygame.K_SPACE:
                    action = "test"
                elif e.key == pygame.K_n:
                    action = "next"
                elif e.key == pygame.K_l:
                    action = "live"
                elif e.key == pygame.K_f:
                    if self.night:
                        try:
                            marked = MarkFalseAlarmCommand(self.repositories).execute(MarkFalseAlarmCommandDTO(night_id=self.night.id))
                            self.uploader.scare(marked)
                            print("   (last scare marked as a false alarm)", flush=True)
                        except NothingToMark:
                            pass
                elif e.key == pygame.K_d:
                    self.debug = not self.debug
                elif e.key == pygame.K_m:
                    self.muted = not self.muted
                    self.stop_sound()
        return action

    # ------------------------------------------------------------------ sound
    def _init_audio(self):
        """pygame.mixer if available; otherwise (e.g. pygame without SDL_mixer) the system player."""
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            return "mixer"
        except (NotImplementedError, pygame.error, AttributeError) as e:
            for player in ("afplay", "ffplay", "paplay", "aplay"):
                if shutil.which(player):
                    print(f"[warning] pygame.mixer not available ({e.__class__.__name__}). Using '{player}' for sound.")
                    return player
            print("[warning] No way to play sound: scares will be silent.")
            return None

    def play_sound(self, path, exclusive=True):
        if self.muted or not path or not self.audio or not os.path.exists(path):
            return
        if self.audio == "mixer":
            try:
                snd = pygame.mixer.Sound(path)
                snd.set_volume(self.args.volume)
                snd.play()
            except pygame.error as e:
                print(f"[warning] Could not play {path}: {e}")
            return
        cmd = {"afplay": ["afplay", "-v", str(self.args.volume), path],
               "ffplay": ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
               "paplay": ["paplay", path], "aplay": ["aplay", "-q", path]}[self.audio]
        if exclusive:
            self.stop_sound()
        self._procs.append(subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

    def stop_sound(self, fade=False):
        if self.audio == "mixer":
            pygame.mixer.fadeout(400) if fade else pygame.mixer.stop()
            return
        for p in getattr(self, "_procs", []):
            if p.poll() is None:
                p.terminate()
        self._procs = []

    # ------------------------------------------------------------------ scares
    def play(self, scare):
        self.count += 1
        print(f"👻  {time.strftime('%H:%M:%S')}  scare: {scare.name}", flush=True)
        v = scare.visual.lower()
        face_now = self._fresh_face()
        self.play_sound(scare.sound_path)
        measured = (None, False, None)
        if v.endswith(VIDEO_EXT):
            measured = self._play_video(scare.visual, scare.jump_at)
        elif v.endswith(GIF_EXT):
            self._play_gif(scare.visual)
        else:
            self._play_image(scare.visual)
        fl, fled, reaction = measured
        self._log_scare("file", scare.name, face_now, fl, fled)
        if reaction is not None and self.args.reaction:
            self.show_reaction(*reaction, score=score10(fl))
        self.stop_sound(fade=True)
        self._flush_camera()

    def _fresh_face(self):
        return self.last_face is not None and time.time() - self.last_face_t < 1.0

    def _log_scare(self, kind, name, face, flinch, fled):
        wait = round(time.time() - self.arrived_t, 1) if self.arrived_t else None
        if self.night:
            event = RecordScareCommand(self.repositories).execute(RecordScareCommandDTO(
                night_id=self.night.id, kind=kind, name=name, face_seen=bool(face), flinch=flinch, fled=fled,
                wait_seconds=wait, trigger=self.trigger, arrival_id=self.arrival.id if self.arrival else None))
            self.uploader.scare(event)
        if flinch is not None:
            print(f"   jump-o-meter: {score10(flinch)}/10 ({flinch} eye-distances){'  FLED!' if fled else ''}", flush=True)

    def _play_video(self, path, jump_t=0.0):
        """Classic scare, ambush version: first the TV is a dark mirror with you in it (with subliminal flashes
        of the monster) and at the second of the hit the drawing jumps on top, with zoom, shake and red.
        With a pose model it also measures how far the person jumps."""
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        measure = self.pose_ok
        ambush = measure and jump_t > 0.6 and self._fresh_face()
        monster = None
        if ambush:                                   # the monster frame, for the flashes
            cap.set(cv2.CAP_PROP_POS_FRAMES, int((jump_t + 0.35) * fps))
            okm, monster = cap.read()
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            if not okm:
                ambush, monster = False, None
        flinch = Flinch(jump_t)
        reaction = None
        flashes = sorted(random.uniform(0.5, max(0.6, jump_t - 0.5)) for _ in range(2)) if ambush else []
        t0 = time.time()
        i = 0
        while self.running:
            t = time.time() - t0
            target = int(t * fps)                    # if measuring slows us down, skip video frames
            while i < target - 1:
                cap.grab()
                i += 1
            ok, frame = cap.read()
            if not ok or t > self.args.max_seconds:
                break
            i += 1
            big = None
            if measure:
                okc, big = self.cap.read()
                if okc:
                    fr = cv2.resize(big, P.WORK)
                    face = self._face_from(*self.detector.person(fr), fr.shape[1])
                    flinch.update(t, face)
                    if reaction is None and t > jump_t + 0.45 and face is not None and face.from_kp:
                        reaction = (cv2.flip(big, 1), face.scaled(big.shape[1] / fr.shape[1]))
                else:
                    big = None
            if ambush and t < jump_t and big is not None:
                out = self._dark_mirror(cv2.resize(big, P.WORK), t / jump_t, monster,
                                        any(abs(t - f) < 0.07 for f in flashes))
            elif t >= jump_t:
                out = self._ambush_hit(frame, (t - jump_t) / max(0.5, self.args.max_seconds - jump_t), t - jump_t)
            else:
                out = grade(frame, 1.0, t)   # no camera: the wait, almost in the dark
            surf, pos = cover(cv_to_surface(out), self.size)
            self.screen.fill((0, 0, 0))
            self.screen.blit(surf, pos)
            pygame.display.flip()
            self.handle_events()
            delay = t0 + i / fps - time.time()       # keeps the video's pace
            if delay > 0:
                time.sleep(delay)
        cap.release()
        fl, fled = flinch.result() if measure else (None, False)
        return fl, fled, reaction

    def _dark_mirror(self, cam, p, monster, flash):
        """The wait: your reflection, darker and greener every moment… and sometimes a frame of something that shouldn't be there."""
        img = grade(cv2.flip(cam, 1), 0.55 + 0.45 * p, p)
        img = (img.astype(np.float32) * (1.0 - 0.55 * p)).astype(np.uint8)          # the light fades out
        if flash and monster is not None:
            m = cv2.resize(monster, (img.shape[1], img.shape[0]))
            img = cv2.addWeighted(img, 0.45, m, 0.55, 0)
        return img

    def _ambush_hit(self, frame, q, dt):
        """The hit on the drawing: it lunges, shakes, turns red and looks 'dirty', like old tape."""
        H, W = frame.shape[:2]
        z = 1.0 + 0.32 * ease(dt * 4) - 0.08 * ease((dt - 0.6) * 2)
        jit = int(28 * max(0.0, 1 - dt * 1.4))
        cw, ch = int(W / z), int(H / z)
        x0 = min(max(0, (W - cw) // 2 + random.randint(-jit, jit)), W - cw)
        y0 = min(max(0, (H - ch) // 2 + random.randint(-jit, jit)), H - ch)
        out = cv2.resize(frame[y0:y0 + ch, x0:x0 + cw], (W, H))
        s = int(3 + 10 * max(0.0, 1 - dt))
        b, g, r = cv2.split(out)
        out = cv2.merge([np.roll(b, -s, axis=1), g, np.roll(r, s, axis=1)])
        out = grade(out, 0.55, dt)
        if dt < 0.5 and int(dt * 24) % 2 == 0:
            out = blend(out, (0, 0, 190), np.full(out.shape[:2], 0.4, np.float32))
        if dt < 0.05:
            out = 255 - out
        return out

    def _play_gif(self, path):
        from PIL import Image, ImageSequence

        im = Image.open(path)
        frames = []
        for fr in ImageSequence.Iterator(im):
            rgba = fr.convert("RGBA")
            s = pygame.image.fromstring(rgba.tobytes(), rgba.size, "RGBA").convert_alpha()
            frames.append((cover(s, self.size), fr.info.get("duration", 80) / 1000))
        t_end = time.time() + min(self.args.max_seconds, max(2.5, sum(d for _, d in frames)))
        while self.running and time.time() < t_end:
            for (surf, pos), dur in frames:
                self.screen.fill((0, 0, 0))
                self.screen.blit(surf, pos)
                pygame.display.flip()
                self.handle_events()
                time.sleep(dur)
                if time.time() >= t_end:
                    break

    def _play_image(self, path):
        base = pygame.image.load(path).convert()
        t0 = time.time()
        dur = min(self.args.max_seconds, 3.0)
        while self.running and time.time() - t0 < dur:
            p = (time.time() - t0) / dur
            zoom = 1.0 + 0.35 * (1 - (1 - p) ** 3)  # lunges at you
            surf, pos = cover(base, (int(self.size[0] * zoom), int(self.size[1] * zoom)))
            ox = (self.size[0] - surf.get_width()) // 2 + random.randint(-12, 12)
            oy = (self.size[1] - surf.get_height()) // 2 + random.randint(-12, 12)
            self.screen.fill((0, 0, 0))
            self.screen.blit(surf, (ox, oy))
            pygame.display.flip()
            self.handle_events()
            self.clock.tick(30)

    def mirror_scare(self, frame):
        """Mirror mode: the TV shows the victim like a mirror… and something appears behind them."""
        print(f"🪞  {time.strftime('%H:%M:%S')}  mirror mode", flush=True)
        mirror, pos = cover(cv_to_surface(cv2.flip(frame, 1)), self.size)
        t0 = time.time()
        while self.running and time.time() - t0 < 2.2:
            p = (time.time() - t0) / 2.2
            self.screen.blit(mirror, pos)
            if self.ghost_overlay is not None and p > 0.35:
                g = self.ghost_overlay.copy()
                g.set_alpha(int(255 * min(1, (p - 0.35) / 0.5) * 0.85))
                h = int(self.size[1] * 0.55)
                g = pygame.transform.smoothscale(g, (int(g.get_width() * h / g.get_height()), h))
                self.screen.blit(g, (int(self.size[0] * 0.68) - g.get_width() // 2, int(self.size[1] * 0.08)))
            pygame.display.flip()
            self.handle_events()
            self.clock.tick(30)
        self.play(self.next_scare())

    # ------------------------------------------------------------------ LIVE scares (their real face)
    def _face_from(self, kp, box, frame_w):
        if box is None:
            return None
        f = Face(kp, box)
        return f.mirrored(frame_w) if f.ok else None

    def next_effect(self):
        if not self.effects:
            self.effects = random.sample(P.EFFECTS, len(P.EFFECTS))
        return self.effects.pop()

    def live_scare(self, frame, effect=None):
        """The TV is a mirror… and something happens to the person looking at it. Nothing is recorded."""
        effect = effect or self.next_effect()
        self.count += 1
        print(f"🩸  {time.strftime('%H:%M:%S')}  LIVE scare: {effect}", flush=True)
        lang_i = 0 if self.args.lang == "es" else 1
        text = P.TEXTS[effect][lang_i]
        self.play_sound(os.path.join(self.args.media, "live", effect + ".wav"))
        voice = self.voices.find(self.args.media, self.args.lang, effect)
        cues = {"voice": (0.45, voice), "sfx": (P.PRE, random.choice(self.sfx) if self.sfx else None)}
        face = self.last_face
        face_now = self._fresh_face()
        flinch = Flinch(P.PRE)
        reaction = None
        last = frame
        t0 = time.time()
        total = P.PRE + P.POST
        while self.running:
            t = time.time() - t0
            if t >= total:
                break
            for name, (when, path) in list(cues.items()):
                if t >= when:
                    self.play_sound(path, exclusive=False)
                    del cues[name]
            ok, big = self.cap.read()
            if not ok:
                big = last
            last = big
            fr = cv2.resize(big, P.WORK)          # the whole effect at 640x360: smooth without a GPU
            new = self._face_from(*self.detector.person(fr), fr.shape[1])
            flinch.update(t, new)
            face = lerp_face(face, new, 0.45)
            self.buffer.append((fr, new))
            mir = cv2.flip(fr, 1)
            if face is None or not face.ok:       # left the frame: use the centre
                face = Face(box=(fr.shape[1] * 0.4, fr.shape[0] * 0.15, fr.shape[1] * 0.6, fr.shape[0] * 0.9))
            extra = None
            if effect == "double" and len(self.buffer) > 5:
                late, lface = self.buffer[max(0, len(self.buffer) - 25)]
                extra = (cv2.flip(late, 1), lface)
            out = self.possession.render(effect, mir, face, t, extra)
            if reaction is None and t > P.PRE + 0.45:   # their real face, half a second after the scare
                reaction = (cv2.flip(big, 1), face.scaled(big.shape[1] / fr.shape[1]))
            surf, pos = cover(cv_to_surface(out), self.size)
            self.screen.fill((0, 0, 0))
            self.screen.blit(surf, pos)
            p = t / P.PRE
            if 0.4 < p < 1.0 and random.random() > 0.15:
                txt = render_text(self.f_scare, text, (235, 225, 225) if p < 0.8 else (230, 30, 40))
                txt.set_alpha(int(255 * min(1, (p - 0.4) * 3)))
                self.screen.blit(txt, (self.size[0] // 2 - txt.get_width() // 2, int(self.size[1] * 0.82)))
            pygame.display.flip()
            self.handle_events()
        fl, fled = flinch.result()
        self._log_scare("live", effect, face_now, fl, fled)
        if reaction is not None and self.args.reaction:
            self.show_reaction(*reaction, score=score10(fl))
        self.stop_sound(fade=True)
        self._flush_camera()

    def show_reaction(self, img, face, score=None):
        """The photo of their scared face, as a polaroid. Only saved with --save-reactions."""
        H, W = img.shape[:2]
        if face is not None and face.ok:
            s = min(int(face.d * 7), W, H)
            c = face.center
            x0, y0 = int(max(0, min(W - s, c[0] - s / 2))), int(max(0, min(H - s, c[1] - s * 0.45)))
            crop = img[y0:y0 + s, x0:x0 + s]
        else:
            crop = img
        if self.args.save_reactions:
            folder = settings.BASE_DIR / "reactions"
            os.makedirs(folder, exist_ok=True)
            cv2.imwrite(str(folder / time.strftime("scare_%Y%m%d_%H%M%S.jpg")), crop)
        side = int(self.size[1] * 0.62)
        photo = pygame.transform.smoothscale(cv_to_surface(crop), (side, int(side * crop.shape[0] / crop.shape[1])))
        b = int(side * 0.05)
        card = pygame.Surface((photo.get_width() + 2 * b, photo.get_height() + (7 if score is not None else 5) * b))
        card.fill((240, 236, 226))
        card.blit(photo, (b, b))
        cap1 = render_text(self.f_small, ("¡TU CARA DE SUSTO!" if self.args.lang == "es" else "YOUR SCARED FACE!"), (30, 20, 20))
        card.blit(cap1, (card.get_width() // 2 - cap1.get_width() // 2, photo.get_height() + int(b * 1.6)))
        if score is not None:
            label = ("SALTÓMETRO" if self.args.lang == "es" else "JUMP-O-METER") + f"  {score}/10"
            cap2 = render_text(self.f_small, label, (190, 20, 30))
            if cap2.get_width() > card.get_width() - 2 * b:
                cap2 = pygame.transform.smoothscale(cap2, (card.get_width() - 2 * b, int(cap2.get_height() * (card.get_width() - 2 * b) / cap2.get_width())))
            card.blit(cap2, (card.get_width() // 2 - cap2.get_width() // 2, photo.get_height() + int(b * 4.0)))
        card = pygame.transform.rotate(card, random.choice((-4, -3, 3, 4)))
        hny = render_text(self.f_scare, "Happy Halloween" if self.args.lang == "en" else "Feliz Halloween", (255, 122, 26))
        t0 = time.time()
        while self.running and time.time() - t0 < 3.2:
            k = min(1, (time.time() - t0) / 0.35)
            self.screen.fill((12, 6, 18))
            sc = pygame.transform.rotozoom(card, 0, 0.7 + 0.3 * k)
            self.screen.blit(sc, (self.size[0] // 2 - sc.get_width() // 2, int(self.size[1] * 0.52) - sc.get_height() // 2))
            self.screen.blit(hny, (self.size[0] // 2 - hny.get_width() // 2, int(self.size[1] * 0.02)))
            pygame.display.flip()
            self.handle_events()
            self.clock.tick(30)

    def _flush_camera(self):
        for _ in range(5):
            self.cap.grab()
        self.detector.reset()

    # ------------------------------------------------------------------ waiting screen
    def draw_idle(self, frame, detected):
        if self.idle is not None:
            self.screen.blit(self.idle, self.idle_pos)
        elif self.bait is not None:
            self.bait.draw(self.screen, time.time() - self.t_start)
        else:
            self.screen.fill((0, 0, 0))
        if self.debug and frame is not None:
            small = cv2.resize(frame, (480, 270))
            sx, sy = 480 / frame.shape[1], 270 / frame.shape[0]
            for (x1, y1, x2, y2) in self.detector.last_boxes:
                cv2.rectangle(small, (int(x1 * sx), int(y1 * sy)), (int(x2 * sx), int(y2 * sy)), (26, 122, 255), 3)
            who = len(self.detector.last_boxes) if self.detector.kind == "yolo" else ("yes" if detected else "no")
            lines = [render_text(self.font, f"detector: {self.detector.kind}   people: {who}   scares: {self.count}",
                                      (255, 122, 26)),
                     render_text(self.font, "SPACE test · N next · D hide · M mute · ESC quit", (220, 210, 230))]
            panel = pygame.Surface((max(520, max(s.get_width() for s in lines) + 40), 400), pygame.SRCALPHA)
            panel.fill((10, 6, 17, 225))
            self.screen.blit(panel, (10, 10))
            self.screen.blit(cv_to_surface(small), (30, 30))
            for i, line in enumerate(lines):
                self.screen.blit(line, (30, 316 + i * 34))
        pygame.display.flip()

    # ------------------------------------------------------------------ main loop
    def run(self):
        streak = 0
        last_seen = 0.0
        armed = True
        last_scare = 0.0
        while self.running:
            if self.args.run_seconds and time.time() - self.t_start > self.args.run_seconds:
                break
            action = self.handle_events()
            ok, frame = self.cap.read()
            if not ok and not str(self.args.camera).isdigit():  # test video: start over
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
            detected = bool(ok and self.detector.detect(frame))
            now = time.time()
            if ok and self.pose_ok:
                f = self._face_from(*self.detector.last_person, frame.shape[1]) if detected else None
                k = P.WORK[0] / frame.shape[1]
                f = f.scaled(k) if f is not None else None
                self.buffer.append((cv2.resize(frame, P.WORK), f))
                if f is not None and f.from_kp:    # only if the face is VISIBLE (not just legs)
                    self.last_face, self.last_face_t = lerp_face(self.last_face, f, 0.5), now
            if detected:
                streak += 1
                if not self.present:
                    self.present, self.arrived_t = True, now
                    if self.night:
                        self.arrival = RecordArrivalCommand(self.repositories).execute(RecordArrivalCommandDTO(night_id=self.night.id))
                        self.uploader.arrival(self.arrival)
                last_seen = now
            else:
                streak = 0
                if now - last_seen > self.args.rearm:
                    armed = True  # they left: next time they show up, scare
                    self.present = False

            if self.args.repeat and detected and now - last_scare > self.args.repeat:
                armed = True  # someone is still there (e.g. sitting at the computer): scare again
            should = (armed and streak >= self.args.frames and now - last_scare > self.args.cooldown)
            if action in ("test", "next", "live") or should:
                self.trigger = action or ("repeat" if self.args.repeat and self.arrived_t and now - self.arrived_t > self.args.repeat else "auto")
                fresh = self.last_face is not None and now - self.last_face_t < 1.0
                if ok and self.live_ok and (action == "live" or (action != "next" and fresh
                                                                 and random.random() < self.args.live_chance)):
                    if action == "live" and not fresh:
                        self.last_face = None
                    self.live_scare(frame)
                elif ok and self.args.mirror_chance > 0 and random.random() < self.args.mirror_chance and action != "next":
                    self.mirror_scare(frame)
                else:
                    self.play(self.next_scare())
                last_scare = time.time()
                armed = False
                streak = 0
                continue
            self.draw_idle(frame if ok else None, detected)
            self.clock.tick(20)
        self.cap.release()
        pygame.quit()
        print(f"Done. Scares: {self.count}", flush=True)
        if self.night:
            self.uploader.night(FinishNightCommand(self.repositories).execute(FinishNightCommandDTO(night_id=self.night.id)))
            self.uploader.flush()
            summary = GetNightSummaryQuery(self.repositories).execute(GetNightSummaryQueryDTO(night_id=self.night.id))
            if summary["scares"] or summary["arrivals"]:
                md = as_markdown(summary, time.strftime("%Y-%m-%d"))
                folder = settings.SCARE_TV["LOGS_DIR"]
                os.makedirs(folder, exist_ok=True)
                path = folder / f"summary_{time.strftime('%Y-%m-%d_%H%M')}.md"
                path.write_text(md + "\n", encoding="utf-8")
                print("\n" + md, flush=True)
                print(f"\n(Summary saved to {path} · also at http://127.0.0.1:8010/api/night/summary with make web)", flush=True)
