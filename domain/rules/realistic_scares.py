"""
Scare-TV 2: which horror photos the image model imagines, and how we decide whether a face can be possessed.
No real people and no movie characters: only generic descriptions.
"""
JUMP = 2.0               # second of the hit in every realistic scare

STYLE = ", found footage horror photo, harsh camera flash, film grain, photorealistic, pitch black background, staring into the camera"
# Prompts are short on purpose: SD-Turbo's text encoder only reads ~77 tokens. The possession step adds the black eyes
# and the gaping mouth later, so the faces keep visible eyes here (YOLO-pose needs them to find the face).
SCARES = [  # (name, description, scream type). All head-and-shoulders faces looking at you, so YOLO-pose finds and possesses them
    ("pale_woman", "head and shoulders portrait of a ghostly woman, grey cracked skin, milky white eyes, long wet black hair hanging over her face", "scream"),
    ("old_man", "head and shoulders portrait of a corpse-like old man, sunken grey skin, hollow cheeks, cloudy white eyes, crooked rotten teeth", "growl"),
    ("girl", "head and shoulders portrait of a possessed little girl, deathly pale skin, dark veins on her cheeks, pale white eyes, cracked lips, dirty white dress", "strings"),
    ("grandmother", "head and shoulders portrait of a dead old woman in a black lace veil, waxy grey skin, milky eyes, lit by one candle", "growl"),
    ("smiling_man", "head and shoulders portrait of a pale bald man with an unnaturally wide grin full of teeth, bulging eyes, standing in a dark doorway", "both"),
    ("drowned_woman", "head and shoulders portrait of a drowned woman, bluish grey skin, wet tangled hair stuck to her face, white eyes, grey lips", "scream"),
    ("boy", "head and shoulders portrait of a ghost boy in old fashioned clothes, ash grey skin, dark sunken eyes, dust on his face, abandoned hallway", "strings"),
    ("flashlight_man", "head and shoulders portrait of a gaunt pale man lit from below by a flashlight, wide staring eyes, sweat, black hallway", "scream"),
    ("nurse", "head and shoulders portrait of a ghostly nurse, rotting grey skin, white eyes, stained old uniform, abandoned hospital corridor", "both"),
    ("clown", "head and shoulders portrait of a sinister clown, cracked white face paint, smeared dark lipstick, yellow rotten teeth", "scream"),
]
VERSION = "4"            # if it changes, they are all imagined again
MAX_TRIES = 5            # attempts to find a face that can be possessed


def plausible_face(face, kp, width):
    """Is this a well-found face? Nose between and below the eyes, a sensible size, and shoulders visible
    clearly BELOW the nose (in extreme close-ups the pose model invents shoulders at face height and
    misplaces the eyes)."""
    if face is None or not face.ok or not face.from_kp or kp is None or len(kp) < 7:
        return False
    shoulders = any(kp[j][2] > 0.3 and kp[j][1] > face.nose[1] + 1.2 * face.d for j in (5, 6))
    (ex0, ey0), (ex1, ey1) = face.eyes[0], face.eyes[1]
    nx, ny = face.nose
    d = face.d / width
    return shoulders and 0.035 < d < 0.4 and min(ex0, ex1) - face.d * 0.15 < nx < max(ex0, ex1) + face.d * 0.15 and ny > min(ey0, ey1)
