# 👻 Scare-TV

Plug your laptop into the TV. A webcam watches and, when **a person** walks by, the TV launches a full-screen jump scare with video and sound.

Detection is done by **YOLO11n-pose**, an open-weight vision model running 100% on your computer. It only reacts to people: cats, curtains or a change in the light won't set it off. Because it's a *pose* model, it also knows **where their eyes, nose and shoulders are**. Camera frames are never saved and never leave the computer.

The app speaks **Spanish and English** (`APP_LANG=es` / `APP_LANG=en`): the pumpkin, the voices, the polaroid and the scares with text follow the chosen language.

## 🩸 Live scares: with their own face

The scare people scream at most isn't a monster. It's **their own reflection**. The TV turns into a mirror (the live webcam, flipped), the picture slowly darkens and pushes in on their face… and something happens to it:

| Scare | What happens to the person |
|---|---|
| **Black eyes** | Their eyes slowly fill with black, veins spreading out. *"I see you."* |
| **Faceless** | Their face smooths over into blank skin… then a mouth full of teeth tears open. |
| **Behind you** | A pale girl with black hair peeks out next to their shoulder. *"Don't turn around."* |
| **Melt** | Their face starts dripping downwards and their eyes go hollow. |
| **Grin** | An ear-to-ear grin that isn't theirs spreads across their face. *"Smile for me."* |
| **Double** | Their reflection lags behind, pale and black-eyed… and creeps closer. |

After 2.6 s of tension comes the hit: a lunge into their face, shake, red flash and a scream. At the end the TV shows them **a polaroid of their own scared face**, which is where the laughter starts. That photo is **not saved** (only with `--save-reactions`, and then ask people first).

By default 80% of scares are live and the rest come from `media/` (`--live-chance` changes it). It never repeats an effect until it has used them all.

**Voices:** on a Mac, the first run records a few lines with the system voice (`say`) and turns them into a demon, a whisper in your ear, a broken child, or a high-pitched child speaking very slowly (*"Don't… turn… around…"*). They are cached in `media/voices/`. With an ElevenLabs account you can get far more realistic voices and screams: `make voices-elevenlabs` (asks for your key, never stores it).

**Sound:** all audio is synthesized in code (44.1 kHz stereo): formant-filtered human screams, crying, a distant ghostly wail, shrieks, stabbing violins, dissonant clusters that rise in tension, sub-bass hits, a detuned music box and cathedral reverb, with a reversed swell that rises right into the scare.

While it waits, the TV shows a **friendly pumpkin** saying *"Happy Halloween! come closer… I have treats for you"*. It's the bait: people walk up to look at it, right in front of the camera… and then the scare hits.

It ships with **20 original scares** in `media/`, generated from code (`make scares`): no frame or sound comes from a movie. See `media/_catalog_en.jpg` and `media/_catalog_es.jpg`.

## 🧟 Scare-TV 2: realistic faces

`make realistic` runs **SD-Turbo** (open weights, on your Mac) to imagine ten realistic horror portraits. YOLO-pose then checks each one: only photos with a clear head and shoulders are kept, and those get possessed (black eyes, gaping mouth) and turned into a scare with a flashlight sweep, a hit and a scream. If a photo has no usable face, it imagines it again. `make run2` starts the TV with these scares plus the live ones.

## 📱 Phone demo (nothing to install)

`web/` is a version of the haunted mirror that runs **in a phone browser**: the face model (MediaPipe Face Mesh, open weights) ships with the page and no image is uploaded. With no camera, it shows a classic scare instead.

- Try it locally: `make web` (opens http://localhost:8010)
- Try it on your phone without deploying: `make mobile` (temporary https link + QR code)
- Publish it for free on Render: *New → Blueprint* and pick this repository (it uses `render.yaml`). Phone cameras need https, and Render provides it.

## 📊 The night log and the jump-o-meter

Every scare is written to a local database (`data/scare_tv.sqlite3`), **numbers only**: which scare, whether a face was visible, how far they jumped, whether they fled out of frame, and how long after they arrived. Closing Scare-TV (ESC) writes `logs/summary_<date>.md`, a table comparing live and classic scares.

The **jump-o-meter** uses the same pose model. It compares where the face was just before the hit with where it is over the next 1.5 seconds, in eye-distances (so distance from the camera doesn't matter). It shows on the polaroid as a 0–10 score. Press **F** if the last scare was a false alarm. `make summary` prints the last night, which is also served at http://localhost:8010/api/night/summary by `make web`. `ARGS=--no-log` turns logging off.

## Run it in 5 minutes (Mac)

```bash
cd scare-tv
make install              # first time takes a while (Poetry installs PyTorch for YOLO)
make displays             # find the TV's number (usually 1)
make run SCREEN=1         # start scaring
```

1. Connect the TV over HDMI and set it as an **extended display** (not mirrored) in *System Settings → Displays*.
2. The first time, macOS asks for **camera** permission for Terminal. Allow it.
3. With `make try` you see the camera and an orange box on every detected person. Press **D** to hide it and leave only the pumpkin.
4. **SPACE** tests a scare. **ESC** turns everything off.

Plain `make` lists every command:

| Command | What it does |
|---|---|
| `make run` | The haunted TV. `SCREEN=1` for the TV, `APP_LANG=en` for English. |
| `make try` | Windowed, showing what the camera detects (to aim it). |
| `make realistic` / `make run2` | Scare-TV 2: imagine the realistic faces / start with them. |
| `make web` / `make mobile` | The mirror in the browser / on your phone with a QR code. |
| `make voices` | Rebuild the live-scare voices. |
| `make scares` | Rebuild the 20 classic scares (`ARGS="05 16"` for some, `ARGS=--sounds` for sounds only). |
| `make summary` | Summary of the last night. |
| `make test` / `make lint` | Tests / code style. |

## Keys

| Key | What it does |
|---|---|
| SPACE | Test scare |
| L | LIVE scare (with the face of whoever is in front) |
| F | The last scare was a false alarm (for the log) |
| N | Next scare from the folder |
| D | Show or hide the camera and the detection |
| M | Mute |
| ESC / Q | Quit |

## Useful options

Any option goes through `ARGS`:

```bash
make run SCREEN=1 ARGS="--live-chance 1"        # every scare is live, with their face
make run SCREEN=1 ARGS="--no-reaction"          # skip the polaroid at the end
make run SCREEN=1 ARGS="--mirror-chance 0.3"    # 30% of the time: classic MIRROR MODE
make run SCREEN=1 ARGS="--idle black"           # black screen instead of the pumpkin
make run SCREEN=1 ARGS="--idle photo.jpg"       # or an "innocent" photo of yours
make run SCREEN=1 ARGS="--cooldown 20"          # at least 20 s between scares
make run SCREEN=1 ARGS="--order sequence"       # scares in order, 01 to 20
make run ARGS="--detector motion"               # no YOLO: any movement triggers it
```

**Mirror mode 🪞:** the TV shows the person live, like a mirror. A translucent ghost slowly appears behind their shoulder… and then the scare hits.

Other settings: `--conf` (0.5 by default; raise it if it fires for no reason), `--frames` (how many consecutive frames must see someone), `--rearm` (seconds with nobody before re-arming), `--volume`, `--camera 1` (another webcam).

## Your own scares

Drop any `.mp4`, `.mov`, `.gif`, `.png` or `.jpg` into `media/`. For the sound:

- A sound with the same name as the video (`my_scare.mp4` + `my_scare.wav`) goes with it.
- If your video already has audio and `ffmpeg` is installed (`brew install ffmpeg`), it is extracted automatically.
- Otherwise a random sound from the folder is used.

Files starting with `_` are ignored. Only use material you have the rights to.

## The 20 classic scares

01 The Smile · 02 The Scream · 03 Eyes in the Dark · 04 The Hands · 05 The Shadow · 06 It's Behind You · 07 Glitch Face · 08 The Crack · 09 Dripping · 10 The Spider · 11 Dead Channel · 12 The Eye · 13 Sewn Mouth · 14 On the Ceiling · 15 A Thousand Smiles · 16 The Skull (Day of the Dead) · 17 The Bite · 18 I See You · 19 Flatline · 20 The Flashlight

The two scares with text have a Spanish and an English version (*"IT'S BEHIND YOU"* / *"ESTÁ DETRÁS DE TI"*, *"I SEE YOU"* / *"TE ESTOY VIENDO"*), picked by the app language.

## How the code is organized

Hexagonal architecture with CQRS, Django + Django REST Framework and Poetry:

```
domain/          entities (Night, Arrival, ScareEvent), pure rules (face geometry, jump-o-meter,
                 night summary, which faces can be possessed) and the ports (abstract repositories and services)
application/     commands/  start_night · record_arrival · record_scare · mark_false_alarm · finish_night ·
                            prepare_voices · generate_realistic_scares
                 queries/   get_night_summary · list_night_scares
infrastructure/  adapters: YOLO-pose, OpenCV possessions, voices with `say`, SD-Turbo, synthesized audio,
                 Django and file repositories, the TV (pygame), the DRF API and the manage.py commands
core/            Django settings and urls
tests/           domain · application · infrastructure
```

## Tests

```bash
make test        # no TV or webcam needed
```

They check that all 20 scares have their sound in each language, that scares with text follow the language, that your own files are picked up, that the random order never repeats, the motion detector, that **YOLO sees people but not the drawn ghosts or an empty room**, a full run with a video acting as the camera, that **each of the 6 live scares** really changes the picture during the build-up and the hit, that black eyes darken exactly the eyes, that the audio hit lands when the picture jumps, the possessed voices, a full live scare with YOLO-pose from start to finish, the commands and queries against the database, the API, and the whole of Scare-TV 2 (detection, possession, video and sound) with a photo standing in for SD-Turbo.

## Warning

The scares have sudden movement and some quick changes in light. Don't use them on people with photosensitive epilepsy, heart conditions, small children, or anyone who won't take it with a sense of humor. 😉
