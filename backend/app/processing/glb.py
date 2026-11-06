"""Minimal GLB writer / reader / analyzer / converters (no external 3D libs)."""
import base64, io, json, struct, zipfile
import numpy as np

CT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


class ModelError(ValueError):
    pass


def build_glb(parts):
    """parts: list of dict(positions Nx3, normals Nx3, indices, color rgba, name, metal, rough)."""
    bin_data, views, accs, meshes, mats, nodes = bytearray(), [], [], [], [], []

    def add(arr, target):
        while len(bin_data) % 4:
            bin_data.append(0)
        views.append({"buffer": 0, "byteOffset": len(bin_data), "byteLength": arr.nbytes, "target": target})
        bin_data.extend(arr.tobytes())
        return len(views) - 1

    for i, p in enumerate(parts):
        pos = np.ascontiguousarray(p["positions"], np.float32)
        nor = np.ascontiguousarray(p["normals"], np.float32)
        idx = np.ascontiguousarray(p["indices"], np.uint32)
        a = len(accs)
        accs.append({"bufferView": add(pos, 34962), "componentType": 5126, "count": len(pos), "type": "VEC3",
                     "min": pos.min(0).tolist(), "max": pos.max(0).tolist()})
        accs.append({"bufferView": add(nor, 34962), "componentType": 5126, "count": len(nor), "type": "VEC3"})
        accs.append({"bufferView": add(idx, 34963), "componentType": 5125, "count": len(idx), "type": "SCALAR"})
        c = [float(x) for x in p["color"]]
        mats.append({"name": p.get("name", f"mat{i}"), "pbrMetallicRoughness": {
            "baseColorFactor": c, "metallicFactor": float(p.get("metal", 0.3)),
            "roughnessFactor": float(p.get("rough", 0.6))}})
        meshes.append({"name": p.get("name", f"part{i}"), "primitives": [
            {"attributes": {"POSITION": a, "NORMAL": a + 1}, "indices": a + 2, "material": i}]})
        nodes.append({"mesh": i, "name": p.get("name", f"part{i}")})
    while len(bin_data) % 4:
        bin_data.append(0)
    js = {"asset": {"version": "2.0", "generator": "3d-asset-generator"}, "scene": 0,
          "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes, "meshes": meshes,
          "materials": mats, "accessors": accs, "bufferViews": views,
          "buffers": [{"byteLength": len(bin_data)}]}
    jb = json.dumps(js, separators=(",", ":")).encode()
    jb += b" " * (-len(jb) % 4)
    total = 12 + 8 + len(jb) + 8 + len(bin_data)
    return (struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(jb), 0x4E4F534A) + jb
            + struct.pack("<II", len(bin_data), 0x004E4942) + bytes(bin_data))


def parse_glb(data: bytes):
    if len(data) < 20 or data[:4] != b"glTF":
        raise ModelError("Not a GLB file (bad magic)")
    ver, length = struct.unpack("<II", data[4:12])
    if ver != 2 or length > len(data):
        raise ModelError("Unsupported or truncated GLB")
    js, binc, off = None, b"", 12
    while off + 8 <= length:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            try:
                js = json.loads(chunk)
            except json.JSONDecodeError as e:
                raise ModelError(f"Invalid JSON chunk: {e}")
        elif ctype == 0x004E4942:
            binc = chunk
        off += 8 + clen
    if js is None:
        raise ModelError("GLB has no JSON chunk")
    for b in js.get("buffers", []):
        if "uri" in b and not b["uri"].startswith("data:"):
            raise ModelError("External buffer references are not allowed")
    return js, binc


def _read(js, binc, ai):
    try:
        a = js["accessors"][ai]
        bv = js["bufferViews"][a["bufferView"]]
        n, ncomp, ch = a["count"], NC[a["type"]], CT[a["componentType"]]
    except (KeyError, IndexError):
        raise ModelError("Malformed accessor")
    size = np.dtype(ch).itemsize
    stride = bv.get("byteStride") or size * ncomp
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    if n == 0 or start + stride * (n - 1) + size * ncomp > len(binc):
        raise ModelError("Accessor reads beyond buffer")
    buf = np.frombuffer(binc, dtype=np.uint8)
    rows = (start + np.arange(n)[:, None] * stride + np.arange(size * ncomp)[None, :])
    return np.ascontiguousarray(buf[rows]).view(np.dtype(ch)).reshape(n, ncomp)


def extract_primitives(data: bytes):
    js, binc = parse_glb(data)
    out = []
    for mesh in js.get("meshes", []):
        for pr in mesh.get("primitives", []):
            at = pr.get("attributes", {})
            if "POSITION" not in at:
                continue
            pos = _read(js, binc, at["POSITION"]).astype(np.float32)
            idx = _read(js, binc, pr["indices"]).reshape(-1).astype(np.uint32) if "indices" in pr \
                else np.arange(len(pos), dtype=np.uint32)
            if len(idx) % 3 or (len(idx) and idx.max() >= len(pos)):
                raise ModelError("Invalid index buffer")
            nor = _read(js, binc, at["NORMAL"]).astype(np.float32) if "NORMAL" in at else None
            color = [0.8, 0.8, 0.8, 1.0]
            if "material" in pr:
                m = js["materials"][pr["material"]]
                color = m.get("pbrMetallicRoughness", {}).get("baseColorFactor", color)
            out.append({"positions": pos, "normals": nor, "indices": idx, "color": color,
                        "name": mesh.get("name", "mesh")})
    if not out:
        raise ModelError("Model contains no mesh geometry")
    return out


def analyze(data: bytes):
    prims = extract_primitives(data)
    js, _ = parse_glb(data)
    allp = np.concatenate([p["positions"] for p in prims])
    mn, mx = allp.min(0), allp.max(0)
    return {
        "vertex_count": int(sum(len(p["positions"]) for p in prims)),
        "triangle_count": int(sum(len(p["indices"]) // 3 for p in prims)),
        "mesh_count": len(js.get("meshes", [])),
        "material_count": len(js.get("materials", [])),
        "texture_count": len(js.get("textures", [])),
        "width": float(mx[0] - mn[0]), "height": float(mx[1] - mn[1]), "depth": float(mx[2] - mn[2]),
        "file_size": len(data),
    }


def glb_to_gltf(data: bytes) -> bytes:
    js, binc = parse_glb(data)
    js = dict(js)
    js["buffers"] = [{"byteLength": len(binc),
                      "uri": "data:application/octet-stream;base64," + base64.b64encode(binc).decode()}]
    return json.dumps(js).encode()


def glb_to_obj_zip(data: bytes, name="model") -> bytes:
    prims = extract_primitives(data)
    obj, mtl, base = [f"mtllib {name}.mtl"], [], 1
    for i, p in enumerate(prims):
        c = p["color"]
        mtl += [f"newmtl mat{i}", f"Kd {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}", f"d {c[3]:.4f}", ""]
        obj += [f"o {p['name']}_{i}", f"usemtl mat{i}"]
        obj += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in p["positions"]]
        has_n = p["normals"] is not None
        if has_n:
            obj += [f"vn {x:.6f} {y:.6f} {z:.6f}" for x, y, z in p["normals"]]
        fmt = (lambda k: f"{k + base}//{k + base}") if has_n else (lambda k: f"{k + base}")
        obj += [f"f {fmt(a)} {fmt(b)} {fmt(c_)}" for a, b, c_ in p["indices"].reshape(-1, 3)]
        base += len(p["positions"])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{name}.obj", "\n".join(obj) + "\n")
        z.writestr(f"{name}.mtl", "\n".join(mtl))
    return buf.getvalue()


def thumbnail_png(data: bytes, size=256) -> bytes:
    """Tiny software rasteriser (painter's algorithm, flat shading) for library thumbnails."""
    from PIL import Image, ImageDraw
    prims = extract_primitives(data)
    allp = np.concatenate([p["positions"] for p in prims])
    c, ext = (allp.min(0) + allp.max(0)) / 2, max(float((allp.max(0) - allp.min(0)).max()), 1e-6)
    ry, rx = np.radians(35), np.radians(-20)
    R = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]]) @ \
        np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
    tris = []
    for p in prims:
        v = ((p["positions"] - c) / ext) @ R.T
        t = v[p["indices"].reshape(-1, 3)]
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        shade = 0.35 + 0.65 * np.clip(n @ np.array([0.3, 0.6, 0.75]), 0, 1)
        for tri, s in zip(t, shade):
            tris.append((tri[:, 2].mean(), tri, s, p["color"]))
    tris.sort(key=lambda x: x[0])
    S = size * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for _, tri, s, col in tris:
        pts = [(S / 2 + x * S * 0.8, S / 2 - y * S * 0.8) for x, y, _ in tri]
        d.polygon(pts, fill=tuple(int(min(255, ch * 255 * s)) for ch in col[:3]) + (255,))
    out = io.BytesIO()
    img.resize((size, size), Image.LANCZOS).save(out, "PNG")
    return out.getvalue()
