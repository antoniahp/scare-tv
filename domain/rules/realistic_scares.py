"""
Scare-TV 2: which horror photos the image model imagines, and how we decide whether a face can be possessed.
No real people and no movie characters: only generic descriptions.
"""
JUMP = 2.0               # second of the hit in every realistic scare

STYLE = ", horror movie still, photorealistic, flash photography at night, dark background, creepy, looking straight at the camera"
SCARES = [  # (name, description, scream type). All head-and-shoulders faces looking at you, so YOLO-pose finds and possesses them
    ("pale_woman", "head and shoulders portrait of a pale thin woman with long wet black hair in a dark room", "scream"),
    ("old_man", "head and shoulders portrait of a gaunt old man with grey skin and sunken cheeks in a dark house", "growl"),
    ("girl", "head and shoulders portrait of a pale little girl with dark circles under her eyes in a dark bedroom", "strings"),
    ("grandmother", "head and shoulders portrait of an old woman in a black dress with grey skin, candlelight", "growl"),
    ("smiling_man", "head and shoulders portrait of a pale bald man with a wide smile standing in a dark doorway", "both"),
    ("drowned_woman", "head and shoulders portrait of a pale woman with wet tangled hair and grey lips in a dark bathroom", "scream"),
    ("boy", "head and shoulders portrait of a pale boy in old fashioned clothes in an abandoned hallway", "strings"),
    ("flashlight_man", "head and shoulders portrait of a thin pale man lit from below by a flashlight in a black hallway", "scream"),
    ("nurse", "head and shoulders portrait of a pale nurse in an abandoned hospital corridor at night", "both"),
    ("clown", "head and shoulders portrait of a pale sad clown with faded makeup in a dark room", "scream"),
]
VERSION = "3"            # if it changes, they are all imagined again
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
