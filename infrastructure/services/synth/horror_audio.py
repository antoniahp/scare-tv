"""
horror_audio.py — horror sound design made from code (nobody's samples).

Formant screams, "stabbing" violins, dissonant clusters rising in tension, sub-bass hits,
cathedral reverb, a reversed swell before the scare and a demonic voice built from any voice
(the Mac's own with `say`, or one you record).

Everything is 44.1 kHz stereo. Used by the procedural scares (the 20 classics) and by the TV
(the live-scare voices and tracks).
"""
import wave

import numpy as np
from scipy import signal

SR = 44100
rng = np.random.default_rng(666)


# ------------------------------------------------------------------ basics
def tt(sec, sr=SR):
    return np.arange(int(sec * sr)) / sr


def noise(sec):
    return rng.normal(0, 1, int(sec * SR))


def osc_saw(freq, n):
    ph = np.cumsum(np.broadcast_to(np.asarray(freq, float), (n,)) / SR)
    return 2 * (ph % 1) - 1


def osc_sin(freq, n):
    ph = np.cumsum(np.broadcast_to(np.asarray(freq, float), (n,)) / SR)
    return np.sin(2 * np.pi * ph)


def bp(x, lo, hi, order=2, sr=SR):
    hi = min(hi, sr / 2 * 0.98)
    sos = signal.butter(order, [lo, hi], btype="band", fs=sr, output="sos")
    return signal.sosfilt(sos, x)


def lp(x, f, order=2, sr=SR):
    return signal.sosfilt(signal.butter(order, min(f, sr / 2 * 0.98), fs=sr, output="sos"), x)


def hp(x, f, order=2, sr=SR):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=sr, output="sos"), x)


def adsr(n, a=0.01, r=0.2):
    e = np.ones(n)
    ai, ri = min(n, int(a * SR)), min(n, int(r * SR))
    if ai:
        e[:ai] = np.linspace(0, 1, ai) ** 2
    if ri:
        e[-ri:] *= np.linspace(1, 0, ri) ** 1.5
    return e


def norm(x, peak=0.95):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def at(total, sec, x):
    """Places x (mono or stereo) at second `sec` of a track `total` seconds long."""
    x = np.asarray(x, float)
    shape = (int(total * SR),) + x.shape[1:]
    out = np.zeros(shape)
    i = int(sec * SR)
    if i < len(out):
        out[i:i + len(x)] += x[: len(out) - i]
    return out


def stereo(x, width=0.012):
    """Mono → stereo with a little width (a different delay in each ear)."""
    if x.ndim == 2:
        return x
    d = int(width * SR)
    r = np.concatenate([np.zeros(d), x])[: len(x)]
    return np.stack([x, 0.85 * x + 0.15 * r], axis=1)


# ------------------------------------------------------------------ space
def reverb(x, t60=2.6, wet=0.35, tone=5000, pre=0.02):
    """Convolution reverb with a synthetic impulse response (decaying noise)."""
    n = int(t60 * SR)
    t = np.arange(n) / SR
    out = []
    xs = x if x.ndim == 2 else x[:, None]
    for ch in range(xs.shape[1]):
        ir = lp(rng.normal(0, 1, n), tone) * np.exp(-6.9 * t / t60)
        ir = np.concatenate([np.zeros(int(pre * SR)), ir])
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        out.append(signal.fftconvolve(xs[:, ch], ir)[: len(xs)])
    w = np.stack(out, axis=1)
    if x.ndim == 1:
        w = w[:, 0]
    return (1 - wet) * x + wet * w * 1.6


def reverse_swell(sec=1.2, hit=None):
    """The 'shhhhOOOP' rising right before the scare: the reverb tail of a hit, reversed."""
    hit = hit if hit is not None else lp(noise(0.25), 6000) * np.exp(-tt(0.25) * 12)
    tail = reverb(np.concatenate([hit, np.zeros(int(sec * SR))]), t60=sec * 1.5, wet=1.0)[: int(sec * SR)]
    return norm(tail[::-1]) * np.linspace(0.2, 1, int(sec * SR)) ** 2


# ------------------------------------------------------------------ instruments of fear
def sub_boom(sec=1.6, f0=62, f1=26):
    n = int(sec * SR)
    t = tt(sec)
    f = f1 + (f0 - f1) * np.exp(-t * 3)
    body = osc_sin(f, n) * np.exp(-t * 2.2)
    crack = hp(noise(sec), 800) * np.exp(-t * 35)
    return np.tanh(2.2 * body + 0.5 * crack)


def strings_stab(sec=1.5, base=1900, voices=5, rate=6.5):
    """Violins that 'stab': high saws in a chromatic cluster, repeated dry attacks."""
    n = int(sec * SR)
    t = tt(sec)
    out = np.zeros(n)
    for v in range(voices):
        f = base * 2 ** (v / 12 + rng.normal(0, 0.008)) * (1 + 0.012 * np.sin(2 * np.pi * (6 + v) * t))
        f *= 1 + 0.06 * t / sec          # upward glissando
        out += osc_saw(f, n) / voices
    stabs = (((t * rate) % 1) < 0.55) * np.exp(-((t * rate) % 1) * 3.5)
    bow = bp(noise(sec), 3000, 9000) * 0.05
    x = bp(out + bow, 900, 9000) * stabs
    return np.tanh(2.0 * x)


def cluster_rise(sec=2.5, lo=110, voices=9, rise=0.5):
    """Tension: a dissonant cluster of low strings that rises and grows… and cuts off suddenly."""
    n = int(sec * SR)
    t = tt(sec)
    out = np.zeros(n)
    for v in range(voices):
        f = lo * 2 ** (v / 12) * 2 ** (rise * (t / sec) ** 2) * (1 + 0.004 * np.sin(2 * np.pi * (0.3 + 0.1 * v) * t))
        out += osc_saw(f, n) * (1 + 0.3 * np.sin(2 * np.pi * (4 + v * 0.7) * t))
    k = (t / sec) ** 2                  # the filter opens up: from dark to shrill
    x = (1 - k) * lp(out, 350) + k * lp(out, 5000)
    return np.tanh(1.4 * x / voices * 3) * (t / sec) ** 1.6


def drone(sec, base=41):
    """Low drone with beating and wind: the 'something is wrong here' sound."""
    n = int(sec * SR)
    t = tt(sec)
    x = sum(osc_saw(base * m * (1 + 0.002 * np.sin(2 * np.pi * 0.11 * t * (k + 1))), n) / (k + 1)
            for k, m in enumerate((1, 1.006, 1.498, 2.013, 2.997)))
    x = lp(x, 400) * 0.6
    wind = bp(noise(sec), 300, 1400) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.17 * t) ** 2) * 0.25
    return (x + wind) * adsr(n, 0.8, 0.3)


def scream(sec=1.8, f_peak=820, f_start=420, voices=3, vowel="a"):
    """Synthetic human scream: glottal pulse with jitter and 'roughness' + vowel formants + saturation."""
    n = int(sec * SR)
    t = tt(sec)
    F = {"a": [(900, 1.0, 9), (1350, 0.8, 10), (2900, 0.5, 14), (3800, 0.3, 16)],
         "i": [(400, 0.8, 8), (2400, 1.0, 12), (3100, 0.7, 14), (3900, 0.3, 16)],
         "o": [(600, 1.0, 8), (950, 0.8, 9), (2700, 0.35, 14), (3600, 0.2, 16)]}[vowel]
    total = np.zeros(n)
    for v in range(voices):
        det = 1 + (v - (voices - 1) / 2) * 0.035
        contour = f_start + (f_peak - f_start) * (1 - np.exp(-t * 14))
        contour *= 1 - 0.12 * (t / sec) ** 2                     # it breaks at the end
        jitter = 1 + 0.012 * np.cumsum(rng.normal(0, 1, n)) / np.sqrt(SR) * 8
        vib = 1 + 0.03 * np.sin(2 * np.pi * (6.3 + v) * t + v)
        f0 = contour * det * vib * np.clip(jitter, 0.9, 1.1)
        src = osc_saw(f0, n) + 0.6 * osc_saw(f0 * 0.5, n) * (0.5 + 0.5 * np.sin(2 * np.pi * 71 * t))  # subharmonic = roughness
        src += 0.1 * noise(sec)
        x = sum(g * bp(src, f * (1 - 1 / (2 * q)), f * (1 + 1 / (2 * q)), 2) for f, g, q in F)
        total += np.roll(x, int(v * 0.011 * SR))
    total = np.tanh(2.0 * norm(total))
    return total * adsr(n, 0.04, min(0.5, sec * 0.35))


def heartbeat(sec, bpm=80):
    n = int(sec * SR)
    out = np.zeros(n)
    th = tt(0.22)
    thump = osc_sin(48 + 20 * np.exp(-th * 30), len(th)) * np.exp(-th * 22)
    x = 0.0
    while x < sec - 0.3:
        for off, g in ((0, 1.0), (0.24, 0.65)):
            i = int((x + off) * SR)
            out[i:i + len(thump)] += g * thump[: n - i]
        x += 60 / bpm
    return np.tanh(1.6 * out)


def music_box(sec=3.0, slow=0.0, notes=(76, 79, 81, 79, 76, 72, 74, 71, 76, 75), step=0.32):
    """Out-of-tune music box (an original minor-key melody) slowing down."""
    n = int(sec * SR)
    out = np.zeros(n)
    x = 0.0
    k = 0
    while x < sec - 0.2:
        m = notes[k % len(notes)]
        f = 440 * 2 ** ((m - 69) / 12) * (1 + rng.normal(0, 0.006))
        th = tt(0.9)
        tone = sum(osc_sin(f * r, len(th)) * np.exp(-th * (3 + 2 * r)) / (1 + i) for i, r in enumerate((1, 2.0, 3.98, 5.4)))
        out += at(sec, x, tone)[:n]
        x += step * (1 + slow * (x / sec) ** 2)
        k += 1
    return out * 0.4


def whisper_noise(sec, rate=3.3):
    t = tt(sec)
    am = np.clip(np.sin(2 * np.pi * rate * t) * np.sin(2 * np.pi * 0.9 * t + 1), 0, 1) ** 1.5
    return bp(noise(sec), 1800, 8000) * am * 0.5


def creak(sec):
    n = int(sec * SR)
    t = tt(sec)
    f = 28 + 22 * np.sin(2 * np.pi * 0.6 * t) + 8 * rng.random(n)
    return bp(osc_saw(f, n), 250, 2600) * 0.8


def glitch_burst(sec=0.6):
    n = int(sec * SR)
    x = osc_saw(np.repeat(rng.uniform(80, 1600, n // 600 + 1), 600)[:n], n)
    return np.tanh(3 * x) * 0.5 * (rng.random(n) > 0.15)


_VOWELS = {"a": [(850, 1.0, 8), (1250, 0.7, 10), (2800, 0.4, 14)],
           "u": [(330, 1.0, 7), (850, 0.5, 9), (2300, 0.25, 14)],
           "o": [(550, 1.0, 8), (900, 0.7, 9), (2600, 0.3, 14)],
           "i": [(350, 0.8, 8), (2300, 1.0, 12), (3000, 0.6, 14)]}


def _voiced(f0, vowel="a", breath=0.15, rough=0.0):
    """A synthetic human voice: glottal pulse (f0 may vary over time) + breath, through formants."""
    f0 = np.asarray(f0, float)
    n = len(f0)
    t = np.arange(n) / SR
    src = osc_saw(f0, n) + rough * osc_saw(f0 * 0.5, n) * (0.5 + 0.5 * np.sin(2 * np.pi * 63 * t))
    src += breath * rng.normal(0, 1, n)
    return sum(g * bp(src, f * (1 - 1 / (2 * q)), f * (1 + 1 / (2 * q))) for f, g, q in _VOWELS[vowel])


def crying(sec, f0=300.0, child=False):
    """Crying: broken, rising sobs, a long wail that cracks and a choked breath in. And again."""
    n = int(sec * SR)
    out = np.zeros(n)
    base = f0 * (1.5 if child else 1.0)
    x = rng.uniform(0, 0.3)
    while x < sec - 0.3:
        for k in range(int(rng.integers(2, 5))):                      # "uh-uh-uh"
            d = rng.uniform(0.09, 0.15)
            m = int(d * SR)
            f = base * (1 + 0.08 * k) * (1 + 0.04 * np.sin(np.linspace(0, np.pi, m)))
            out += at(sec, x, _voiced(f, "u", 0.35) * np.hanning(m) ** 0.7)[:n]
            x += d + rng.uniform(0.05, 0.11)
        d = rng.uniform(0.55, 1.1)                                    # a falling, trembling "huuuuuh…"
        m = int(d * SR)
        tt_ = np.linspace(0, 1, m)
        f = base * 1.35 * (1 - 0.35 * tt_) * (1 + 0.035 * np.sin(2 * np.pi * 7.5 * tt_ * d))
        wail = _voiced(f, "a" if rng.random() < 0.5 else "u", 0.25, 0.3) * np.sin(np.pi * tt_) ** 0.6
        out += at(sec, x, wail)[:n]
        x += d + 0.08
        g = rng.uniform(0.25, 0.4)                                    # the broken breath in
        gasp = bp(rng.normal(0, 1, int(g * SR)), 900, 4500) * np.linspace(0.2, 1, int(g * SR)) ** 2 * 0.22
        out += at(sec, x, gasp)[:n]
        x += g + rng.uniform(0.2, 0.6)
    return np.tanh(1.5 * norm(out)) * 0.9


def wail(sec, f0=520.0):
    """Ghostly wail: a high, distant 'oooooh' rising and falling without a breath (two voices that don't match)."""
    n = int(sec * SR)
    t = tt(sec)
    out = np.zeros(n)
    for v, det in enumerate((1.0, 1.013)):
        f = f0 * det * (1 + 0.45 * np.sin(2 * np.pi * (0.22 + 0.05 * v) * t + v) ** 2) * (1 + 0.02 * np.sin(2 * np.pi * 5.5 * t))
        out += _voiced(f, "u", 0.12) * (0.55 + 0.45 * np.sin(2 * np.pi * 0.3 * t + v) ** 2)
    return reverb(norm(out) * adsr(n, 0.6, 0.6), t60=4.0, wet=0.6)


def shriek(sec=1.2, f_peak=1700):
    """Shrill shriek: high, harsh and merciless (for the hit)."""
    n = int(sec * SR)
    t = tt(sec)
    f = f_peak * (0.75 + 0.25 * (1 - np.exp(-t * 20))) * (1 + 0.05 * np.sin(2 * np.pi * 9 * t)) * (1 - 0.15 * (t / sec) ** 2)
    x = _voiced(f, "i", 0.2, 0.6) + 0.5 * _voiced(f * 1.06, "a", 0.2, 0.6)
    return np.tanh(3.5 * norm(x)) * adsr(n, 0.01, sec * 0.4)


# ------------------------------------------------------------------ the full scare
def jump_hit(sec=2.0, kind="scream"):
    """What plays at the moment of the scare: sub hit + scream/violins + reverb."""
    x = at(sec, 0, sub_boom(min(sec, 1.6)))
    if kind in ("scream", "both"):
        x += at(sec, 0.0, scream(sec * 0.9, f_peak=rng.uniform(720, 980), vowel=rng.choice(["a", "i"]))) * 0.9
    if kind in ("strings", "both"):
        x += at(sec, 0.0, strings_stab(sec * 0.85, base=rng.uniform(1700, 2300))) * 0.6
    if kind == "growl":
        g = scream(sec * 0.9, f_peak=140, f_start=90, voices=4, vowel="o")
        x += at(sec, 0, np.tanh(4 * g)) * 0.9
    x += at(sec, 0.04, shriek(min(1.3, sec * 0.6), f_peak=rng.uniform(1500, 2100))) * (0.55 if kind != "growl" else 0.35)
    return x


def master(x, t60=2.4, wet=0.3):
    """Reverb, stereo, gentle compression and normalization. Returns float stereo."""
    x = stereo(np.asarray(x, float))
    x = reverb(x, t60=t60, wet=wet)
    x = np.tanh(1.3 * norm(x)) / np.tanh(1.3)
    x = norm(x, 0.97)
    fade = int(0.08 * SR)
    x[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return x


def live_track(effect, pre=2.6, post=2.4):
    """Soundtrack of a 'live' scare (with the victim's real face):
    `pre` seconds of tension, 0.15 s of silence and the hit at second `pre`."""
    T = pre + post
    t = tt(pre)
    if effect == "black_eyes":
        tension = drone(pre, 38) * 0.6 + cluster_rise(pre, 98) * 0.8 + wail(pre, 560) * 0.35
    elif effect == "faceless":
        tension = drone(pre, 38) * 0.5 + cluster_rise(pre, 98) * 0.6 + crying(pre, 260) * 0.55
    elif effect == "behind_you":            # a girl cries in the other room… and then speaks
        tension = drone(pre, 33) * 0.6 + heartbeat(pre, 100) * 0.6 + reverb(crying(pre, 330, child=True), t60=2.5, wet=0.7) * 0.5
    elif effect == "double":
        tension = music_box(pre, slow=0.8) + crying(pre, 300, child=True) * 0.3 + drone(pre, 44) * 0.3
    elif effect == "melt":
        tension = cluster_rise(pre, 70, rise=-0.4) * 0.8 + drone(pre, 30) * 0.4 + wail(pre, 430) * 0.4
    else:                       # grin
        tension = music_box(pre, slow=0.5, notes=(81, 80, 81, 77, 76, 75, 76, 72)) * 0.8 + wail(pre, 640) * 0.25
    tension = tension * np.where(t > pre - 0.15, 0, 1)          # the silence right before
    x = at(T, 0, tension)
    x += at(T, pre - 0.9, reverse_swell(0.9)) * 0.5
    kind = {"black_eyes": "scream", "faceless": "both", "behind_you": "scream", "double": "strings",
            "melt": "growl", "grin": "both"}.get(effect, "scream")
    x += at(T, pre, jump_hit(post, kind))
    return master(x)


# ------------------------------------------------------------------ voices
def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    dt = {1: np.uint8, 2: np.int16, 4: np.int32}[sw]
    x = np.frombuffer(raw, dt).astype(float)
    if sw == 1:
        x = (x - 128) / 128
    else:
        x /= float(np.iinfo(dt).max)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def write_wav(path, x, sr=SR):
    x = np.asarray(x, float)
    ch = 1 if x.ndim == 1 else x.shape[1]
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def resample(x, sr_in, sr_out=SR):
    if sr_in == sr_out:
        return x
    return signal.resample_poly(x, sr_out, sr_in)


def vocode_whisper(x, bands=12):
    """Turns a voice into a whisper: same band envelopes, but noise instead of vocal cords."""
    edges = np.geomspace(200, 9000, bands + 1)
    out = np.zeros(len(x))
    nz = rng.normal(0, 1, len(x))
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        envl = lp(np.abs(bp(x, lo, hi)), 40)
        out += bp(nz, lo, hi) * np.clip(envl, 0, None)
    return norm(out)


def stretch(x, factor):
    """Slower without changing the pitch (grain overlap). factor 1.8 = almost twice as slow."""
    g = int(0.06 * SR)
    hin = g // 4
    hout = int(hin * factor)
    win = np.hanning(g)
    k = max(1, (len(x) - g) // hin)
    out = np.zeros(k * hout + g)
    wsum = np.zeros_like(out)
    for i in range(k):
        out[i * hout:i * hout + g] += x[i * hin:i * hin + g] * win
        wsum[i * hout:i * hout + g] += win
    return out / np.maximum(wsum, 1e-3)


def add_pauses(x, extra=0.45):
    """A long silence between words. Like someone speaking very slowly… from very close."""
    hop = int(0.02 * SR)
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    if not len(e):
        return x
    quiet = e < 0.08 * e.max()
    out, i, last = [], 0, 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * 0.02 >= 0.06 and i > 0 and j < len(quiet):     # a gap between words
                cut = (i + j) // 2 * hop
                out += [x[last:cut], np.zeros(int(extra * SR))]
                last = cut
            i = j
        else:
            i += 1
    out.append(x[last:])
    return np.concatenate(out)


def demon_voice(x, sr, style="demon"):
    """The 'possessed' voice: low and slow + a whisper on top + metallic ring + cathedral reverb.
    style: 'demon' (low), 'whisper' (in your ear), 'child' (high and broken),
           'slow_child' (high, VERY slow, with long pauses and trembling: "Don't… turn… around…")."""
    x = resample(norm(np.asarray(x, float)), sr)
    n = len(x)
    if style == "slow_child":
        hi = signal.resample(x, int(n / 1.45))                     # higher
        slow = stretch(hi, 1.7)                                    # and very slow, while staying high
        slow = add_pauses(slow, 0.4)                               # with silences between words
        t = np.arange(len(slow)) / SR
        shaky = slow * (0.8 + 0.2 * np.sin(2 * np.pi * 5.2 * t))   # trembling voice, as if about to cry
        v = shaky + 0.3 * vocode_whisper(slow)
        v = stereo(np.concatenate([v, np.zeros(int(2.5 * SR))]), 0.0)
        v[:, 1] *= 0.55                                            # closer to one ear
        return master(v, t60=3.2, wet=0.45)
    if style == "whisper":
        w = vocode_whisper(x)
        v = 0.85 * w + 0.15 * x
        v = stereo(v, 0.0)
        v[:, 1] *= 0.35                           # right against the left ear
        return master(np.concatenate([v, np.zeros((int(1.2 * SR), 2))]), t60=1.4, wet=0.2)
    if style == "child":
        hi = signal.resample(x, int(n / 1.32))    # higher (and a little faster)
        crack = np.where(rng.random(len(hi)) > 0.002, 1, 0)
        crack = lp(crack.astype(float), 30)
        v = hi * np.clip(crack, 0.2, 1) + 0.25 * vocode_whisper(hi)
        return master(np.concatenate([v, np.zeros(int(2.0 * SR))]), t60=3.2, wet=0.45)
    low = signal.resample(x, int(n * 1.42))       # a bit more than a fourth lower, slower
    t = np.arange(len(low)) / SR
    ring = low * (0.75 + 0.25 * np.sin(2 * np.pi * 34 * t))
    low2 = signal.resample(x, int(n * 1.9))[: len(low)]
    low2 = np.pad(low2, (0, len(low) - len(low2)))
    wh = np.pad(vocode_whisper(x), (0, len(low) - n))
    v = np.tanh(2.2 * norm(ring)) + 0.55 * low2 + 0.4 * np.roll(wh, int(0.04 * SR))
    v = np.concatenate([v, np.zeros(int(2.5 * SR))])
    pre = reverb(np.concatenate([v[: int(0.8 * SR)], np.zeros(int(1.0 * SR))]), t60=1.6, wet=1.0)[::-1][-int(0.6 * SR):]
    v = np.concatenate([norm(pre) * 0.35, v])     # the echo arrives BEFORE the voice
    return master(v, t60=3.5, wet=0.42)
