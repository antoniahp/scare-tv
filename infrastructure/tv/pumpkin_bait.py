"""The waiting screen: a friendly pumpkin that invites people to come closer… right up to the camera."""
import random

import numpy as np
import pygame
from django.conf import settings

from infrastructure.tv.drawing import render_text


class PumpkinBait:
    """The 'innocent' screen: a friendly pumpkin that invites people to come closer… right up to the camera."""

    TEXT = {"es": ("¡Feliz Halloween!", "acércate… tengo dulces para ti"),
            "en": ("Happy Halloween!", "come closer… I have treats for you")}

    def __init__(self, size, lang="es"):
        self.W, self.H = W, H = size
        self.title, self.sub = self.TEXT.get(lang, self.TEXT["es"])
        font_path = str(settings.SCARE_TV["ASSETS_DIR"] / "Creepster-Regular.ttf")
        try:
            try:
                import pygame.freetype as ft  # draw the font with FreeType directly (avoids the SDL_ttf bug)
                ft.init()
                self.f_title = ft.Font(font_path, max(24, int(H * 0.12)))
                self.f_sub = ft.Font(font_path, max(16, int(H * 0.05)))
            except (ImportError, NotImplementedError, AttributeError):
                self.f_title = pygame.font.Font(font_path, max(24, int(H * 0.12)))
                self.f_sub = pygame.font.Font(font_path, max(16, int(H * 0.05)))
        except (FileNotFoundError, OSError):
            self.f_title = pygame.font.SysFont("Arial", max(24, int(H * 0.1)), bold=True)
            self.f_sub = pygame.font.SysFont("Arial", max(16, int(H * 0.045)))
        # night sky with stars and moon (drawn only once)
        self.bg = pygame.Surface(size)
        for y in range(H):
            k = y / H
            self.bg.fill((int(34 * (1 - k) + 6 * k), int(16 * (1 - k) + 3 * k), int(58 * (1 - k) + 12 * k)), (0, y, W, 1))
        r = random.Random(31)
        for _ in range(140):
            c = r.randint(120, 230)
            self.bg.fill((c, c, c + 20 if c < 235 else 255), (r.randrange(W), r.randrange(int(H * 0.7)), 2, 2))
        mr = int(H * 0.08)
        moon = pygame.Surface((mr * 6, mr * 6), pygame.SRCALPHA)
        for k in range(12, 0, -1):
            pygame.draw.circle(moon, (255, 230, 170, int(6 * (13 - k))), (mr * 3, mr * 3), int(mr * (1 + k * 0.15)))
        pygame.draw.circle(moon, (250, 236, 200), (mr * 3, mr * 3), mr)
        self.bg.blit(moon, (int(W * 0.8) - mr * 3, int(H * 0.16) - mr * 3))
        pygame.draw.rect(self.bg, (8, 4, 12), (0, int(H * 0.86), W, H))
        self.bats = [(r.random() * 10, 0.05 + r.random() * 0.06, 0.12 + r.random() * 0.3, 0.6 + r.random() * 0.8)
                     for _ in range(5)]

    def _pumpkin(self, screen, cx, cy, rad, glow):
        lobes = [(-0.62, 0.8, (214, 92, 10)), (0.62, 0.8, (214, 92, 10)), (-0.32, 0.9, (240, 112, 18)),
                 (0.32, 0.9, (240, 112, 18)), (0, 1.0, (255, 128, 30))]
        pygame.draw.ellipse(screen, (4, 2, 8), (cx - rad * 1.3, cy + rad * 0.62, rad * 2.6, rad * 0.4))
        for dx, w, col in lobes:
            rw, rh = int(rad * w), int(rad * 0.82)
            pygame.draw.ellipse(screen, col, (cx + dx * rad - rw // 1.6, cy - rh, rw * 1.25, rh * 2))
        pygame.draw.rect(screen, (70, 110, 30), (cx - rad * 0.08, cy - rad * 1.02, rad * 0.16, rad * 0.26), border_radius=6)
        # ridges between lobes
        for dx in (-0.45, -0.15, 0.15, 0.45):
            pygame.draw.arc(screen, (180, 70, 5), (cx + dx * rad - rad * 0.12, cy - rad * 0.8, rad * 0.24, rad * 1.6),
                            -1.2 if dx < 0 else 1.9, 1.2 if dx < 0 else 4.3, 3)
        light = (255, int(190 + 50 * glow), int(60 + 50 * glow))
        flesh = (150, 50, 0)
        feats = [[(cx + side * rad * 0.48, cy - rad * 0.02), (cx + side * rad * 0.14, cy - rad * 0.02),
                  (cx + side * rad * 0.3, cy - rad * 0.36)] for side in (-1, 1)]
        feats.append([(cx - rad * 0.08, cy + rad * 0.12), (cx + rad * 0.08, cy + rad * 0.12), (cx, cy + rad * 0.02)])
        for f in feats:
            pygame.draw.polygon(screen, flesh, f, max(3, rad // 18))
            pygame.draw.polygon(screen, light, f)
        mouth = [(cx - rad * 0.58, cy + rad * 0.22)]
        for k in range(1, 9):
            x = cx - rad * 0.58 + k * rad * 1.16 / 9
            y = cy + rad * 0.22 + rad * 0.32 * np.sin(np.pi * k / 9)
            mouth.append((x, y - (rad * 0.1 if k % 3 == 0 else 0)))
        mouth.append((cx + rad * 0.58, cy + rad * 0.22))
        mouth += [(cx + rad * 0.3, cy + rad * 0.34), (cx, cy + rad * 0.3), (cx - rad * 0.3, cy + rad * 0.34)]
        pygame.draw.polygon(screen, flesh, mouth, max(3, rad // 18))
        pygame.draw.polygon(screen, light, mouth)

    def _bat(self, screen, x, y, s, flap):
        w, h = 46 * s, 16 * s * (0.5 + 0.5 * abs(flap))
        pts = [(x, y), (x - w * 0.5, y - h), (x - w, y + h * 0.2), (x - w * 0.6, y + h * 0.2), (x - w * 0.3, y + h * 0.6),
               (x, y + h * 0.3), (x + w * 0.3, y + h * 0.6), (x + w * 0.6, y + h * 0.2), (x + w, y + h * 0.2), (x + w * 0.5, y - h)]
        pygame.draw.polygon(screen, (6, 3, 10), pts)

    def draw(self, screen, t):
        W, H = self.W, self.H
        screen.blit(self.bg, (0, 0))
        for ph, sp, yy, sc in self.bats:
            x = ((t * sp + ph) % 1.4 - 0.2) * W
            self._bat(screen, x, H * yy + 12 * np.sin(t * 2 + ph), sc * H / 540, np.sin(t * 14 + ph * 3))
        glow = 0.6 + 0.25 * np.sin(t * 7.3) + 0.15 * np.sin(t * 17.1)
        rad = int(H * 0.2)
        self._pumpkin(screen, W // 2, int(H * 0.62 + np.sin(t * 1.6) * H * 0.008), rad, max(0.0, min(1.0, glow)))
        title = render_text(self.f_title, self.title, (255, 122, 26))
        shadow = render_text(self.f_title, self.title, (60, 20, 0))
        screen.blit(shadow, (W // 2 - title.get_width() // 2 + 4, int(H * 0.1) + 5))
        screen.blit(title, (W // 2 - title.get_width() // 2, int(H * 0.1)))
        sub = render_text(self.f_sub, self.sub, (230, 220, 245))
        sub.set_alpha(int(150 + 100 * np.sin(t * 1.8)))
        screen.blit(sub, (W // 2 - sub.get_width() // 2, int(H * 0.1) + title.get_height() + 8))


# --------------------------------------------------------------------------- app
