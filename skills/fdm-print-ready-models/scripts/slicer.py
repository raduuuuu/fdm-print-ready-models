"""Check 5: slice the part with a real slicer and read what the slicer decided.

The geometry checks approximate a slicer. This one runs PrusaSlicer or OrcaSlicer on the part,
in its print orientation, with no supports, and reports:

  slicer_alert            the slicer's own print-stability alerts (PrusaSlicer only)
  slicer_bridge_too_long  the longest bridging line over air, when it is over max_bridge
  slicer_wall_in_air      an overhang wall printed further from the layer below than max_ledge
  slicer_longest_bridge   the longest bridge over air, for information

PrusaSlicer needs nothing but the STL. OrcaSlicer needs three preset files exported from the
slicer (machine, process, filament); supports are switched off in a copy of the process preset.

The measuring needs the package shapely (requirements-slicer.txt). Without it, or without a
slicer, the check is skipped and the verdict says "geometry only".
"""
import json
import math
import os
import re
import shutil
import subprocess
import tempfile

import limits as L
from layers import Finding, slices_of

BRIDGE = {"Bridge infill", "Bridge"}
OVERHANG = {"Overhang perimeter", "Overhang wall"}
OUTER = {"External perimeter", "Outer wall", "Perimeter", "Inner wall"} | OVERHANG
ALERTS = ("Floating bridge anchors", "Long bridging extrusions", "Collapsing overhang",
          "Loose extrusions", "Thin fragile part", "Floating object part", "Low bed adhesion")
TESTED = {"PrusaSlicer": ("2.9",), "OrcaSlicer": ("2.5",)}
PATHS = {
    "prusa": ["prusa-slicer", "PrusaSlicer", "prusa-slicer-console",
              "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
              "/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/PrusaSlicer"],
    "orca": ["orca-slicer", "OrcaSlicer", "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"],
}


class Skipped(Exception):
    """The check could not be attempted (no slicer, no presets, a package missing). Not a failure."""


class SlicerError(Exception):
    """The slicer was run and did not produce a slice that can be trusted."""


def find(kind):
    for name in PATHS[kind]:
        path = name if os.path.isabs(name) else shutil.which(name)
        if path and os.path.isfile(path):
            return path
    return None


def choose(want="auto", path=None, orca_presets=None):
    """(kind, executable) to use, or raise Skipped saying why not."""
    if want == "none":
        raise Skipped("the slicer check was switched off")
    if path:
        if not os.path.isfile(path):
            raise Skipped(f"no slicer at {os.path.basename(path)}")
        kind = want if want in ("prusa", "orca") else ("orca" if "orca" in os.path.basename(path).lower() else "prusa")
        if kind == "orca" and not orca_presets:
            raise Skipped("OrcaSlicer needs --orca-presets (machine, process and filament files)")
        return kind, path
    if want in ("auto", "prusa") and find("prusa"):
        return "prusa", find("prusa")
    if want in ("auto", "orca") and find("orca"):
        if orca_presets:
            return "orca", find("orca")
        raise Skipped("OrcaSlicer found, but it needs --orca-presets (machine, process and filament files)")
    raise Skipped("no slicer found" if want == "auto" else f"{want} slicer not found")


def parse_alerts(text):
    """PrusaSlicer's print-stability alerts from its console output."""
    found = []
    for block in re.findall(r"print warning:(.*?)(?:\n\d+ =>|\Z)", text, re.S):
        for line in block.splitlines():
            for item in line.split(","):
                if item.strip() in ALERTS:
                    found.append(item.strip())
    return sorted(set(found))


def _run(cmd, cwd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", cwd=cwd,
                           timeout=L.SLICER_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise SlicerError(f"the slicer did not finish within {L.SLICER_TIMEOUT} seconds")
    except OSError as e:
        raise SlicerError(f"the slicer could not be started ({e.strerror})")
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
        raise SlicerError(f"the slicer exited with code {r.returncode}: {' | '.join(tail)}")
    return r.stdout + r.stderr


def slice_prusa(exe, stl, workdir):
    out = os.path.join(workdir, "out.gcode")
    args = ["--layer-height", f"{L.LAYER:g}", "--first-layer-height", f"{L.LAYER:g}",
            "--nozzle-diameter", f"{L.NOZZLE:g}", "--filament-diameter", "1.75", "--perimeters", "3",
            "--fill-density", "15%", "--bed-shape", "0x0,256x0,256x256,0x256", "--center", "128,128",
            "--skirts", "0", "--use-relative-e-distances"]
    text = _run([exe, "--export-gcode", *args, "-o", out, os.path.abspath(stl)], workdir)
    return out, parse_alerts(text)


def slice_orca(exe, stl, workdir, presets):
    machine, process, filament = [os.path.abspath(p) for p in presets]
    for p in (machine, process, filament):
        if not os.path.isfile(p):
            raise SlicerError(f"preset file not found: {os.path.basename(p)}")
    try:
        with open(process) as fh:
            proc = json.load(fh)
    except (OSError, ValueError) as e:
        raise SlicerError(f"the process preset cannot be read: {e}")
    proc["enable_support"] = "0"              # the check is about printing without supports
    no_support = os.path.join(workdir, "process_no_support.json")
    with open(no_support, "w") as fh:
        json.dump(proc, fh)
    outdir = os.path.join(workdir, "out")
    os.makedirs(outdir)
    _run([exe, "--datadir", os.path.join(workdir, "data"), "--slice", "0", "--outputdir", outdir,
          "--load-settings", f"{machine};{no_support}", "--load-filaments", filament,
          os.path.abspath(stl)], workdir)
    made = [f for f in os.listdir(outdir) if f.endswith(".gcode")]
    return (os.path.join(outdir, made[0]) if made else os.path.join(outdir, "missing.gcode")), None


_NUM = re.compile(r"([XYZEIJ])(-?\d*\.?\d+)")


def _arc(x, y, nx, ny, i, j, clockwise):
    """Points along a G2/G3 arc from (x, y) to (nx, ny) about (x + i, y + j), about 1 mm apart.
    The same start and end is a full circle."""
    cx, cy, r = x + i, y + j, math.hypot(i, j)
    a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
    sweep = (a0 - a1) if clockwise else (a1 - a0)
    if sweep <= 1e-9:
        sweep += 2 * math.pi
    n = min(720, max(1, math.ceil(r * sweep)))
    turn = -sweep if clockwise else sweep
    pts = [(cx + r * math.cos(a0 + turn * k / n), cy + r * math.sin(a0 + turn * k / n)) for k in range(1, n)]
    return pts + [(nx, ny)]


def parse_gcode(path, zs=None):
    """(slicer name, version, segments). A segment is an extruding move:
    (feature, z, x0, y0, x1, y1). Understands PrusaSlicer (;TYPE:) and OrcaSlicer (; FEATURE:).
    Travel moves (G0, or G1 without extrusion) move the position; arcs with a centre are cut into
    short chords. `zs`, if given, receives the height of every layer."""
    if not os.path.isfile(path):
        raise SlicerError("could not confirm the slice ran: no G-code was written")
    name = version = None
    x = y = z = 0.0
    feature, layers, segs = "", 0, []
    with open(path, errors="replace") as fh:
        for line in fh:
            if line.startswith(";"):
                m = re.match(r"; generated by (\w+) ([\d.]+)", line)
                if m and name is None:
                    name, version = m.group(1), m.group(2)
                elif line.startswith(";TYPE:"):
                    feature = line[6:].strip()
                elif line.startswith("; FEATURE: "):
                    feature = line[11:].strip()
                elif line.startswith(";Z:") or line.startswith("; Z_HEIGHT: "):
                    z = float(line.split(":")[1])
                    layers += 1
                    if zs is not None:
                        zs.append(z)
                continue
            if line.startswith("M82"):
                raise SlicerError("the G-code uses absolute extrusion; switch on relative extruder distances")
            if not line.startswith(("G0 ", "G1 ", "G2 ", "G3 ")):
                continue
            v = dict(_NUM.findall(line.split(";")[0]))
            nx, ny = float(v.get("X", x)), float(v.get("Y", y))
            if "E" in v and float(v["E"]) > 0 and feature in (BRIDGE | OUTER):
                if line[1] in "23" and ("I" in v or "J" in v):
                    pts = _arc(x, y, nx, ny, float(v.get("I", 0)), float(v.get("J", 0)), line[1] == "2")
                else:
                    pts = [(nx, ny)]         # a straight move, or an arc given by radius: its chord
                px, py = x, y
                for qx, qy in pts:
                    if qx != px or qy != py:
                        segs.append((feature, z, px, py, qx, qy))
                    px, py = qx, qy
            x, y = nx, ny
    if name is None or layers == 0 or not segs:
        raise SlicerError("could not confirm the slice ran: the G-code has no layers or no slicer header")
    return name, version, segs


def check_layers(zs):
    """The G-code must have the layers the part is compared against. A preset with another layer
    height would be measured against the wrong layer below, so the run is not trusted."""
    if max(abs(z / L.LAYER - round(z / L.LAYER)) for z in zs) > 0.25:
        steps = sorted({round(b - a, 3) for a, b in zip(zs, zs[1:]) if b > a})[:3]
        raise SlicerError(f"the slicer's layers do not match the {L.LAYER:g} mm layers the check measures "
                          f"against (first layer at {zs[0]:g} mm, then steps of "
                          f"{', '.join(f'{s:g}' for s in steps) or 'none'} mm): pass --layer with the "
                          f"preset's layer height, or set the preset's layer height and first layer "
                          f"height to {L.LAYER:g} mm")


def _join_bridges(segs):
    """Bridging moves that carry on in a straight line are one line. A slicer may send one long
    bridge as several moves, and each piece alone would look short."""
    out = []
    for s in segs:
        p = out[-1] if out else None
        if p and s[0] in BRIDGE and p[0] in BRIDGE and p[1] == s[1] \
                and math.hypot(p[4] - s[2], p[5] - s[3]) < 0.05:
            ax, ay, bx, by = p[4] - p[2], p[5] - p[3], s[4] - s[2], s[5] - s[3]
            la, lb = math.hypot(ax, ay), math.hypot(bx, by)
            if la > 0 and lb > 0 and ax * bx + ay * by > 0 and abs(ax * by - ay * bx) < 0.05 * la * lb:
                out[-1] = (p[0], p[1], p[2], p[3], s[4], s[5])
                continue
        out.append(s)
    return out


def _shift(m, segs):
    """Where the slicer put the part on its bed, as (dx, dy) from part coordinates to G-code
    coordinates: the middle of the wall moves against the middle of the part."""
    xs = [s[2] for s in segs if s[0] in OUTER] + [s[4] for s in segs if s[0] in OUTER]
    ys = [s[3] for s in segs if s[0] in OUTER] + [s[5] for s in segs if s[0] in OUTER]
    bb = m.bounding_box()
    return (min(xs) + max(xs)) / 2 - (bb[0] + bb[3]) / 2, (min(ys) + max(ys)) / 2 - (bb[1] + bb[4]) / 2


def measure(m, segs):
    """Every bridging line and overhang wall against the layer below it.
    Returns (spans, walls): spans are (length, x, y, z); walls are (distance out, length, x, y, z)."""
    from shapely.geometry import LineString, Point, Polygon
    max_air = L.value("max_ledge")
    dx, dy = _shift(m, segs)
    z0, sliced = slices_of(m)
    below, grown = {}, {}

    def sup_at(z):
        if z not in below:
            i = int(round((z - 1.5 * L.LAYER) / L.LAYER - 0.5))      # the slice of the layer below
            g = None
            if 0 <= i < len(sliced):
                for c in sliced[i][1].to_polygons():
                    if len(c) < 3:
                        continue
                    p = Polygon(c)
                    if not p.is_valid:
                        p = p.buffer(0)
                    g = p if g is None else g.symmetric_difference(p)
            below[z] = g
        return below[z]

    spans, walls = [], []

    def close_run(run):
        """A chain of overhang-wall moves: held at both ends is a bridge, otherwise a ledge."""
        if not run:
            return
        z, raw = run
        sup = sup_at(z)
        pts = [raw[0]]                  # resample about every mm so long straight moves are measured
        for p in raw[1:]:
            q = pts[-1]
            n = max(1, int(math.hypot(p[0] - q[0], p[1] - q[1])))
            pts += [(q[0] + (p[0] - q[0]) * i / n, q[1] + (p[1] - q[1]) * i / n) for i in range(1, n + 1)]
        d = [99.0 if sup is None else float(Point(p).distance(sup)) for p in pts]
        k = d.index(max(d))
        length = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
        if d[0] < L.SLICER_END_HELD and d[-1] < L.SLICER_END_HELD and max(d) >= max_air:
            chord = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
            if chord > L.SLICER_MIN_LINE:
                spans.append((round(chord, 1), round(pts[k][0], 1), round(pts[k][1], 1), round(z0 + z, 1)))
        elif max(d) > L.SLICER_WALL_MIN and length >= L.SLICER_MIN_RUN:
            walls.append((round(max(d), 1), round(length, 1), round(pts[k][0], 1), round(pts[k][1], 1), round(z0 + z, 1)))

    run = None
    for feature, z, ax, ay, bx, by in _join_bridges(segs):
        if z < 1.5 * L.LAYER or feature not in (BRIDGE | OVERHANG):
            continue
        a, b = (ax - dx, ay - dy), (bx - dx, by - dy)
        if feature in BRIDGE:
            close_run(run)
            run = None
            if math.hypot(b[0] - a[0], b[1] - a[1]) < L.SLICER_MIN_LINE:
                continue
            sup = sup_at(z)
            line = LineString([a, b])
            # a line within one extrusion width of the layer below leans on its neighbour
            if sup is not None and z not in grown:
                grown[z] = sup.buffer(L.SLICER_LEAN)
            air = line if sup is None else line.difference(grown[z])
            for p in ([air] if air.geom_type == "LineString" else list(getattr(air, "geoms", []))):
                if p.length > L.SLICER_MIN_LINE:
                    n = max(2, int(p.length))
                    far = max(float(p.interpolate(i / n, normalized=True).distance(sup)) if sup is not None else 99.0
                              for i in range(n + 1))
                    mid = p.interpolate(0.5, normalized=True)
                    at = (round(float(mid.x), 1), round(float(mid.y), 1), round(z0 + z, 1))
                    if far < max_air:          # runs along a narrow ledge: not a span
                        walls.append((round(far, 1), round(p.length, 1)) + at)
                    else:
                        spans.append((round(p.length, 1),) + at)
        elif run and run[0] == z and math.hypot(run[1][-1][0] - a[0], run[1][-1][1] - a[1]) < 0.05:
            run[1].append(b)
        else:
            close_run(run)
            run = (z, [a, b])
    close_run(run)
    return sorted(spans, reverse=True), sorted(walls, reverse=True)


def run(m, stl, want="auto", path=None, orca_presets=None, info=None):
    """Slice and measure. Returns findings; raises Skipped or SlicerError.
    `info`, if given, receives the slicer's name and version for the report."""
    kind, exe = choose(want, path, orca_presets)
    try:
        import shapely  # noqa: F401
    except ImportError:
        raise Skipped("the slicer check needs the package shapely (requirements-slicer.txt)")
    with tempfile.TemporaryDirectory() as work:
        if kind == "prusa":
            gcode, alerts = slice_prusa(exe, stl, work)
        else:
            gcode, alerts = slice_orca(exe, stl, work, orca_presets)
        zs = []
        name, version, segs = parse_gcode(gcode, zs)
    check_layers(zs)
    if info is not None:
        info.update({"name": name, "version": version})
    spans, walls = measure(m, segs)

    def note(kind_, text):
        return Finding(kind_, text, "note", 0.0, 0.0, 0.0, 0.0, 0.0)
    out = []
    if not any(version.startswith(v) for v in TESTED.get(name, ())):
        out.append(note("slicer_untested_version", f"{name} {version}"))
    for a in alerts or []:
        out.append(note("slicer_alert", a))
    if alerts is None:
        out.append(note("slicer_alerts_not_read", name))
    if spans:
        length, x, y, z = spans[0]
        over = length > L.value("max_bridge")
        out.append(Finding("slicer_bridge_too_long" if over else "slicer_longest_bridge",
                           length, "span_mm", x, y, z, z, 0.0))
    for dist, length, x, y, z in walls:
        if dist > L.value("max_ledge"):
            out.append(Finding("slicer_wall_in_air", dist, "reach_mm", x, y, z, z, 0.0, length))
    return out
