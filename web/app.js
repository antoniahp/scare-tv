/* Scare-TV · web mirror
 * The camera becomes a mirror. MediaPipe Face Mesh (open weights, Apache 2.0) runs inside the browser
 * and finds 468 points on your face; the possession is drawn on top of your real reflection.
 * No image, video or sound ever leaves the device. When a server is there (Render), the page sends it
 * anonymous numbers only: which scare ran and how far the face jumped, to compare with everyone else.
 */
"use strict";

const PRE = 2.6, POST = 2.4, WINDOW = 1.5;
const DEBUG = /[?&]debug/.test(location.search);           // ?debug shows what the camera and the model are doing          // same timeline as the TV version and its audio tracks
const EFFECTS = ["black_eyes", "behind_you", "grin", "faceless", "melt", "double"];

const I18N = {
  en: {
    tag: "Look into the mirror",
    lead: "Your camera becomes a mirror. An open-weight face model finds your eyes, your nose and your mouth… and then something happens to them.",
    start: "Look 👁️",
    fine: "Everything runs <b>inside your browser</b>. No photo or video ever leaves your device: only anonymous numbers (which scare, how far you jumped). Turn the sound <b>up</b>. Best on a phone, in a dim room.",
    cap: "Your scared face", again: "Again 👻", save: "Save photo",
    local: "This photo only exists on your phone. Only the jump score was counted, anonymously.",
    meter: (n) => `Jump-o-meter ${n}/10`, meterNone: "Jump-o-meter: you didn't even blink", blinked: "It struck while you blinked.",
    rank: (p) => `You jumped more than ${p}% of people`, first: "You're the first one tonight 👻",
    fallbackfine: "This is one of the 20 classic scares. The live one needs a camera: open this page on your phone.",
    retry: "Try the camera again",
    loading: "Waking the mirror… (downloading the face model, 10 MB)", noFace: "The face model isn't answering on this browser.", look: "Look into the mirror…", closer: "Come closer… I can't see your face",
    errDenied: "You said no to the camera. That's fine: here's a classic scare instead.",
    errNone: "I couldn't find a camera on this device. Here's a classic scare instead.",
    errInsecure: "The camera only works over https.", errModel: "The face model didn't load. Here's a classic scare instead.",
    texts: { black_eyes: "I SEE YOU", faceless: "WHERE IS YOUR FACE?", behind_you: "DON'T TURN AROUND",
             melt: "YOU'RE MELTING", grin: "SMILE", double: "WHICH ONE IS YOU?" },
    lines: { black_eyes: "I see you.", faceless: "Give me your face.", behind_you: "Don't turn around.",
             melt: "You're melting.", grin: "Smile for me.", double: "Which one of us is you?" },
    speech: "en-US",
  },
  es: {
    tag: "Mírate en el espejo",
    lead: "Tu cámara se convierte en un espejo. Un modelo de caras open-weight encuentra tus ojos, tu nariz y tu boca… y entonces les pasa algo.",
    start: "Mirar 👁️",
    fine: "Todo funciona <b>dentro de tu navegador</b>. Ninguna foto ni vídeo sale de tu dispositivo: solo números anónimos (qué susto y cuánto saltaste). Sube el <b>volumen</b>. Mejor en el móvil y con poca luz.",
    cap: "Tu cara de susto", again: "Otra vez 👻", save: "Guardar foto",
    local: "Esta foto solo existe en tu móvil. Solo se ha contado tu salto, de forma anónima.",
    meter: (n) => `Saltómetro ${n}/10`, meterNone: "Saltómetro: ni has pestañeado", blinked: "Atacó mientras parpadeabas.",
    rank: (p) => `Saltaste más que el ${p} % de la gente`, first: "Eres la primera víctima de la noche 👻",
    fallbackfine: "Este es uno de los 20 sustos clásicos. El de tu cara necesita cámara: abre esta página en el móvil.",
    retry: "Probar la cámara otra vez",
    loading: "Despertando al espejo… (bajando el modelo de caras, 10 MB)", noFace: "El modelo de caras no responde en este navegador.", look: "Mírate en el espejo…", closer: "Acércate… no veo tu cara",
    errDenied: "Has dicho que no a la cámara. No pasa nada: aquí tienes un susto clásico.",
    errNone: "No encuentro ninguna cámara en este dispositivo. Aquí tienes un susto clásico.",
    errInsecure: "La cámara solo funciona con https.", errModel: "El modelo de caras no ha cargado. Aquí tienes un susto clásico.",
    texts: { black_eyes: "TE VEO", faceless: "¿DÓNDE ESTÁ TU CARA?", behind_you: "NO TE GIRES",
             melt: "TE ESTÁS DESHACIENDO", grin: "SONRÍE", double: "¿CUÁL DE LOS DOS ERES TÚ?" },
    lines: { black_eyes: "Te veo.", faceless: "Dame tu cara.", behind_you: "No te gires.",
             melt: "Te estás deshaciendo.", grin: "Sonríe para mí.", double: "¿Cuál de los dos eres tú?" },
    speech: "es-ES",
  },
};

// ------------------------------------------------------------------ landmarks (MediaPipe Face Mesh indices)
const EYE_A = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7];
const EYE_B = [263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249];
const OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
              176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109];

const $ = (id) => document.getElementById(id);
const S = {
  lang: "en", phase: "intro", effect: null, effects: [], t0: 0, lm: null, lmT: 0, face: null, faceSince: 0, lastSeen: 0,
  sending: false, mesh: null, audio: null, buffers: {}, snap: null, flinch: null, buffer: [], frameN: 0, voiceSaid: false, hitDone: false,
};
const video = $("cam"), view = $("stage"), vctx = view.getContext("2d");
const world = document.createElement("canvas"), wctx = world.getContext("2d", { willReadFrequently: true });
const tmp = document.createElement("canvas"), tctx = tmp.getContext("2d", { willReadFrequently: true });
const tiny = document.createElement("canvas"); tiny.width = tiny.height = 14;
const tinyctx = tiny.getContext("2d", { willReadFrequently: true });

const tr = (k, ...a) => { const v = I18N[S.lang][k]; return typeof v === "function" ? v(...a) : v; };
const ease = (x) => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
const lerp = (a, b, k) => a + (b - a) * k;
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

// ------------------------------------------------------------------ language
function applyLang(l) {
  S.lang = I18N[l] ? l : "en";
  document.documentElement.lang = S.lang;
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = tr(el.dataset.t); });
  document.querySelectorAll("[data-html]").forEach((el) => { el.innerHTML = tr(el.dataset.html); });
  document.querySelectorAll(".langs button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.l === S.lang)));
  try { localStorage.setItem("stv-lang", S.lang); } catch (e) { /* private mode */ }
}
document.querySelectorAll(".langs button").forEach((b) => b.addEventListener("click", () => applyLang(b.dataset.l)));

// ------------------------------------------------------------------ the face, in world (mirrored video) pixels
function faceFrom(lm) {
  if (!lm) return null;
  const W = world.width, H = world.height;
  const P = (i) => [(1 - lm[i].x) * W, lm[i].y * H];
  const avg = (ids) => { let x = 0, y = 0; ids.forEach((i) => { const p = P(i); x += p[0]; y += p[1]; }); return [x / ids.length, y / ids.length]; };
  const ea = avg(EYE_A), eb = avg(EYE_B);
  const eyes = ea[0] < eb[0] ? [ea, eb] : [eb, ea];
  const d = Math.max(6, dist(ea, eb));
  const ex = [(eyes[1][0] - eyes[0][0]) / d, (eyes[1][1] - eyes[0][1]) / d];
  let ey = [-ex[1], ex[0]]; if (ey[1] < 0) ey = [-ey[0], -ey[1]];
  const mid = [(ea[0] + eb[0]) / 2, (ea[1] + eb[1]) / 2];
  const mouth = avg([13, 14]);
  const center = [(mid[0] + mouth[0]) / 2, (mid[1] + mouth[1]) / 2];
  const oval = OVAL.map(P);
  const xs = oval.map((p) => p[0]), ys = oval.map((p) => p[1]);
  return {
    P, d, ex, ey, mid, mouth, center, oval, eyeRings: [EYE_A.map(P), EYE_B.map(P)], eyes,
    angle: Math.atan2(ex[1], ex[0]), cornerA: P(61), cornerB: P(291), edgeA: P(234), edgeB: P(454),
    box: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)],
    headHalf: dist(P(234), P(454)) / 2,
  };
}

// ------------------------------------------------------------------ brushes
function polyPath(ctx, pts) { ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); }
function seeded(n) { let s = n * 9301 + 49297; return () => ((s = (s * 9301 + 49297) % 233280) / 233280); }

function blackEyes(ctx, f, a, veins = true) {
  if (a <= 0) return;
  ctx.save();
  f.eyeRings.forEach((ring) => {
    const c = ring.reduce((m, p) => [m[0] + p[0] / ring.length, m[1] + p[1] / ring.length], [0, 0]);
    const g = ctx.createRadialGradient(c[0], c[1], 0, c[0], c[1], f.d * 0.6);
    g.addColorStop(0, `rgba(0,0,0,${0.6 * a})`); g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g; ctx.fillRect(c[0] - f.d, c[1] - f.d, f.d * 2, f.d * 2);
    const k = 1 + 0.75 * a;
    polyPath(ctx, ring.map((p) => [c[0] + (p[0] - c[0]) * k, c[1] + (p[1] - c[1]) * (k + 0.35 * a)]));
    ctx.globalAlpha = Math.min(1, a * 1.4); ctx.fillStyle = "#020004"; ctx.shadowColor = "#000"; ctx.shadowBlur = f.d * 0.15;
    ctx.fill(); ctx.shadowBlur = 0; ctx.globalAlpha = 1;
    if (veins && a > 0.5) {
      const r = seeded(Math.round(c[0]));
      ctx.strokeStyle = "rgba(28,8,44,.85)"; ctx.lineWidth = Math.max(1, f.d / 38);
      for (let i = 0; i < 8; i++) {
        const ang = r() * Math.PI * 2, len = f.d * (0.3 + 0.45 * r()) * (a - 0.5) * 2;
        ctx.beginPath(); ctx.moveTo(c[0] + Math.cos(ang) * f.d * 0.22, c[1] + Math.sin(ang) * f.d * 0.18);
        ctx.quadraticCurveTo(c[0] + Math.cos(ang + 0.3) * (f.d * 0.25 + len * 0.6), c[1] + Math.sin(ang + 0.3) * (f.d * 0.25 + len * 0.6),
                             c[0] + Math.cos(ang) * (f.d * 0.22 + len), c[1] + Math.sin(ang) * (f.d * 0.18 + len));
        ctx.stroke();
      }
    }
    if (a > 0.85) { ctx.fillStyle = "rgba(230,30,40,.9)"; ctx.beginPath(); ctx.arc(c[0] + f.d * 0.05, c[1] - f.d * 0.04, Math.max(1.2, f.d * 0.03), 0, 7); ctx.fill(); }
  });
  ctx.restore();
}

function gapingMouth(ctx, f, a, teeth = true) {
  if (a <= 0) return;
  const c = [f.mouth[0] + f.ey[0] * f.d * 0.25 * a, f.mouth[1] + f.ey[1] * f.d * 0.25 * a];
  const rx = f.d * (0.32 + 0.3 * a), ry = f.d * (0.1 + 1.0 * a);
  ctx.save(); ctx.translate(c[0], c[1]); ctx.rotate(f.angle);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, Math.max(rx, ry) * 1.5);
  g.addColorStop(0, `rgba(0,0,0,${0.6 * a})`); g.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = g; ctx.fillRect(-rx * 2, -ry * 2, rx * 4, ry * 4);
  ctx.fillStyle = "#08000a"; ctx.beginPath(); ctx.ellipse(0, 0, rx, ry, 0, 0, 7); ctx.fill();
  if (teeth && a > 0.3) {
    ctx.fillStyle = "#c7d1d6"; const n = 7, w = rx / n * 0.8, h = f.d * 0.28 * a;
    for (let i = 0; i < n; i++) {
      const x = -rx * 0.8 + 1.6 * rx * (i + 0.5) / n, yy = ry * 0.92 * Math.sqrt(Math.max(0, 1 - (x / rx) ** 2));
      [[-yy, 1], [yy, -1]].forEach(([y0, s]) => { ctx.beginPath(); ctx.moveTo(x - w, y0); ctx.lineTo(x + w, y0); ctx.lineTo(x, y0 + s * h); ctx.fill(); });
    }
  }
  ctx.restore();
}

function grin(ctx, f, a) {
  if (a <= 0) return;
  const half = f.d * (0.3 + 0.95 * a), curve = f.d * (0.15 + 0.65 * a), thick = f.d * (0.06 + 0.3 * a);
  const at = (x, y) => [f.mouth[0] + f.ex[0] * x * half + f.ey[0] * y, f.mouth[1] + f.ex[1] * x * half + f.ey[1] * y];
  const up = (x) => -curve * x * x + thick * 0.2 * (1 - x * x), lo = (x) => -curve * x * x + thick * (1 - x * x);
  const pts = [];
  for (let i = 0; i <= 40; i++) { const x = -1 + i / 20; pts.push(at(x, up(x))); }
  for (let i = 40; i >= 0; i--) { const x = -1 + i / 20; pts.push(at(x, lo(x))); }
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,.8)"; ctx.shadowBlur = f.d * 0.18;
  polyPath(ctx, pts); ctx.globalAlpha = Math.min(1, a * 1.4); ctx.fillStyle = "#0a000c"; ctx.fill();
  ctx.shadowBlur = 0;
  if (a > 0.35) {
    ctx.fillStyle = "#b9c5c9";
    for (let k = 0; k < 16; k++) {
      const x = -0.9 + 1.8 * (k + 0.5) / 16, w = 0.9 / 16 * 0.9, h = (lo(x) - up(x)) * 0.45;
      [[up(x), 1], [lo(x), -1]].forEach(([y0, s]) => { polyPath(ctx, [at(x - w, y0), at(x + w, y0), at(x, y0 + s * h)]); ctx.fill(); });
    }
  }
  ctx.restore();
}

function faceless(ctx, f, a) {
  if (a <= 0) return;
  const [x0, y0, x1, y1] = f.box;
  tinyctx.drawImage(world, x0, y0, x1 - x0, y1 - y0, 0, 0, tiny.width, tiny.height);
  const px = tinyctx.getImageData(5, 6, 4, 4).data;
  let r = 0, g = 0, b = 0; for (let i = 0; i < px.length; i += 4) { r += px[i]; g += px[i + 1]; b += px[i + 2]; }
  const n = px.length / 4;
  ctx.save();
  // only the face, from the eyebrows down: shrink the oval a little towards its centre
  polyPath(ctx, f.oval.map((p) => [lerp(f.center[0], p[0], 0.9), lerp(f.center[1], p[1], 0.92) + f.d * 0.08]));
  ctx.clip();
  ctx.globalAlpha = Math.min(1, a * 1.2); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  ctx.drawImage(tiny, x0, y0, x1 - x0, y1 - y0);
  ctx.globalAlpha = 0.5 * a; ctx.fillStyle = `rgb(${r / n | 0},${g / n | 0},${b / n | 0})`; ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  ctx.restore();
}

function melt(ctx, f, a, t) {
  if (a <= 0) return;
  const cx = f.center[0], top = f.mid[1] - f.d * 1.3;
  const x0 = Math.max(0, cx - f.d * 3), x1 = Math.min(world.width, cx + f.d * 3), h = Math.min(world.height - top, f.d * 5);
  if (h <= 4 || x1 - x0 <= 4) return;
  tmp.width = x1 - x0; tmp.height = h;
  tctx.drawImage(world, x0, top, x1 - x0, h, 0, 0, x1 - x0, h);
  const sw = Math.max(2, f.d * 0.05);
  for (let x = x0; x < x1; x += sw) {
    const col = Math.exp(-(((x - cx) / (f.d * 1.5)) ** 2));
    const drip = 1 + 0.5 * Math.sin(x / (f.d * 0.18) + 1.7) * Math.sin(x / (f.d * 0.07) + t * 0.5);
    const dy = a * f.d * 2.6 * col * drip;
    ctx.drawImage(tmp, x - x0, 0, sw + 0.5, h, x, top, sw + 0.5, h + dy);
  }
  ctx.save(); ctx.globalCompositeOperation = "multiply"; ctx.globalAlpha = Math.min(0.8, a);
  ctx.fillStyle = "rgb(185,230,160)"; ctx.fillRect(x0, top, x1 - x0, h * 1.6); ctx.restore();
}

let GHOST = null;
function ghostCanvas() {
  if (GHOST) return GHOST;
  const S0 = 512, c = document.createElement("canvas"); c.width = S0; c.height = S0 * 2.1;
  const g = c.getContext("2d"), cx = S0 / 2;
  g.fillStyle = "#0c080a"; g.beginPath(); g.ellipse(cx, S0 * 0.55, S0 * 0.5, S0 * 0.55, 0, 0, 7); g.fill();
  const r = seeded(7); g.strokeStyle = "#0a0608"; g.lineCap = "round";
  for (let i = 0; i < 70; i++) {
    const x = cx + (r() - 0.5) * 0.96 * S0; g.lineWidth = S0 / 26 * (0.6 + r());
    g.beginPath(); g.moveTo(x, S0 * 0.5); g.quadraticCurveTo(x + (r() - 0.5) * 40, S0 * 1.2, x + (r() - 0.5) * 50, S0 * (1.4 + r() * 0.65)); g.stroke();
  }
  const sk = g.createRadialGradient(cx, S0 * 0.62, S0 * 0.05, cx, S0 * 0.68, S0 * 0.4);
  sk.addColorStop(0, "#e8e2db"); sk.addColorStop(0.7, "#bdb6b4"); sk.addColorStop(1, "#6d6870");
  g.fillStyle = sk; g.beginPath(); g.ellipse(cx, S0 * 0.68, S0 * 0.27, S0 * 0.36, 0, 0, 7); g.fill();
  g.fillStyle = "#0e090b"; g.beginPath(); g.ellipse(cx, S0 * 0.44, S0 * 0.32, S0 * 0.14, 0, Math.PI, Math.PI * 2); g.fill();
  [-1, 1].forEach((sx) => {
    const ex = cx + sx * S0 * 0.11, ey = S0 * 0.645;
    g.fillStyle = "rgba(60,50,60,.9)"; g.beginPath(); g.ellipse(ex, ey + 6, S0 * 0.11, S0 * 0.09, 0, 0, 7); g.fill();
    g.fillStyle = "#050205"; g.beginPath(); g.ellipse(ex, ey, S0 * 0.075, S0 * 0.055, 0, 0, 7); g.fill();
    g.strokeStyle = "rgba(25,10,30,.9)"; g.lineWidth = 4; g.beginPath(); g.moveTo(ex, ey + 20); g.lineTo(ex + sx * 3, ey + S0 * 0.2); g.stroke();
  });
  GHOST = c; return c;
}
function drawGhost(ctx, x, y, size, alpha, mouth) {
  const g = ghostCanvas(), k = size / g.width;
  ctx.save(); ctx.globalAlpha = alpha; ctx.drawImage(g, x, y, size, g.height * k);
  ctx.fillStyle = "#080208"; ctx.beginPath();
  ctx.ellipse(x + size / 2, y + size * 0.86, size * (0.05 + 0.06 * mouth), size * (0.02 + 0.17 * mouth), 0, 0, 7); ctx.fill();
  ctx.restore();
}

function ghostify(srcCanvas) {
  tmp.width = srcCanvas.width; tmp.height = srcCanvas.height;
  tctx.globalCompositeOperation = "source-over"; tctx.drawImage(srcCanvas, 0, 0);
  tctx.globalCompositeOperation = "saturation"; tctx.fillStyle = "#808080"; tctx.fillRect(0, 0, tmp.width, tmp.height);
  tctx.globalCompositeOperation = "screen"; tctx.fillStyle = "rgb(70,72,80)"; tctx.fillRect(0, 0, tmp.width, tmp.height);
  tctx.globalCompositeOperation = "source-over";
  return tmp;
}

let NOISE = null;
function grade(ctx, k) {
  const W = world.width, H = world.height;
  ctx.save();
  ctx.globalCompositeOperation = "saturation"; ctx.globalAlpha = 0.65 * k; ctx.fillStyle = "#808080"; ctx.fillRect(0, 0, W, H);
  ctx.globalCompositeOperation = "multiply"; ctx.globalAlpha = k; ctx.fillStyle = "rgb(215,240,205)"; ctx.fillRect(0, 0, W, H);
  ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;
  ctx.fillStyle = `rgba(0,0,0,${0.3 * k + (Math.random() < 0.07 ? 0.25 * k : 0)})`; ctx.fillRect(0, 0, W, H);
  const v = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.2, W / 2, H / 2, Math.max(W, H) * 0.7);
  v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, `rgba(0,0,0,${0.85 * k})`); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  if (!NOISE) {
    NOISE = document.createElement("canvas"); NOISE.width = NOISE.height = 256;
    const nc = NOISE.getContext("2d"), id = nc.createImageData(256, 256);
    for (let i = 0; i < id.data.length; i += 4) { const g = Math.random() * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = g; id.data[i + 3] = 255; }
    nc.putImageData(id, 0, 0);
  }
  ctx.globalCompositeOperation = "overlay"; ctx.globalAlpha = 0.16 * k;
  ctx.translate(-Math.random() * 256, -Math.random() * 256); ctx.fillStyle = ctx.createPattern(NOISE, "repeat"); ctx.fillRect(0, 0, W + 256, H + 256);
  ctx.restore();
}

// ------------------------------------------------------------------ camera (where the screen "looks" inside the world)
function viewTransform(focus, zoom, shake) {
  const W = world.width, H = world.height, VW = view.width, VH = view.height;
  const s = Math.max(VW / W, VH / H) * zoom;
  let tx = VW / 2 - focus[0] * s, ty = VH * 0.45 - focus[1] * s;
  tx = Math.min(0, Math.max(VW - W * s, tx)) + (shake ? (Math.random() - 0.5) * shake : 0);
  ty = Math.min(0, Math.max(VH - H * s, ty)) + (shake ? (Math.random() - 0.5) * shake : 0);
  return [s, tx, ty];
}

// ------------------------------------------------------------------ jump-o-meter (same maths as domain/rules/flinch.py)
function newFlinch() { return { ref: null, best: 0, after: 0, seen: 0 }; }
function flinchUpdate(fl, t, f) {
  if (t < PRE) { if (f) fl.ref = [f.center, f.d]; return; }
  if (t > PRE + WINDOW || !fl.ref) return;
  fl.after++; if (!f) return; fl.seen++;
  const moved = dist(f.center, fl.ref[0]) / fl.ref[1], back = Math.max(0, 1 - f.d / fl.ref[1]) * 4;
  fl.best = Math.max(fl.best, moved, back);
}
// ------------------------------------------------------------------ blink: the hit lands while your eyes are closed
// Eye openness from the Face Mesh eyelid landmarks (upper/lower lid over eye width, both eyes).
const MIN_TENSION = 0.9;                // seconds of tension before a blink may bring the hit forward
function eyeOpenness(lm) {
  if (!lm) return null;
  const d = (a, b) => Math.hypot(lm[a].x - lm[b].x, lm[a].y - lm[b].y);
  const w = d(33, 133) + d(362, 263);
  return w > 0 ? (d(159, 145) + d(386, 374)) / w : null;
}
function trackEyes(fresh) {             // keeps a running "eyes open" baseline; true on the frame a blink starts
  const e = fresh ? eyeOpenness(S.lm) : null;
  if (e == null) return false;
  if (S.eyeBase == null) S.eyeBase = e;
  const closed = e < S.eyeBase * 0.55;
  if (!closed) S.eyeBase = S.eyeBase * 0.95 + e * 0.05;
  const blink = closed && !S.eyesClosed;
  S.eyesClosed = closed;
  return blink;
}
function hitNow(now) {                  // jump the timeline (picture and sound) straight to the hit
  if ((now - S.t0) / 1000 >= PRE) return;
  S.t0 = now - PRE * 1000; S.blinkHit = true;
  if (S.src) { try { S.src.stop(); } catch (e) { /* already stopped */ } }
  const b = S.buffers[S.effect];
  if (b && S.audio) {
    const src = S.audio.createBufferSource(); src.buffer = b; src.connect(S.audio.destination);
    src.start(0, Math.max(0, PRE - 0.05)); S.src = src;
  }
}

function flinchScore(fl) {
  if (!fl || !fl.ref || !fl.after) return null;
  if (fl.seen / fl.after < 0.3) return 10;               // left the frame: maximum
  return Math.max(0, Math.min(10, Math.round(fl.best * 2.5)));
}

// ------------------------------------------------------------------ audio
async function loadBuffer(name) {
  if (S.buffers[name]) return S.buffers[name];
  const res = await fetch(`audio/${name}.mp3`);
  const data = await res.arrayBuffer();
  S.buffers[name] = await new Promise((ok, ko) => S.audio.decodeAudioData(data, ok, ko));
  return S.buffers[name];
}
function playTrack(name) {
  const b = S.buffers[name]; if (!b || !S.audio) return;
  const src = S.audio.createBufferSource(); src.buffer = b; src.connect(S.audio.destination); src.start();
  return src;
}
function sayLine(effect) {
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(tr("lines")[effect]);
  u.lang = tr("speech"); u.pitch = 0.1; u.rate = 0.72; u.volume = 1;
  const v = speechSynthesis.getVoices().find((x) => x.lang && x.lang.startsWith(S.lang)); if (v) u.voice = v;
  speechSynthesis.cancel(); speechSynthesis.speak(u);
}

// ------------------------------------------------------------------ anonymous stats (only numbers, only if a server is there)
async function api(path, body) {
  try {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return r.ok ? await r.json() : null;
  } catch (e) { return null; }
}
async function reportScare(fl, effect, waitS) {
  if (!S.visit) S.visit = (await api("api/web/visits", { lang: S.lang }) || {}).visit;
  if (!S.visit) return null;
  const measured = !!(fl && fl.ref && fl.after);
  const fled = measured && fl.seen / fl.after < 0.3;
  return api("api/web/scares", {
    visit: S.visit, effect, face_seen: !!(fl && fl.ref), fled,
    flinch: measured ? Math.round(Math.min(20, fled ? Math.max(fl.best, 4) : fl.best) * 100) / 100 : null,
    wait_seconds: waitS == null ? null : Math.round(waitS * 10) / 10,
  });
}

// ------------------------------------------------------------------ flow
function hint(text) { $("hint").textContent = text || ""; $("hint").style.opacity = text ? 1 : 0; }
function nextEffect() {
  if (!S.effects.length) { S.effects = EFFECTS.slice().sort(() => Math.random() - 0.5); }
  return S.effects.pop();
}
function startPossession() {
  S.wait = S.faceSince ? (performance.now() - S.faceSince) / 1000 : null;
  S.effect = nextEffect(); S.phase = "possess"; S.t0 = performance.now(); S.flinch = newFlinch(); S.snap = null;
  S.voiceSaid = false; S.hitDone = false; S.blinkHit = false; hint("");
  S.src = playTrack(S.effect);
  loadBuffer(S.effects.length ? S.effects[S.effects.length - 1] : EFFECTS[0]).catch(() => {});   // prefetch the next one
}

function takeSnap(f) {
  const W = world.width, H = world.height, s = Math.min(f.d * 7, W, H);
  const x0 = Math.max(0, Math.min(W - s, f.center[0] - s / 2)), y0 = Math.max(0, Math.min(H - s, f.center[1] - s * 0.45));
  const c = document.createElement("canvas"); c.width = c.height = 720;
  const cx = c.getContext("2d");
  cx.setTransform(-1, 0, 0, 1, c.width, 0);              // the raw camera image, mirrored like the screen
  cx.drawImage(video, (W - x0 - s) * (video.videoWidth / W), y0 * (video.videoHeight / H), s * (video.videoWidth / W), s * (video.videoHeight / H), 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", 0.88);
}

function showPolaroid() {
  S.phase = "polaroid"; hint("");
  const score = flinchScore(S.flinch);
  $("shot").src = S.snap || "";
  $("meter").textContent = (score === null || score === 0 ? tr("meterNone") : tr("meter", score)) + (S.blinkHit ? " · " + tr("blinked") : "");
  $("barfill").style.width = "0";
  $("rank").textContent = "";
  $("polaroid").hidden = false;
  if (score !== null) {
    reportScare(S.flinch, S.effect, S.wait).then((r) => {
      if (!r || S.phase !== "polaroid") return;
      $("rank").textContent = r.rank === null || r.rank === undefined ? tr("first") : tr("rank", r.rank);
    });
  }
  requestAnimationFrame(() => requestAnimationFrame(() => { $("barfill").style.width = `${(score || 0) * 10}%`; }));
}

function frame(now) {
  requestAnimationFrame(frame);
  if (video.readyState < 2) return;
  const W = video.videoWidth, H = video.videoHeight;
  if (world.width !== W || world.height !== H) { world.width = W; world.height = H; }
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const VW = Math.round(innerWidth * dpr), VH = Math.round(innerHeight * dpr);
  if (view.width !== VW || view.height !== VH) { view.width = VW; view.height = VH; }

  if (S.meshReady && !S.sending && S.phase !== "polaroid") {
    S.sending = true; S.sends = (S.sends || 0) + 1;
    S.mesh.send({ image: video }).catch((e) => { S.sendErr = (S.sendErr || 0) + 1; S.lastErr = String(e && (e.message || e)); })
      .finally(() => { S.sending = false; });
  }
  if (DEBUG && S.frameN % 15 === 0) {
    $("dbg").hidden = false;
    $("dbg").textContent = `video ${video.videoWidth}x${video.videoHeight} rs=${video.readyState}\nmodel ready=${!!S.meshReady} sends=${S.sends || 0} results=${S.results || 0} faces=${S.faces || 0}\nerrors=${S.sendErr || 0} ${S.lastErr || ""}\nphase=${S.phase}`;
  }
  wctx.setTransform(-1, 0, 0, 1, W, 0); wctx.drawImage(video, 0, 0, W, H); wctx.setTransform(1, 0, 0, 1, 0, 0);
  const fresh = S.lm && now - S.lmT < 400 ? faceFrom(S.lm) : null;
  if (fresh) { S.face = fresh; S.lastSeen = now; }
  const f = S.face;

  // a small ring of recent frames for the double
  S.frameN++;
  if (S.phase === "possess" && S.effect === "double" && S.frameN % 2 === 0) {
    const c = document.createElement("canvas"); c.width = W >> 1; c.height = H >> 1;
    c.getContext("2d").drawImage(world, 0, 0, c.width, c.height);
    S.buffer.push({ c, f: fresh, t: now }); while (S.buffer.length && now - S.buffer[0].t > 1400) S.buffer.shift();
  }

  let focus = [W / 2, H / 2], zoom = 1, shake = 0;
  if (S.phase === "mirror") {
    if (fresh) { if (!S.faceSince) { S.faceSince = now; S.waitMs = 1500 + Math.random() * 3500; } hint(tr("look")); } else { S.faceSince = 0; }
    trackEyes(fresh);                                             // learn how open their eyes normally are
    if (!S.meshReady) hint(tr("loading"));                       // still downloading: don't blame the face
    else if (!S.results && S.sendErr > 3) hint(tr("noFace") + (DEBUG ? " " + S.lastErr : ""));
    else if (!fresh && S.results && now - Math.max(S.lastSeen, S.readyAt || 0) > 2500) hint(tr("closer"));
    grade(wctx, 0.25);
    if (S.faceSince && now - S.faceSince > (S.waitMs || 1300)) startPossession();   // a random wait: no rhythm to guess
  } else if (S.phase === "possess" && f) {
    const t = (now - S.t0) / 1000, p = Math.min(1, t / PRE), k = ease(p), jumping = t >= PRE, q = jumping ? (t - PRE) / POST : 0;
    flinchUpdate(S.flinch, t, fresh);
    if (trackEyes(fresh) && !jumping && t > MIN_TENSION) hitNow(now);   // you blinked: it's already in your face
    if (!S.voiceSaid && t > 0.5) { S.voiceSaid = true; sayLine(S.effect); }
    if (jumping && !S.hitDone) { S.hitDone = true; if (navigator.vibrate) navigator.vibrate([260, 80, 420]); }
    if (jumping && !S.snap && t > PRE + 0.45) S.snap = takeSnap(f);
    const e = S.effect;
    if (e === "black_eyes") { blackEyes(wctx, f, ease(p * 1.25)); if (jumping) gapingMouth(wctx, f, ease(q * 4)); }
    else if (e === "faceless") { faceless(wctx, f, ease(p * 1.3)); if (jumping) gapingMouth(wctx, f, ease(q * 3.5)); }
    else if (e === "melt") { melt(wctx, f, ease(p) * 0.9 + (jumping ? q * 0.6 : 0), t); if (jumping || p > 0.7) blackEyes(wctx, f, jumping ? 1 : ease((p - 0.7) * 3.3), false); }
    else if (e === "grin") { grin(wctx, f, ease(p * 1.15)); if (p > 0.6) blackEyes(wctx, f, ease((p - 0.6) * 2.5), false); }
    else if (e === "behind_you" && !jumping) {
      const size = f.d * 3.4, side = f.center[0] > W / 2 ? -1 : 1;
      const gx = f.center[0] + side * (f.headHalf * 0.95 + f.d * 0.3 + size * 0.5) - size / 2, gy = f.mid[1] - f.d * 2.3;
      const appear = ease((p - 0.25) / 0.5) * (Math.random() > 0.12 ? 1 : 0.5);
      drawGhost(wctx, gx, gy, size, appear * 0.92, 0.15);
    } else if (e === "double" && S.buffer.length > 3) {
      const late = S.buffer[0], g = ghostify(late.c), lf = late.f;
      if (lf) {
        const half = { ...lf, d: lf.d / 2, center: [lf.center[0] / 2, lf.center[1] / 2], mouth: [lf.mouth[0] / 2, lf.mouth[1] / 2],
                       eyeRings: lf.eyeRings.map((r) => r.map((pt) => [pt[0] / 2, pt[1] / 2])) };
        blackEyes(tctx, half, ease(p * 1.4), false);
        if (jumping) gapingMouth(tctx, half, ease(q * 4));
      }
      const shift = W * (0.3 - 0.2 * k);
      wctx.save(); wctx.globalAlpha = 0.3 + 0.5 * k;
      if (lf) { wctx.beginPath(); wctx.rect(lf.center[0] + shift - lf.d * 3.4, lf.center[1] - lf.d * 3, lf.d * 6.8, H); wctx.clip(); }
      wctx.drawImage(g, shift, 0, W, H); wctx.restore();
      if (jumping && lf) { focus = [lf.center[0] + shift, lf.center[1]]; }
    }
    grade(wctx, jumping ? 1 : 0.35 + 0.65 * k);
    if (jumping && e === "behind_you") {
      wctx.fillStyle = "rgba(0,0,0,.65)"; wctx.fillRect(0, 0, W, H);
      const visW = VW / Math.max(VW / W, VH / H), base = Math.min(H * 0.95, visW * 1.05);   // fits a portrait phone too
      const size = base * (0.7 + 0.45 * ease(q * 3)), j = base * 0.03 * (1 - q);
      drawGhost(wctx, W / 2 - size / 2 + (Math.random() - 0.5) * j, H * 0.5 - size * 0.75 + (Math.random() - 0.5) * j, size, 1, Math.min(1, q * 4));
    }
    // the camera: a slow push-in during the tension, then the lunge
    const zmax = Math.max(1, Math.min(2.3, 0.5 * H / (4.2 * f.d)));
    if (!jumping) {
      zoom = 1 + (zmax - 1) * ease(p * 1.1) * 0.9; focus = [lerp(W / 2, f.center[0], k), lerp(H / 2, f.center[1], k)];
      if (e === "behind_you") {            // keep the girl in shot, even on a narrow portrait screen
        const size = f.d * 3.4, side = f.center[0] > W / 2 ? -1 : 1;
        const gcx = f.center[0] + side * (f.headHalf * 0.95 + f.d * 0.3 + size * 0.5);
        const need = Math.abs(gcx - f.center[0]) + size * 0.7 + f.headHalf * 1.2;
        const s0 = Math.max(VW / W, VH / H);
        zoom = Math.max(1, Math.min(zoom, VW / s0 / need));
        focus = [lerp(W / 2, (gcx + f.center[0]) / 2, k), lerp(H / 2, f.center[1], k)];
      }
    }
    else if (e !== "behind_you") {
      const s0 = Math.max(VW / W, VH / H), zl = Math.max(zmax, Math.min(VW, VH) / s0 / (f.d * 5.2));   // the face fills the short side
      zoom = lerp(zmax, zl, ease(q * 3.2)); if (e !== "double") focus = f.center; shake = f.d * 0.6 * (1 - q * 0.6) * s0;
    } else { shake = 18 * (1 - q); }
    if (t >= PRE + POST) { showPolaroid(); }
  } else if (S.phase === "possess" && !f) {
    grade(wctx, 0.6);
  }

  // world → screen
  const [s, tx, ty] = viewTransform(focus, zoom, shake);
  vctx.setTransform(1, 0, 0, 1, 0, 0); vctx.fillStyle = "#000"; vctx.fillRect(0, 0, VW, VH);
  vctx.setTransform(s, 0, 0, s, tx, ty); vctx.drawImage(world, 0, 0); vctx.setTransform(1, 0, 0, 1, 0, 0);

  if (S.phase === "possess") {
    const t = (now - S.t0) / 1000, p = t / PRE, q = (t - PRE) / POST;
    if (t >= PRE && q < 0.45 && (S.frameN >> 1) % 2 === 0) { vctx.fillStyle = "rgba(170,0,10,.42)"; vctx.fillRect(0, 0, VW, VH); }
    if (t >= PRE && q < 0.035) { vctx.globalCompositeOperation = "difference"; vctx.fillStyle = "#fff"; vctx.fillRect(0, 0, VW, VH); vctx.globalCompositeOperation = "source-over"; }
    if (p > 0.4 && p < 1 && Math.random() > 0.15) {
      const size = Math.round(Math.min(VW * 0.11, VH * 0.07));
      vctx.font = `${size}px Creepster, cursive`; vctx.textAlign = "center"; vctx.textBaseline = "alphabetic";
      vctx.globalAlpha = Math.min(1, (p - 0.4) * 3); vctx.fillStyle = p < 0.8 ? "#ece2e2" : "#e01e28";
      vctx.shadowColor = "#000"; vctx.shadowBlur = 12;
      vctx.fillText(tr("texts")[S.effect], VW / 2, VH * 0.86, VW * 0.92);
      vctx.shadowBlur = 0; vctx.globalAlpha = 1;
    }
  }
}

// ------------------------------------------------------------------ start
async function start() {
  $("start").disabled = true;
  try {
    S.audio = S.audio || new (window.AudioContext || window.webkitAudioContext)();
    if (S.audio.state === "suspended") await S.audio.resume();
    if ("speechSynthesis" in window) { const u = new SpeechSynthesisUtterance(" "); u.volume = 0; speechSynthesis.speak(u); }   // unlock on iOS
    if (!window.isSecureContext) throw Object.assign(new Error("insecure"), { name: "Insecure" });
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw Object.assign(new Error("none"), { name: "NotFoundError" });
    const stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } } });
    video.srcObject = stream; await video.play();
    $("intro").hidden = true; S.phase = "mirror"; hint(tr("loading"));
    EFFECTS.forEach((e) => loadBuffer(e).catch(() => {}));
    if (!S.mesh) {
      const base = new URL("vendor/face_mesh/", location.href).href;     // the model ships with the page: no CDN, no tracking
      S.mesh = new FaceMesh({ locateFile: (file) => base + file });
      S.mesh.setOptions({ maxNumFaces: 1, refineLandmarks: false, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
      S.mesh.onResults((r) => {
        S.results = (S.results || 0) + 1;
        const lm = r.multiFaceLandmarks && r.multiFaceLandmarks[0];
        if (lm) { S.faces = (S.faces || 0) + 1; S.lm = lm; S.lmT = performance.now(); }
      });
      await S.mesh.initialize();
      S.meshReady = true; S.readyAt = performance.now();
    }
    hint(tr("look"));
  } catch (err) {
    fallback(err);
  } finally { $("start").disabled = false; }
}

function fallback(err) {
  console.warn("[scare-tv]", err && (err.name || err.message));
  const n = err && err.name;
  $("errmsg").textContent = n === "NotAllowedError" ? tr("errDenied") : n === "NotFoundError" || n === "OverconstrainedError" ? tr("errNone")
    : n === "Insecure" ? tr("errInsecure") : tr("errModel");
  $("intro").hidden = true; $("fallback").hidden = false; S.phase = "fallback"; hint("");
}

$("start").addEventListener("click", start);
$("retry").addEventListener("click", () => { $("fallback").hidden = true; $("intro").hidden = false; $("classic").pause(); });
$("again").addEventListener("click", () => {
  $("polaroid").hidden = true; S.phase = "mirror"; S.faceSince = 0; S.buffer = []; hint(tr("look"));
  if (S.audio && S.audio.state === "suspended") S.audio.resume();
});
$("save").addEventListener("click", () => {
  if (!S.snap) return;
  const a = document.createElement("a"); a.href = S.snap; a.download = "scare-tv-my-scared-face.jpg"; document.body.appendChild(a); a.click(); a.remove();
});

let startLang = "en";
try { startLang = localStorage.getItem("stv-lang") || ""; } catch (e) { /* private mode */ }
if (!startLang) startLang = (navigator.language || "").toLowerCase().startsWith("es") ? "es" : "en";
applyLang(startLang);
requestAnimationFrame(frame);

// for automated tests only
window.__stv = { S, EFFECTS, startPossession, flinchScore, newFlinch, flinchUpdate, faceFrom, showPolaroid, reportScare };
