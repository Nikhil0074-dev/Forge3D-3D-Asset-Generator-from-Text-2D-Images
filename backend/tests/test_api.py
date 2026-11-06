import io, time, pytest
from PIL import Image
from conftest import wait
from app import main, jobs, db
from app.providers.base import Provider, ProviderStatus
import app.main as m


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_text_generation_end_to_end(client):
    r = client.post("/api/generation/text", json={"prompt": "A futuristic silver robotic dog", "style": "realistic", "quality": "high"})
    assert r.status_code == 202 and r.json()["status"] == "queued"
    final = wait(client, r.json()["job_id"])
    assert final["status"] == "completed" and final["progress"] == 100
    a = client.get(f"/api/assets/{final['asset_id']}").json()
    assert a["stats"]["triangle_count"] > 0 and a["format"] == "glb"
    g = client.get(f"/api/assets/{a['asset_id']}/preview")
    assert g.status_code == 200 and g.content[:4] == b"glTF"
    t = client.get(a["thumbnail"])
    assert t.headers["content-type"] == "image/png" and t.content[:4] == b"\x89PNG"
    d = client.get(f"/api/assets/{a['asset_id']}/download")
    assert "attachment" in d.headers["content-disposition"] or d.headers["content-disposition"]


def test_progress_observed(client):
    jid = client.post("/api/generation/text", json={"prompt": "castle"}).json()["job_id"]
    seen = set()
    while True:
        r = client.get(f"/api/generation/{jid}").json(); seen.add(r["status"])
        if r["status"] == "completed": break
        time.sleep(0.02)
    assert "completed" in seen


@pytest.mark.parametrize("body,code", [({"prompt": ""}, 422), ({"prompt": "   "}, 422), ({}, 422),
                                       ({"prompt": "x" * 1001}, 422), ({"prompt": "chair", "output_format": "obj"}, 422)])
def test_text_validation(client, body, code):
    assert client.post("/api/generation/text", json=body).status_code == code


def test_image_generation(client, png):
    r = client.post("/api/generation/image", files={"file": ("../../evil.png", png, "image/png")}, data={"prompt": "robot"})
    assert r.status_code == 202
    final = wait(client, r.json()["job_id"])
    assert final["status"] == "completed" and final["generation_type"] == "image-to-3d"
    assert client.get(f"/api/assets/{final['asset_id']}").json()["generation_type"] == "image-to-3d"


def test_image_rejections(client, png, monkeypatch):
    assert client.post("/api/generation/image", files={"file": ("a.png", b"GIF89a....", "image/png")}).status_code == 415
    assert client.post("/api/generation/image", files={"file": ("a.txt", b"hello world", "text/plain")}).status_code == 415
    assert client.post("/api/generation/image", files={"file": ("a.png", b"\x89PNG\r\n\x1a\nbroken", "image/png")}).status_code == 422
    monkeypatch.setattr(m.config, "MAX_UPLOAD_BYTES", 10)
    assert client.post("/api/generation/image", files={"file": ("a.png", png, "image/png")}).status_code == 413
    monkeypatch.setattr(m.config, "MAX_UPLOAD_BYTES", 10 ** 7); monkeypatch.setattr(m.config, "MAX_IMAGE_DIM", 10)
    assert client.post("/api/generation/image", files={"file": ("a.png", png, "image/png")}).status_code == 422


def test_job_404_and_cancel(client, monkeypatch):
    assert client.get("/api/generation/job_nope").status_code == 404
    assert client.post("/api/generation/job_nope/cancel").status_code == 404
    monkeypatch.setattr(m.config, "MOCK_DURATION", 5)
    from app.providers.mock_provider import MockProvider
    monkeypatch.setattr(m, "_provider", MockProvider(5))
    jid = client.post("/api/generation/text", json={"prompt": "slow"}).json()["job_id"]
    assert client.post(f"/api/generation/{jid}/cancel").json()["status"] == "cancelled"
    time.sleep(0.3)
    assert client.get(f"/api/generation/{jid}").json()["status"] == "cancelled"
    assert client.post(f"/api/generation/{jid}/cancel").status_code == 409


def test_library_search_rename_delete(client, make_asset):
    a1, a2 = make_asset("unique zebra chair"), make_asset("purple sword")
    names = [x["asset_id"] for x in client.get("/api/assets", params={"search": "zebra"}).json()]
    assert a1 in names and a2 not in names
    assert a1 in [x["asset_id"] for x in client.get("/api/assets", params={"type": "text-to-3d"}).json()]
    assert client.get("/api/assets", params={"type": "image-to-3d", "search": "zebra"}).json() == []
    assert client.patch(f"/api/assets/{a1}", json={"name": "Renamed"}).json()["name"] == "Renamed"
    assert client.patch(f"/api/assets/{a1}", json={"name": ""}).status_code == 422
    assert client.delete(f"/api/assets/{a1}").status_code == 204
    assert client.get(f"/api/assets/{a1}").status_code == 404
    assert client.get(f"/api/assets/{a1}/preview").status_code == 404
    assert client.delete(f"/api/assets/{a1}").status_code == 404


def test_exports(client, make_asset):
    import zipfile, json
    a = make_asset("blue car")
    g = client.post(f"/api/assets/{a}/export", json={"format": "glb"})
    assert g.content[:4] == b"glTF"
    t = client.post(f"/api/assets/{a}/export", json={"format": "gltf"})
    assert json.loads(t.content)["asset"]["version"] == "2.0" and ".gltf" in t.headers["content-disposition"]
    o = client.post(f"/api/assets/{a}/export", json={"format": "OBJ"})
    assert sorted(zipfile.ZipFile(io.BytesIO(o.content)).namelist())[0].endswith(".mtl")
    assert client.post(f"/api/assets/{a}/export", json={"format": "stl"}).status_code == 422
    assert client.post("/api/assets/asset_x/export", json={"format": "glb"}).status_code == 404


def test_provider_failure_and_bad_model_mark_job_failed(client, monkeypatch):
    class Bad(Provider):
        name = "bad"
        def __init__(self, st): self.st = st
        def submit_text(self, p, o): return "h"
        def poll(self, h): return self.st
    monkeypatch.setattr(m, "_provider", Bad(ProviderStatus("failed", message="quota exceeded")))
    r = wait(client, client.post("/api/generation/text", json={"prompt": "x"}).json()["job_id"])
    assert r["status"] == "failed" and "quota" in r["error"]
    monkeypatch.setattr(m, "_provider", Bad(ProviderStatus("completed", 100, "", b"not a glb at all")))
    r = wait(client, client.post("/api/generation/text", json={"prompt": "x"}).json()["job_id"])
    assert r["status"] == "failed" and "GLB" in r["error"]


def test_indeterminate_progress_is_null(client, monkeypatch):
    class Slow(Provider):
        name = "slow"
        def submit_text(self, p, o): return "h"
        def poll(self, h): return ProviderStatus("processing", None, "working")
    monkeypatch.setattr(m, "_provider", Slow())
    jid = client.post("/api/generation/text", json={"prompt": "x"}).json()["job_id"]
    time.sleep(0.3)
    r = client.get(f"/api/generation/{jid}").json()
    assert r["status"] == "processing" and r["progress"] is None
    client.post(f"/api/generation/{jid}/cancel")


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(m.config, "RATE_LIMIT_PER_MIN", 2)
    m._hits.clear()
    codes = [client.post("/api/generation/text", json={"prompt": "ring"}).status_code for _ in range(3)]
    assert codes == [202, 202, 429]
    m._hits.clear()
