"""Procedural primitives used by the offline mock provider."""
import numpy as np


def _grid(fn, nu, nv):
    pts = np.array([[fn(u / nu, v / nv) for u in range(nu + 1)] for v in range(nv + 1)])  # (nv+1,nu+1,3)
    idx = []
    for v in range(nv):
        for u in range(nu):
            a = v * (nu + 1) + u
            b, c, d = a + 1, a + nu + 1, a + nu + 2
            idx += [a, c, b, b, c, d]
    return pts.reshape(-1, 3), np.array(idx, np.uint32), (nu + 1, nv + 1)


def _normals(pos, idx):
    n = np.zeros_like(pos)
    t = idx.reshape(-1, 3)
    fn = np.cross(pos[t[:, 1]] - pos[t[:, 0]], pos[t[:, 2]] - pos[t[:, 0]])
    for k in range(3):
        np.add.at(n, t[:, k], fn)
    ln = np.linalg.norm(n, axis=1)
    bad = ln < 1e-4  # degenerate pole / cap-centre vertices: point along the axis away from the centroid
    n[bad] = np.stack([np.zeros(bad.sum()), np.sign(pos[bad, 1] - pos[:, 1].mean()) + (pos[bad, 1] == pos[:, 1].mean()), np.zeros(bad.sum())], 1)
    return (n / np.linalg.norm(n, axis=1, keepdims=True)).astype(np.float32)


def _make(fn, nu, nv, off, scale, color, name, metal=0.3, rough=0.6):
    pos, idx, _ = _grid(fn, nu, nv)
    pos = pos * np.array(scale) + np.array(off)
    return {"positions": pos.astype(np.float32), "normals": _normals(pos, idx), "indices": idx,
            "color": color, "name": name, "metal": metal, "rough": rough}


def sphere(off=(0, 0, 0), scale=(1, 1, 1), **kw):
    f = lambda u, v: (np.sin(np.pi * v) * np.cos(2 * np.pi * u), np.cos(np.pi * v), np.sin(np.pi * v) * np.sin(2 * np.pi * u))
    return _make(f, 28, 20, off, scale, **kw)


def cylinder(off=(0, 0, 0), scale=(1, 1, 1), top=1.0, **kw):
    """Unit cylinder radius 1 / height 1 (centered); `top` tapers radius (0 = cone). Caps closed via rim rows."""
    def f(u, v):
        if v < 0.04: r, y = v / 0.04, -0.5
        elif v > 0.96: r, y = (1 - (v - 0.96) / 0.04) * top, 0.5
        else:
            t = (v - 0.04) / 0.92
            r, y = 1 + (top - 1) * t, -0.5 + t
        return (r * np.cos(2 * np.pi * u), y, r * np.sin(2 * np.pi * u))
    return _make(f, 28, 25, off, scale, **kw)


def box(off=(0, 0, 0), scale=(1, 1, 1), **kw):
    p = np.array([[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)], np.float32)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    pos, idx = [], []
    for f in faces:
        b = len(pos)
        pos += [p[i] for i in f]
        idx += [b, b + 1, b + 2, b, b + 2, b + 3]
    pos = np.array(pos) * np.array(scale) + np.array(off)
    idx = np.array(idx, np.uint32)
    # flat normals per face
    n = np.repeat(np.array([_fn(pos[i * 4:i * 4 + 4]) for i in range(6)]), 4, axis=0)
    return {"positions": pos.astype(np.float32), "normals": n.astype(np.float32), "indices": idx,
            "color": kw["color"], "name": kw["name"], "metal": kw.get("metal", .3), "rough": kw.get("rough", .6)}


def _fn(q):
    n = np.cross(q[1] - q[0], q[2] - q[0])
    return n / (np.linalg.norm(n) + 1e-9)


def torus(off=(0, 0, 0), scale=(1, 1, 1), R=1.0, r=0.3, **kw):
    f = lambda u, v: ((R + r * np.cos(2 * np.pi * v)) * np.cos(2 * np.pi * u), r * np.sin(2 * np.pi * v),
                      (R + r * np.cos(2 * np.pi * v)) * np.sin(2 * np.pi * u))
    return _make(f, 36, 16, off, scale, **kw)
