"""Layer-by-layer checks: what a slicer would find when it prints one layer on the one below.

The part is sliced once, every LAYER mm, in the orientation it was exported in (flat side on the
bed). Each layer is compared with the layer below. Reported kinds:

  thin_feature      a region narrower than min_width that persists over several layers
  floating_region   an outline that neither sits on the layer below nor touches it (it starts
                    in mid-air). Slivers too narrow for a slicer to extrude are ignored
  ledge             a flat underside reaching more than max_ledge past the layer below
                    without support on a second side
  bridge_too_long   a bridge spanning more than max_bridge
  ceiling_bridge    a bridge longer than ceiling_warn that is wider than a thin wall head
  bridge            any other bridge (reported for information)

Known gap: an overhang held on two sides is classed as a bridge even when part of it sticks out
beyond those supports. The slicer check catches that case; this one does not yet.

This module only measures. limits.py holds the numbers, the severity of each kind and whether it
may be waived.
"""
from dataclasses import asdict, dataclass

import numpy as np
from manifold3d import JoinType, Manifold, Mesh

import limits as L


class MeshError(ValueError):
    """The file loaded but is not a solid the checks can slice."""


@dataclass
class Finding:
    kind: str
    value: float      # the measurement the kind is about
    what: str         # what `value` is: "span_mm", "reach_mm" or "area_mm2"
    x: float
    y: float
    z0: float
    z1: float
    area: float       # mm2: largest per-layer area (overhangs), or the sum over layers (thin)
    width: float = 0.0   # mm, widest inscribed width of a bridging region; 0 when not measured

    def to_dict(self):
        return asdict(self)


def load(path):
    """Read an STL as a solid. Raises FileNotFoundError, or MeshError when it is not a valid solid.

    The solid test is manifold3d's, not trimesh's `is_watertight`: trimesh reports parts made of
    several touching bodies as open although they slice correctly.
    """
    import trimesh
    tm = trimesh.load(path, force="mesh")
    if len(tm.faces) == 0:
        raise MeshError("the file contains no triangles")
    m = Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                      tri_verts=np.asarray(tm.faces, np.uint32)))
    if m.status().name != "NoError":
        raise MeshError(f"not a valid solid ({m.status().name}); repair the mesh first")
    if m.is_empty():
        raise MeshError("the solid is empty")
    return m


def _off(cs, d):
    return cs.offset(d, JoinType.Round, 2.0, 24)


def _centre(cs):
    b = cs.bounds()
    return round((b[0] + b[2]) / 2, 1), round((b[1] + b[3]) / 2, 1)


def _reach(island, support, limit=60.0):
    """How far the island reaches past the support: smallest d with the island inside the support
    grown by d (binary search, 10 steps)."""
    if (island - _off(support, limit)).area() > L.MIN_ISLAND_AREA:
        return limit
    lo, hi = 0.0, limit
    for _ in range(10):
        mid = (lo + hi) / 2
        if (island - _off(support, mid)).area() > 0.05:
            lo = mid
        else:
            hi = mid
    return hi


def _extrudable(cs):
    """False for a sliver narrower than FLOAT_MIN_WIDTH: a slicer prints nothing there."""
    return cs.offset(-L.FLOAT_MIN_WIDTH / 2, JoinType.Round).area() > 1e-3


def inscribed_width(cs):
    """Widest inscribed width of a region: twice the largest inward offset that leaves something.
    A thin wall head measures as its wall thickness; a ceiling measures as its smaller side."""
    if not cs.offset(-0.05, JoinType.Round).area() > 0:
        return 0.1
    lo, hi = 0.0, 20.0
    for _ in range(9):
        mid = (lo + hi) / 2
        if cs.offset(-mid, JoinType.Round).area() > 1e-3:
            lo = mid
        else:
            hi = mid
    return 2 * lo


def scan(m, layer=L.LAYER, min_width=None, max_ledge=None, max_bridge=None, ceiling_warn=None):
    """One pass over the layers. Returns per-layer raw items:

    thin    (z, (x, y), area)
    over    (kind, z, (x, y), area, reach, held_two_sides, width, extrudable)
            kind: float | bridge | ledge
    floats  (z, (x, y), area)
    """
    min_width = L.value("min_width") if min_width is None else min_width
    max_ledge = L.value("max_ledge") if max_ledge is None else max_ledge
    max_bridge = L.value("max_bridge") if max_bridge is None else max_bridge
    ceiling_warn = L.value("ceiling_warn") if ceiling_warn is None else ceiling_warn
    step = layer * L.STEP_FACTOR

    bb = m.bounding_box()
    z0, z1 = bb[2], bb[5]
    zs = np.arange(z0 + layer / 2, z1, layer)
    thin, over, floats = [], [], []
    prev = None          # the layer below (may be empty)
    started = False      # a non-empty layer has been seen: the part has left the bed
    r = min_width / 2 - 0.01
    for z in zs:
        cs = m.slice(z)
        if cs.is_empty():
            prev = cs
            continue

        # thin features: what an opening of radius r removes
        opened = _off(_off(cs, -r), r)
        for p in (cs - opened).decompose():
            if p.area() > L.MIN_ISLAND_AREA and p.area() > L.MIN_THIN_AREA:
                thin.append((round(z, 2), _centre(p), round(p.area(), 2)))

        # floating regions: an outline of this layer that neither sits on the layer below nor
        # touches it. One that touches is an overhang and is judged by the ledge and bridge rules
        # further down. After an empty layer everything is floating.
        if started:
            below = None if prev.is_empty() else _off(prev, -L.FLOAT_SHRINK)
            reach = None if prev.is_empty() else _off(prev, L.FLOAT_BOND)
            for p in cs.decompose():
                a = p.area()
                if a < L.FLOAT_MIN_AREA:
                    continue
                ov = 0.0 if below is None else (p ^ below).area()
                if not (ov < L.FLOAT_OVERLAP * a or ov < L.FLOAT_MIN_OVERLAP) or not _extrudable(p):
                    continue
                if reach is None or (p ^ reach).area() < L.FLOAT_MIN_OVERLAP:
                    floats.append((round(z, 2), _centre(p), round(a, 2)))

        # overhangs: what sticks out past the layer below
        if prev is not None and z - z0 > layer:
            sup = _off(prev, step)
            for p in (cs - sup).decompose():
                if not p.area() > L.MIN_ISLAND_AREA:
                    continue
                ring = _off(p, step + 0.3) - _off(p, step)
                touch = ring ^ prev
                n_touch = len([t for t in touch.decompose() if t.area() > 0.05])
                held = touch.area() / ring.area() if ring.area() > 0 else 0
                d = _reach(p, prev)
                if d <= max_ledge:
                    continue
                two_sides = n_touch >= 2 or held > L.BRIDGE_HELD
                if n_touch == 0:
                    kind = "float"
                elif two_sides and d <= max_bridge / 2:
                    kind = "bridge"
                else:
                    kind = "ledge"
                w = inscribed_width(p) if kind == "bridge" and 2 * d > ceiling_warn else 0.0
                ext = _extrudable(p) if kind == "float" else True
                over.append((kind, round(z, 2), _centre(p), round(p.area(), 2), round(d, 1),
                             two_sides, round(w, 2), ext))
        prev = cs
        started = True
    return thin, over, floats


def cluster_thin(items, tol=2.0):
    """Merge per-layer thin regions into features (same xy within tol, z gaps under 1 mm)."""
    feats = []
    for z, (x, y), a in items:
        for f in feats:
            if abs(f["x"] - x) < tol and abs(f["y"] - y) < tol and z - f["z1"] < 1.01:
                f["z1"] = z
                f["area"] += a
                break
        else:
            feats.append({"x": x, "y": y, "z0": z, "z1": z, "area": a})
    return [f for f in feats if f["area"] > L.MIN_THIN_TOTAL and f["z1"] - f["z0"] >= L.MIN_THIN_HEIGHT]


def cluster_over(items, tol=3.0):
    """Merge per-layer overhang islands of one kind into features."""
    feats = []
    for kind, z, (x, y), a, d, two_sides, w, ext in items:
        for f in feats:
            if f["kind"] == kind and abs(f["x"] - x) < tol and abs(f["y"] - y) < tol and z - f["z1"] < 1.01:
                f["z1"] = z
                f["area"] = max(f["area"], a)
                f["dist"] = max(f["dist"], d)
                f["two_sides"] = f["two_sides"] or two_sides
                f["width"] = max(f["width"], w)
                f["extrudable"] = f["extrudable"] or ext
                break
        else:
            feats.append({"kind": kind, "x": x, "y": y, "z0": z, "z1": z, "area": a, "dist": d,
                          "two_sides": two_sides, "width": w, "extrudable": ext})
    return feats


def _near(a, b, tol=3.0):
    return abs(a.x - b["x"]) < tol and abs(a.y - b["y"]) < tol and abs(a.z0 - b["z0"]) < 0.31


def run(m, layer=L.LAYER):
    """All layer findings for a solid, as a list of Finding. Nothing here decides pass or fail."""
    thin, over, floats = scan(m, layer=layer)
    out = []
    for f in cluster_thin(thin):
        out.append(Finding("thin_feature", round(f["area"], 2), "area_mm2",
                           f["x"], f["y"], f["z0"], f["z1"], round(f["area"], 2)))
    for z, (x, y), a in floats:
        out.append(Finding("floating_region", a, "area_mm2", x, y, z, z, a))
    n_float = len(out)
    head = L.value("thin_wall_head") + L.WIDTH_TOL
    for f in cluster_over(over):
        span = round(2 * f["dist"], 1)
        if f["kind"] == "float":
            # An overhang island touching nothing. The floating-region test above reports these
            # (or ignores them as slivers); a wide one it somehow missed is still reported.
            if f["extrudable"] and not any(_near(g, f) for g in out[:n_float]):
                out.append(Finding("floating_region", f["area"], "area_mm2",
                                   f["x"], f["y"], f["z0"], f["z1"], f["area"]))
        elif f["kind"] == "ledge" and f["two_sides"]:
            out.append(Finding("bridge_too_long", span, "span_mm",
                               f["x"], f["y"], f["z0"], f["z1"], f["area"]))
        elif f["kind"] == "ledge":
            out.append(Finding("ledge", f["dist"], "reach_mm",
                               f["x"], f["y"], f["z0"], f["z1"], f["area"]))
        elif span > L.value("ceiling_warn") and f["width"] > head:
            out.append(Finding("ceiling_bridge", span, "span_mm",
                               f["x"], f["y"], f["z0"], f["z1"], f["area"], f["width"]))
        else:
            out.append(Finding("bridge", span, "span_mm",
                               f["x"], f["y"], f["z0"], f["z1"], f["area"], f["width"]))
    return out
