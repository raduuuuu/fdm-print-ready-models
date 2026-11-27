"""Surface checks: what the angle of each face says, without slicing.

All angles are measured from the bed: 0 degrees is flat, 90 degrees is a vertical wall.

  slope_too_shallow   a top surface between flat and roof_min_angle. It prints as wide separate
                      steps. Narrow bands (fillets) are ignored: see fillet_band.
  overhang_too_flat   an underside flatter than overhang_fail_angle that runs out further than a
                      ledge may
  overhang_shallow    the same between overhang_fail_angle and overhang_target_angle (a warning)
  overhang_narrow     an underside flatter than overhang_fail_angle that is too narrow for the
                      rule above but runs out further than a ledge may (a warning)
  sharp_corner_horizontal, sharp_corner_vertical
                      sharp inner corners. Reported for a person to judge; never a failure.

Flat undersides are bridges and ledges, which the layer check measures. They are left out here.

This module only measures. limits.py holds the numbers and how serious each kind is.
"""
import numpy as np

import limits as L
from layers import Finding

_MESH = []     # [solid, mesh] for the last solid, compared by identity (see layers.slices_of)


def mesh_of(m):
    import trimesh
    if not (_MESH and _MESH[0] is m):
        raw = m.to_mesh()
        _MESH[:] = [m, trimesh.Trimesh(np.asarray(raw.vert_properties)[:, :3],
                                       np.asarray(raw.tri_verts), process=False)]
    return _MESH[1]


def _angle_from_bed(normals):
    """Angle of each face from the bed, 0 to 90 degrees, whichever way it faces."""
    return np.degrees(np.arccos(np.clip(np.abs(normals[:, 2]), 0.0, 1.0)))


def _regions(mesh, mask):
    """Connected groups of the faces selected by `mask` (faces sharing an edge), as index arrays.
    A small union-find, so no graph library is needed."""
    adj = mesh.face_adjacency
    pairs = adj[mask[adj[:, 0]] & mask[adj[:, 1]]]
    parent = np.arange(len(mask))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for i in np.nonzero(mask)[0]:
        groups.setdefault(find(i), []).append(i)
    return [np.array(g) for g in groups.values()]


def _band_width(mesh, faces, flat=False):
    """Typical width of a region: twice its area over the length of its outline. A long band
    measures as its width; a compact patch as about half its side. With flat=True both are
    measured in plan, which gives the horizontal run of a sloped band."""
    v = mesh.vertices[:, :2] if flat else mesh.vertices
    tri = mesh.faces[faces]
    a, b, c = v[tri[:, 0]], v[tri[:, 1]], v[tri[:, 2]]
    u, w = b - a, c - a
    if flat:
        area = np.abs(u[:, 0] * w[:, 1] - u[:, 1] * w[:, 0]).sum() / 2
    else:
        area = np.linalg.norm(np.cross(u, w), axis=1).sum() / 2
    edges = np.sort(np.vstack([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    uniq, count = np.unique(edges, axis=0, return_counts=True)
    rim = uniq[count == 1]
    outline = np.linalg.norm(v[rim[:, 0]] - v[rim[:, 1]], axis=1).sum()
    return (2 * area / outline if outline > 0 else 0.0), area


def _where(mesh, faces):
    w = mesh.area_faces[faces]
    c = (mesh.triangles_center[faces] * w[:, None]).sum(0) / w.sum()
    z = mesh.vertices[mesh.faces[faces].ravel(), 2]
    return round(float(c[0]), 1), round(float(c[1]), 1), round(float(z.min()), 2), round(float(z.max()), 2)


def _run_out(mesh, faces, ang):
    """How far a sloped underside runs out past its foot, in plan.

    A flat-sided underside leans one way: its run is its extent along that direction. This is
    its real reach however narrow it is; _band_width reads a 1.6 mm wide arm that runs 10 mm
    out as 1.4 mm. An underside that leans several ways (a cone, the two sides of an arch) has
    no single direction: its run is its height over the tangent of its mean angle.
    """
    w = mesh.area_faces[faces]
    lean = mesh.face_normals[faces][:, :2]
    lean = lean / np.linalg.norm(lean, axis=1)[:, None]
    mean = (lean * w[:, None]).sum(0) / w.sum()
    v = mesh.vertices[np.unique(mesh.faces[faces])]
    if np.linalg.norm(mean) > 0.9:
        along = v[:, :2] @ (mean / np.linalg.norm(mean))
        return float(along.max() - along.min())
    angle = np.radians(float((ang[faces] * w).sum() / w.sum()))
    return float((v[:, 2].max() - v[:, 2].min()) / np.tan(angle))


def run_slopes(m):
    """Top surfaces that are neither flat nor steep enough, as regions wider than a fillet."""
    mesh = mesh_of(m)
    ang = _angle_from_bed(mesh.face_normals)
    up = mesh.face_normals[:, 2] > 0
    shallow = up & (ang > L.FLAT_ANGLE) & (ang < L.value("roof_min_angle") - L.ANGLE_MARGIN)
    out = []
    for faces in _regions(mesh, shallow):
        width, area = _band_width(mesh, faces)
        if width < L.value("fillet_band") or area < L.SLOPE_MIN_AREA:
            continue
        w = mesh.area_faces[faces]
        mean = float((ang[faces] * w).sum() / w.sum())
        x, y, z0, z1 = _where(mesh, faces)
        out.append(Finding("slope_too_shallow", round(mean, 1), "angle_deg", x, y, z0, z1,
                           round(float(area), 1), round(float(width), 2)))
    return out


def run_overhangs(m):
    """Sloped undersides flatter than the overhang limits that run out further than a ledge may."""
    mesh = mesh_of(m)
    ang = _angle_from_bed(mesh.face_normals)
    down = mesh.face_normals[:, 2] < 0
    out = []
    bands = (("overhang_too_flat", L.FLAT_ANGLE, L.value("overhang_fail_angle")),
             ("overhang_shallow", L.value("overhang_fail_angle"), L.value("overhang_target_angle")))
    for band, lo, hi in bands:
        sel = down & (ang > lo) & (ang < hi - L.ANGLE_MARGIN)
        for faces in _regions(mesh, sel):
            kind = band
            run, plan_area = _band_width(mesh, faces, flat=True)
            if plan_area < L.SURFACE_MIN_AREA:
                continue
            w = mesh.area_faces[faces]
            limit = L.value("max_ledge") + L.RUN_TOL
            if run <= limit:
                # Too narrow for the rule above. Its real reach still counts once it is larger
                # than the narrow undersides that are known to print.
                if kind != "overhang_too_flat" or float(w.sum()) < L.NARROW_UNDERSIDE_MIN_AREA:
                    continue
                run = _run_out(mesh, faces, ang)
                if run <= limit:
                    continue
                kind = "overhang_narrow"
            flattest = float(ang[faces].min())
            x, y, z0, z1 = _where(mesh, faces)
            out.append(Finding(kind, round(flattest, 1), "angle_deg", x, y, z0, z1,
                               round(float(w.sum()), 1), round(float(run), 2)))
    return out


def run_corners(m):
    """Sharp inner corners, for a person to judge. Horizontal ones are listed one by one
    (the skill makes fillets mandatory there); vertical ones are counted."""
    mesh = mesh_of(m)
    sharp = (~mesh.face_adjacency_convex) & (np.degrees(mesh.face_adjacency_angles) >= L.SHARP_ANGLE)
    if not sharp.any():
        return []
    e = mesh.face_adjacency_edges[sharp]
    p, q = mesh.vertices[e[:, 0]], mesh.vertices[e[:, 1]]
    d = q - p
    length = np.linalg.norm(d, axis=1)
    ok = length > 1e-9
    p, q, d, length = p[ok], q[ok], d[ok] / length[ok][:, None], length[ok]
    flip = (d[:, 2] < -1e-9) | ((np.abs(d[:, 2]) <= 1e-9) & ((d[:, 0] < -1e-9) | ((np.abs(d[:, 0]) <= 1e-9) & (d[:, 1] < 0))))
    d[flip] *= -1
    foot = p - (p * d).sum(1)[:, None] * d            # the point of each edge's line nearest the origin
    lines = {}                                         # edges on one straight line are one corner
    for i in range(len(length)):
        key = (tuple(np.round(d[i], 2)), tuple(np.round(foot[i], 1)))
        g = lines.setdefault(key, {"len": 0.0, "pts": [], "dz": abs(d[i, 2])})
        g["len"] += float(length[i])
        g["pts"] += [p[i], q[i]]
    out, vertical_len, vertical_n = [], 0.0, 0
    horizontal = []
    for g in lines.values():
        if g["len"] < L.value("corner_min_edge"):
            continue
        pts = np.array(g["pts"])
        if g["dz"] < 0.2:
            c = pts.mean(0)
            horizontal.append(Finding("sharp_corner_horizontal", round(g["len"], 1), "length_mm",
                                      round(float(c[0]), 1), round(float(c[1]), 1),
                                      round(float(pts[:, 2].min()), 2), round(float(pts[:, 2].max()), 2), 0.0))
        elif g["dz"] > 0.98:
            vertical_len += g["len"]
            vertical_n += 1
    horizontal.sort(key=lambda f: -f.value)
    out += horizontal[:L.CORNER_LIST_MAX]
    if vertical_n:
        out.append(Finding("sharp_corner_vertical", round(vertical_len, 1), "total_length_mm",
                           0.0, 0.0, 0.0, 0.0, float(vertical_n)))
    return out
