"""Write tests/fixtures/known_good.stl: a small original part that must pass every shipped check.

A base plate, two walls with a 10 mm ceiling between them, a window with a 12 mm head in a
2.4 mm wall, and a 4 mm post. Rerun after changing the shape:
    python tests/fixtures/make_known_good.py
"""
import os

import numpy as np
import trimesh
from manifold3d import Manifold


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def known_good():
    base = box(0, 60, 0, 40, 0, 2)
    room = box(5, 9, 5, 25, 2, 14) + box(19, 23, 5, 25, 2, 14) + box(5, 23, 5, 25, 14, 16)
    wall = box(30, 56, 5, 7.4, 2, 22) - box(37, 49, 4, 8.4, 8, 16)
    post = box(40, 44, 28, 32, 2, 20)
    return base + room + wall + post


if __name__ == "__main__":
    mesh = known_good().to_mesh()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "known_good.stl")
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts),
                    process=False).export(out)
    print(out)
