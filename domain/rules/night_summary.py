"""How a night is summarized: arrivals, scares, live vs classic and the jump for each one."""
import statistics


def group_stats(rows):
    fl = [r.flinch for r in rows if r.flinch is not None]
    return {
        "n": len(rows),
        "measured": len(fl),
        "flinch_mean": round(statistics.mean(fl), 2) if fl else None,
        "flinch_median": round(statistics.median(fl), 2) if fl else None,
        "fled": sum(1 for r in rows if r.fled),
        "face_seen": sum(1 for r in rows if r.face_seen),
    }


def percentile_rank(values, value):
    """Percentage of `values` strictly below `value` (0-100), or None if there is nothing to compare with."""
    others = [v for v in values if v is not None]
    if value is None or not others:
        return None
    return round(100 * sum(1 for v in others if v < value) / len(others))


def summarize_all(scares, arrivals, nights):
    """Summary over many nights at once (e.g. every visit to the web mirror)."""
    s = _summarize_scares(scares, arrivals)
    return {"visits": nights, **s}


def summarize(night, scares, arrivals):
    return {"night": str(night.id), "minutes": night.minutes, **_summarize_scares(scares, arrivals)}


def _summarize_scares(scares, arrivals):
    real = [s for s in scares if not s.false_alarm]
    by_name = {}
    for s in real:
        by_name.setdefault((s.kind, s.name), []).append(s)
    waits = [s.wait_seconds for s in real if s.wait_seconds is not None]
    return {
        "arrivals": arrivals,
        "scares": len(real),
        "false_alarms": sum(1 for s in scares if s.false_alarm),
        "wait_median_s": round(statistics.median(waits), 1) if waits else None,
        "live": group_stats([s for s in real if s.kind == "live"]),
        "classic": group_stats([s for s in real if s.kind == "file"]),
        "by_scare": sorted(({"kind": k, "name": n, **group_stats(rows)} for (k, n), rows in by_name.items()),
                           key=lambda r: -(r["flinch_mean"] if r["flinch_mean"] is not None else -1)),
    }


def as_markdown(s, date_label):
    f = lambda v: "–" if v is None else str(v)  # noqa: E731
    lines = [f"# Scare-TV · night of {date_label}", "",
             f"- Switched on: **{s['minutes']} min**",
             f"- People arriving at the TV: **{s['arrivals']}**",
             f"- Scares: **{s['scares']}** (false alarms marked with F: {s['false_alarms']})",
             f"- Typical time from someone arriving to the scare: **{f(s['wait_median_s'])} s**", "",
             "Jump-o-meter: how far the face moved in the second and a half after the hit, "
             "in eye-distances (more = bigger jump).", "",
             "| Type | Scares | Measured | Mean jump | Median | Fled the frame |",
             "|---|---|---|---|---|---|"]
    for label, g in (("Live (their face)", s["live"]), ("Classic (drawings)", s["classic"])):
        lines.append(f"| {label} | {g['n']} | {g['measured']} | {f(g['flinch_mean'])} | {f(g['flinch_median'])} | {g['fled']} |")
    lines += ["", "| Scare | Type | Times | Mean jump | Fled |", "|---|---|---|---|---|"]
    for r in s["by_scare"]:
        lines.append(f"| {r['name']} | {'live' if r['kind'] == 'live' else 'classic'} | {r['n']} | {f(r['flinch_mean'])} | {r['fled']} |")
    lines += ["", "*No images or sound: just these numbers.*"]
    return "\n".join(lines)


def web_markdown(s):
    """Markdown for the web mirror stats (every visit together)."""
    f = lambda v: "–" if v is None else str(v)  # noqa: E731
    g = s["live"]
    lines = ["# Scare-TV · web mirror stats", "",
             f"- Visits: **{s['visits']}**",
             f"- Scares: **{s['scares']}** ({g['measured']} with a measured jump)",
             f"- Mean jump: **{f(g['flinch_mean'])}** eye-distances (median {f(g['flinch_median'])})",
             f"- Fled the frame: **{g['fled']}**", "",
             "| Scare | Times | Mean jump | Fled |", "|---|---|---|---|"]
    for r in s["by_scare"]:
        lines.append(f"| {r['name']} | {r['n']} | {f(r['flinch_mean'])} | {r['fled']} |")
    lines += ["", "*Anonymous numbers only: no image or sound ever leaves the visitor's phone.*"]
    return "\n".join(lines)
