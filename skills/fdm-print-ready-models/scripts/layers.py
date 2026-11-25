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
  overhang_past_supports   a bridge whose deck sticks out more than max_ledge past the outline
                    of its supports

The post check (run_posts) and the support prediction (run_supports) use the same slices:
  thin_post_overhang, thin_post_overhang_small, slender_column
  support_on_plate, support_on_model, support_enclosed

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


_SLICES = []     # [solid, layer, result] for the last solid sliced


def slices_of(m, layer=None):
    """(z of the bed, [(z, outline), ...]) for a solid. Sliced once and remembered for the last
    solid only, so the layer, post and support checks share one slicing pass. The solid itself
    is kept and compared by identity: an id() alone can be reused by a later object."""
    layer = L.LAYER if layer is None else layer
    if not (_SLICES and _SLICES[0] is m and _SLICES[1] == layer):
        bb = m.bounding_box()
        _SLICES[:] = [m, layer, (bb[2], [(z, m.slice(z)) for z in np.arange(bb[2] + layer / 2, bb[5], layer)])]
    return _SLICES[2]


def _past_supports(island, touch, step):
    """How far a bridging island reaches beyond the convex outline of its supports (0 if it
    stays between them). `touch` is where the island's rim rests on the layer below."""
    span = _off(touch.hull(), step + 0.3 + 0.05)
    outside = island - span
    if not outside.area() > L.MIN_ISLAND_AREA:
        return 0.0
    return _reach(outside, span)


def scan(m, layer=None, min_width=None, max_ledge=None, max_bridge=None, ceiling_warn=None,
         cantilever=True):
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
    layer = L.LAYER if layer is None else layer
    step = layer * L.STEP_FACTOR

    z0, sliced = slices_of(m, layer)
    thin, over, floats = [], [], []
    prev = None          # the layer below (may be empty)
    started = False      # a non-empty layer has been seen: the part has left the bed
    r = min_width / 2 - 0.01
    for z, cs in sliced:
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
                if cantilever and kind == "bridge":
                    out = _past_supports(p, touch, step)
                    if out > max_ledge:
                        kind, d = "past_supports", out
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


def run(m, layer=None):
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
        elif f["kind"] == "past_supports":
            out.append(Finding("overhang_past_supports", f["dist"], "reach_mm",
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


def scan_posts(m, layer=None):
    """Overhangs carried only by thin posts, and slender columns. Port of the original post
    check: {"overhang": [...], "slender": [...]} with the same fields."""
    layer = L.LAYER if layer is None else layer
    z0, sliced = slices_of(m, layer)
    step = layer * L.STEP_FACTOR
    prev_isl, prev = [], None      # islands of the layer below: (outline, thin, stack height, width, column id)
    oh, cols = [], {}
    for z, cs in sliced:
        isl = []
        for p in cs.decompose():
            a = p.area()
            if a < 0.05:
                continue
            w = inscribed_width(p) if a < L.POST_WIDE_AREA else 99
            thin = w < L.POST_THIN_WIDTH or a < L.POST_THIN_AREA
            h, src = 0.0, None
            if thin:
                for (q, qs, qh, qw, qid) in prev_isl:
                    if qs and (p ^ q).area() > 0.3 * min(a, q.area()):
                        if qh >= h:
                            h, src = qh, qid
                h += layer
            cid = src if src is not None else (round(z, 2), _centre(p))
            if thin:
                c = cols.setdefault(cid, {"z0": z, "z1": z, "ws": [], "xy": _centre(p)})
                c["z1"] = z
                c["ws"].append(max(w, 0.1))
            isl.append((p, thin, h, w, cid))
        if prev is not None and not cs.is_empty() and z - z0 > layer:
            for p in (cs - _off(prev, step)).decompose():
                if p.area() < L.POST_OVERHANG_AREA:
                    continue
                d = _reach(p, prev)
                if d <= L.value("max_ledge"):
                    continue
                ring = _off(p, step + 0.4)
                anchors = [(q, qs, qh, qw) for (q, qs, qh, qw, _) in prev_isl if (ring ^ q).area() > 0.02]
                if not anchors or not all(a[1] for a in anchors):
                    continue           # nothing under it (the layer check's job) or a solid anchor
                oh.append({"kind": "beam-overhang", "z": round(z, 2), "xy": _centre(p),
                           "area": round(p.area(), 1), "reach": round(d, 1), "n_anchor": len(anchors),
                           "anchor_w": round(min(a[3] for a in anchors), 2),
                           "anchor_area": round(sum(a[0].area() for a in anchors), 1),
                           "post_h": round(max(a[2] for a in anchors), 1)})
        prev, prev_isl = cs, isl
    for c in cols.values():        # typical width over the column (a thin sign on top is not the post)
        c["w"] = float(np.median(c.pop("ws")))
    slender = [dict(c, h=round(c["z1"] - c["z0"], 1)) for c in cols.values()
               if c["z1"] - c["z0"] > L.COLUMN_MIN_HEIGHT
               and (c["z1"] - c["z0"]) / max(c["w"], 0.3) > L.value("column_ratio")]
    return {"overhang": _merge_posts(oh), "slender": slender}


def _merge_posts(items, tol=4.0):
    out = []
    for it in items:
        for f in out:
            if f["kind"] == it["kind"] and abs(f["xy"][0] - it["xy"][0]) < tol + f["area"] ** .5 / 2 and \
               abs(f["xy"][1] - it["xy"][1]) < tol + f["area"] ** .5 / 2 and it["z"] - f["z1"] < 1.01:
                f["z1"] = it["z"]
                for k in ("area", "reach", "post_h"):
                    f[k] = max(f[k], it[k])
                f["anchor_w"] = min(f["anchor_w"], it["anchor_w"])
                break
        else:
            out.append(dict(it, z1=it["z"]))
    return out


def run_posts(m, layer=None):
    res = scan_posts(m, layer)
    out = []
    for f in res["overhang"]:
        serious = f["post_h"] > L.POST_FAIL_HEIGHT and f["area"] > L.POST_FAIL_AREA
        out.append(Finding("thin_post_overhang" if serious else "thin_post_overhang_small",
                           f["area"], "area_mm2", f["xy"][0], f["xy"][1], f["z"], f["z1"],
                           f["area"], f["anchor_w"]))
    for c in res["slender"]:
        out.append(Finding("slender_column", round(c["h"] / max(c["w"], 0.3), 1), "ratio",
                           c["xy"][0], c["xy"][1], round(c["z0"], 2), round(c["z1"], 2), 0.0,
                           round(c["w"], 2)))
    return out


def scan_supports(m, layer=None):
    """Where a slicer with supports on would put them: per layer, the area not carried by the
    layer below, keeping patches at least support_min_width wide.
    Returns [(z, outline, layer index, base layer index or None)]; None = stands on the plate."""
    z0, sliced = slices_of(m, layer)
    cs_at = [cs for _, cs in sliced]
    minw = L.value("support_min_width")
    out = []
    for i in range(1, len(cs_at)):
        if cs_at[i].is_empty():
            continue
        d = cs_at[i] - _off(cs_at[i - 1], L.SUPPORT_GROW)
        if d.is_empty():
            continue
        d = _off(_off(d, -minw / 2), minw / 2 + 0.01)
        for p in d.decompose():
            if p.area() < L.SUPPORT_MIN_AREA:
                continue
            base = None
            for j in range(i - 2, -1, -1):
                if not cs_at[j].is_empty() and (cs_at[j] ^ p).area() > L.SUPPORT_BASE_SHARE * p.area():
                    base = j
                    break
            out.append((round(float(sliced[i][0]), 2), p, i, base))
    return out


def _tool_reach(outline, frame):
    """The part of a layer's empty space that a tool tool_gap wide can reach from outside."""
    r = L.value("tool_gap") / 2
    core = _off(frame - outline, -r)
    fb = frame.bounds()
    outer = None
    for c in core.decompose():
        b = c.bounds()
        if b[0] <= fb[0] + r + 0.05 or b[1] <= fb[1] + r + 0.05 or b[2] >= fb[2] - r - 0.05 or b[3] >= fb[3] - r - 0.05:
            outer = c if outer is None else outer + c
    return None if outer is None else _off(outer, r)


def run_supports(m, layer=None):
    from manifold3d import CrossSection
    layer = L.LAYER if layer is None else layer
    z0, sliced = slices_of(m, layer)
    bb = m.bounding_box()
    pad = 2 * L.value("tool_gap")
    frame = CrossSection.square([bb[3] - bb[0] + 2 * pad, bb[4] - bb[1] + 2 * pad]).translate([bb[0] - pad, bb[1] - pad])
    reach_at = {}
    out = []
    for z, p, i, base in scan_supports(m, layer):
        x, y = _centre(p)
        area = round(p.area(), 1)
        if base is None:
            out.append(Finding("support_on_plate", area, "area_mm2", x, y, z, z, area))
            continue
        # the support would stand in the layers between its base and the patch: can a tool get
        # to it there? Look at the lowest, the middle and the highest of those layers.
        gap = sorted({base + 1, (base + i) // 2, i - 1})
        reachable = False
        for k in gap:
            if k not in reach_at:
                reach_at[k] = _tool_reach(sliced[k][1], frame)
            # Removable when at least half of the patch is where a tool fits, or within half a
            # tool's width of such a place (a shallow recess such as a narrow window head).
            # A room behind a slit fails this: only the slit's own ceiling is near the outside.
            if reach_at[k] is not None:
                near = _off(reach_at[k], L.value("tool_gap") / 2)
                if (p ^ near).area() >= 0.5 * p.area():
                    reachable = True
                    break
        out.append(Finding("support_on_model" if reachable else "support_enclosed", area, "area_mm2",
                           x, y, z, z, area, round((i - base) * layer, 1)))
    return out
