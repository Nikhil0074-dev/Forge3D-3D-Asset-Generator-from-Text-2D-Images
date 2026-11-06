import json, zipfile, io, struct, pytest
from app.processing import glb, shapes as S
from app.providers.mock_provider import build_model


def test_roundtrip_stats():
    data = glb.build_glb([S.box(name="b", color=(1, 0, 0, 1))])
    st = glb.analyze(data)
    assert st["vertex_count"] == 24 and st["triangle_count"] == 12
    assert st["mesh_count"] == 1 and st["material_count"] == 1
    assert st["width"] == pytest.approx(1.0) and st["file_size"] == len(data)


def test_header_valid():
    d = glb.build_glb([S.sphere(name="s", color=(1, 1, 1, 1))])
    magic, ver, length = struct.unpack("<4sII", d[:12])
    assert magic == b"glTF" and ver == 2 and length == len(d) and len(d) % 4 == 0


@pytest.mark.parametrize("bad", [b"", b"notaglb" * 10, b"glTF" + b"\x01\x00\x00\x00" + b"\x00" * 20])
def test_rejects_garbage(bad):
    with pytest.raises(glb.ModelError):
        glb.analyze(bad)


def test_truncated_binary_rejected():
    d = glb.build_glb([S.box(name="b", color=(1, 0, 0, 1))])
    with pytest.raises(glb.ModelError):
        glb.analyze(d[:len(d) // 2])


def test_external_buffer_rejected():
    js, binc = glb.parse_glb(glb.build_glb([S.box(name="b", color=(1, 0, 0, 1))]))
    js["buffers"][0]["uri"] = "http://evil.example/x.bin"
    jb = json.dumps(js).encode(); jb += b" " * (-len(jb) % 4)
    d = (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(jb) + 8 + len(binc)) + struct.pack("<II", len(jb), 0x4E4F534A) + jb
         + struct.pack("<II", len(binc), 0x004E4942) + binc)
    with pytest.raises(glb.ModelError, match="External"):
        glb.analyze(d)


def test_gltf_export_embeds_buffer():
    d = glb.build_glb([S.box(name="b", color=(1, 0, 0, 1))])
    js = json.loads(glb.glb_to_gltf(d))
    assert js["buffers"][0]["uri"].startswith("data:application/octet-stream;base64,")
    assert len(js["meshes"]) == 1


def test_obj_zip_contents():
    d = glb.build_glb([S.box(name="b", color=(1, 0, 0, 1)), S.sphere(name="s", color=(0, 1, 0, 1))])
    z = zipfile.ZipFile(io.BytesIO(glb.glb_to_obj_zip(d, "thing")))
    assert sorted(z.namelist()) == ["thing.mtl", "thing.obj"]
    obj, mtl = z.read("thing.obj").decode(), z.read("thing.mtl").decode()
    st = glb.analyze(d)
    assert obj.count("\nv ") == st["vertex_count"]
    assert obj.count("\nf ") == st["triangle_count"]
    assert "mtllib thing.mtl" in obj and mtl.count("newmtl") == 2
    # face indices must stay in range
    nv = st["vertex_count"]
    for line in obj.splitlines():
        if line.startswith("f "):
            assert all(1 <= int(t.split("/")[0]) <= nv for t in line[2:].split())


def test_thumbnail_is_png_with_content():
    from PIL import Image
    im = Image.open(io.BytesIO(glb.thumbnail_png(build_model("red robot"), 128)))
    assert im.size == (128, 128) and im.getbbox() is not None


@pytest.mark.parametrize("kind", ["sphere", "cylinder", "box", "torus"])
def test_shapes_valid(kind):
    p = getattr(S, kind)(name=kind, color=(1, 1, 1, 1))
    assert p["indices"].max() < len(p["positions"]) and len(p["indices"]) % 3 == 0
    import numpy as np
    assert np.allclose(np.linalg.norm(p["normals"], axis=1), 1, atol=1e-3)
