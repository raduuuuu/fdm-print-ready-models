"""A small waiting shelter, built to the rules in SKILL.md. Run it to write shelter.stl:

    python examples/shelter/shelter.py            writes shelter.stl next to this file
    python examples/shelter/shelter.py --preview  also draws preview.png

Every size is a named constant, and each feature says which rule it follows. The part prints
upright, floor on the bed, with no supports.
"""
import math
import os
import sys

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold

HERE = os.path.dirname(os.path.abspath(__file__))

WIDTH, DEPTH = 50.0, 30.0     # outside, mm
WALL = 2.4                    # six extrusion lines; also carries the roof
FLOOR = 2.0
EAVE = 22.0                   # height of the side walls
ROOF_ANGLE = 45.0             # steeper than the 35 degree roof limit, and its underside is a 45 degree overhang
ROOF_THICK = 2.4              # measured square to the roof
FILLET = 2.0                  # where walls meet the floor: horizontal inner corners get a fillet
WINDOW_W, WINDOW_SILL, WINDOW_SPRING = 10.0, 8.0, 13.0   # pointed head: no flat bridge, nothing for supports to hold
BENCH_DEPTH, BENCH_TOP, BENCH_LIP = 5.0, 10.0, 1.0       # a corbel: its underside is a 45 degree slope from the wall


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def along_y(points, y0, y1):
    """A solid with this x-z outline, from y0 to y1."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    pts = points if area > 0 else points[::-1]
    return Manifold.extrude(CrossSection([pts]), y1 - y0).rotate([90, 0, 0]).translate([0, y1, 0])


def along_x(points, x0, x1):
    """A solid with this y-z outline, from x0 to x1."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    pts = points if area > 0 else points[::-1]
    return Manifold.extrude(CrossSection([pts]), x1 - x0).rotate([90, 0, 90]).translate([x0, 0, 0])


def cove(radius, steps=6):
    """Outline of a concave fillet in a corner at the origin: wall along +z, floor along +x."""
    arc = [(radius - radius * math.cos(math.radians(a)), radius - radius * math.sin(math.radians(a)))
           for a in np.linspace(0, 90, steps + 1)]
    return [(0.0, 0.0)] + [(x, z) for x, z in arc][::-1]


def build():
    rise = math.tan(math.radians(ROOF_ANGLE))
    ridge = EAVE + rise * WIDTH / 2
    drop = ROOF_THICK / math.cos(math.radians(ROOF_ANGLE))      # roof thickness measured vertically

    # shell: one outline for walls and roof, so the roof grows out of the walls with no ledge
    shell = along_y([(0, 0), (WIDTH, 0), (WIDTH, EAVE), (WIDTH / 2, ridge), (0, EAVE)], 0, DEPTH)
    inner_eave = EAVE + rise * WALL - drop
    room = along_y([(WALL, FLOOR), (WIDTH - WALL, FLOOR), (WIDTH - WALL, inner_eave),
                    (WIDTH / 2, ridge - drop), (WALL, inner_eave)], WALL, DEPTH + 1)   # open at the front
    part = shell - room

    # fillets where the side walls and the back wall meet the floor
    left = [(WALL + x, FLOOR + z) for x, z in cove(FILLET)]
    right = [(WIDTH - WALL - x, FLOOR + z) for x, z in cove(FILLET)]
    part += along_y(left, WALL, DEPTH) + along_y(right, WALL, DEPTH)
    part += along_x([(WALL + y, FLOOR + z) for y, z in cove(FILLET)], WALL, WIDTH - WALL)

    # bench along the back wall: a corbel growing out of the wall at 45 degrees, so there is no
    # flat underside, with a fillet where its top meets the wall. One outline, one solid.
    y0 = WALL
    fillet = [(y0 + y, BENCH_TOP + z) for y, z in cove(FILLET)][1:]          # from the bench top up the wall
    bench = [(y0, BENCH_TOP - BENCH_LIP - BENCH_DEPTH), (y0 + BENCH_DEPTH, BENCH_TOP - BENCH_LIP),
             (y0 + BENCH_DEPTH, BENCH_TOP)] + fillet
    part += along_x(bench, WALL, WIDTH - WALL)

    # window in the back wall, above the bench, with a pointed head (two 45 degree sides)
    xc, half = WIDTH / 2, WINDOW_W / 2
    z_sill = BENCH_TOP + WINDOW_SILL - 5.0
    z_spring = BENCH_TOP + WINDOW_SPRING - 5.0
    window = along_y([(xc - half, z_sill), (xc + half, z_sill), (xc + half, z_spring),
                      (xc, z_spring + half), (xc - half, z_spring)], -1, WALL + 1)
    return part - window


def write_stl(solid, path):
    mesh = solid.to_mesh()
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts),
                    process=False).export(path)


def preview(solid, path, size=520):
    """A shaded picture of the part, looking into the open front. Plain numpy and a PNG written by
    hand, so the example needs nothing beyond the packages the checks use."""
    import struct
    import zlib
    mesh = solid.to_mesh()
    v, f = np.asarray(mesh.vert_properties)[:, :3].astype(float), np.asarray(mesh.tri_verts)
    az, el = math.radians(180 + 32), math.radians(24)
    v = v - (v.max(0) + v.min(0)) / 2
    rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, math.cos(el), -math.sin(el)], [0, math.sin(el), math.cos(el)]])
    cam = v @ rz.T @ rx.T                      # x right, z up, y towards the viewer is negative
    scale = (size * 0.86) / (cam[:, [0, 2]].max(0) - cam[:, [0, 2]].min(0)).max()
    px = (cam[:, 0] - cam[:, 0].min()) * scale + size * 0.07
    py = size - ((cam[:, 2] - cam[:, 2].min()) * scale + size * 0.07)
    depth = np.full((size, size), np.inf)
    img = np.full((size, size, 3), 255, np.uint8)
    light = np.array([-0.45, -0.75, 0.5])
    for a, b, c in f:
        n = np.cross(cam[b] - cam[a], cam[c] - cam[a])
        ln = np.linalg.norm(n)
        if ln == 0:
            continue
        shade = 0.30 + 0.70 * abs(float(n @ light) / ln)
        xs, ys = px[[a, b, c]], py[[a, b, c]]
        x0, x1 = int(max(xs.min(), 0)), int(min(xs.max() + 1, size - 1))
        y0, y1 = int(max(ys.min(), 0)), int(min(ys.max() + 1, size - 1))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        det = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(det) < 1e-12:
            continue
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / det
        w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / det
        w2 = 1 - w0 - w1
        d = w0 * cam[a, 1] + w1 * cam[b, 1] + w2 * cam[c, 1]
        zb = depth[y0:y1 + 1, x0:x1 + 1]
        hit = (w0 >= 0) & (w1 >= 0) & (w2 >= 0) & (d < zb)
        zb[hit] = d[hit]
        img[y0:y1 + 1, x0:x1 + 1][hit] = (np.array([222, 168, 86]) * shade).astype(np.uint8)
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(size))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    part = build()
    write_stl(part, os.path.join(HERE, "shelter.stl"))
    if "--preview" in sys.argv:
        preview(part, os.path.join(HERE, "preview.png"))
    print("volume %.1f mm3" % part.volume())
