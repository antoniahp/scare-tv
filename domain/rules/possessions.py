"""The live possessions: what happens to people, how long the build-up lasts and how long the hit."""

EFFECTS = ["black_eyes", "faceless", "behind_you", "melt", "grin", "double"]
PRE, POST = 2.6, 2.4         # seconds of build-up and of scare (the audio tracks are cut the same way)
WORK = (640, 360)            # working resolution (the TV scales it up): fast even without a GPU

TEXTS = {
    "black_eyes": ("TE VEO", "I SEE YOU"),
    "faceless": ("¿DÓNDE ESTÁ TU CARA?", "WHERE IS YOUR FACE?"),
    "behind_you": ("NO TE GIRES", "DON'T TURN AROUND"),
    "melt": ("TE ESTÁS DESHACIENDO", "YOU'RE MELTING"),
    "grin": ("SONRÍE", "SMILE"),
    "double": ("¿CUÁL DE LOS DOS ERES TÚ?", "WHICH ONE IS YOU?"),
}


def text_for(effect, lang):
    return TEXTS[effect][0 if lang == "es" else 1]
