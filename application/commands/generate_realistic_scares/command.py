import random

from domain.rules.realistic_scares import MAX_TRIES, SCARES, STYLE, VERSION


class GenerateRealisticScaresCommand:
    """Scare-TV 2: one model imagines realistic horror faces and the other one possesses them.

    For each description the image model imagines a photo; the pose model looks for a face that can be
    reliably possessed (head and shoulders); if there is none, it imagines again (up to MAX_TRIES times).
    The chosen face is possessed (black eyes, open mouth) and turned into a scare with video and sound.
    Photos without a clear face are left out: better 8 good ones than 10 with textures.
    """

    def __init__(self, imagination_service, media_service, possession_service, log=print, rng=None):
        self.imagination = imagination_service
        self.media = media_service
        self.possession = possession_service
        self.log = log
        self.rng = rng or random.Random()

    def execute(self, dto):
        folder = dto.folder
        if not dto.build_only:
            regenerate = dto.again or self.media.version(folder) != VERSION
            for i, (name, prompt, _) in enumerate(SCARES):
                if not regenerate and self.media.has_photo(folder, name):
                    continue
                self._imagine_one(folder, i, name, prompt, fresh_seeds=dto.again)
            self.media.set_version(folder, VERSION)
        faces = self.media.faces(folder)
        built = []
        for i, (name, _, kind) in enumerate(SCARES):
            if not faces.get(name):
                continue                                   # no possessed face, no scare
            stem = f"real_{i + 1:02d}_{name}"
            self.media.build_scare(folder, stem, self.media.load_photo(folder, name), kind, seed=i, focus=faces[name])
            built.append(stem)
            self.log(f"  scare ready: {stem}")
        self.media.finish(folder, built)
        return built

    def _imagine_one(self, folder, i, name, prompt, fresh_seeds):
        best = None
        for k in range(MAX_TRIES):
            seed = self.rng.randrange(1 << 30) if fresh_seeds else 666 + i * 31 + k * 7
            raw = self.imagination.imagine(prompt + STYLE, seed)
            face = self.media.find_face(raw)
            size = face.d if face else 0.0
            if best is None or size > best[2]:
                possessed = self.possession.possess_photo(raw, face) if face else raw
                focus = [float(face.center[0] / raw.shape[1]), float(face.center[1] / raw.shape[0]), float(face.d / raw.shape[1])] if face else None
                best = (raw, possessed, size, focus)
            if size and k >= 1:                            # we have a good face (and tried at least two)
                break
        self.media.save_photos(folder, name, best[0], best[1], best[3])
        self.log(f"  imagined {i + 1}/{len(SCARES)}: {name}{'  (face possessed)' if best[2] else '  (no clear face: will not be used)'}")
        return best
