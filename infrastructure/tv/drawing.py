"""pygame drawing helpers: text in the Creepster font, full-screen scaling, OpenCV to pygame."""
import cv2
import pygame
from django.conf import settings


def render_text(font, text, color):
    """Text with clean transparency. Renders white on black and uses that as the alpha channel: avoids a bug
    in some pygame-ce/SDL_ttf versions on Mac that draws a box over the last letters."""
    if hasattr(font, "render_to"):          # pygame.freetype: does not use SDL_ttf
        surf, _ = font.render(text, fgcolor=tuple(color[:3]))
        return surf.convert_alpha() if pygame.display.get_surface() else surf
    mask = font.render(text, True, (255, 255, 255), (0, 0, 0))
    surf = pygame.Surface(mask.get_size(), pygame.SRCALPHA)
    surf.fill(tuple(color[:3]) + (255,))
    alpha = pygame.surfarray.pixels_alpha(surf)
    alpha[:] = pygame.surfarray.array3d(mask)[:, :, 0]
    del alpha
    return surf


def load_font(px):
    """Creepster through FreeType (avoids the SDL_ttf bug on Mac); falls back to Arial."""
    path = str(settings.SCARE_TV["ASSETS_DIR"] / "Creepster-Regular.ttf")
    try:
        import pygame.freetype as ft

        ft.init()
        return ft.Font(path, px)
    except (ImportError, NotImplementedError, AttributeError, FileNotFoundError, OSError):
        try:
            return pygame.font.Font(path, px)
        except (FileNotFoundError, OSError):
            return pygame.font.SysFont("Arial", px, bold=True)


def cover(surface, size):
    """Scales to fill the whole screen without distortion (cropping the edges)."""
    sw, sh = surface.get_size()
    W, H = size
    k = max(W / sw, H / sh)
    s = pygame.transform.smoothscale(surface, (int(sw * k) + 1, int(sh * k) + 1))
    return s, ((W - s.get_width()) // 2, (H - s.get_height()) // 2)


def cv_to_surface(frame_bgr):
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return pygame.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), "RGB")


# --------------------------------------------------------------------------- calabaza cebo
