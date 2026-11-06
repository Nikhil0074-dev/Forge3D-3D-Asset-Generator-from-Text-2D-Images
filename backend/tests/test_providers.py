import io, json, time, httpx, pytest
from PIL import Image
from app.providers.mock_provider import MockProvider, build_model, pick_color
from app.providers.tripo_provider import TripoProvider
from app.providers.base import ProviderError
from app.processing import glb
from app.providers import get_provider


@pytest.mark.parametrize("prompt,min_meshes", [("wooden chair", 6), ("golden sword", 4), ("stone castle", 9), ("sports car", 6),
                                              ("robotic dog", 7), ("knight helmet", 2), ("sci-fi robot", 8), ("gold ring", 1),
                                              ("oak tree", 2), ("something abstract", 2)])
def test_mock_shapes(prompt, min_meshes):
    st = glb.analyze(build_model(prompt))
    assert st["mesh_count"] >= min_meshes and st["triangle_count"] > 0


def test_accent_words_do_not_recolour_body():
    c = pick_color("a sci-fi robot with glowing blue eyes, metallic silver")
    assert c == pick_color("silver") and c[2] < 0.9


def test_mock_color_keywords():
    assert pick_color("a blue car")[2] > 0.8
    assert pick_color("zzz") == pick_color("zzz")  # deterministic


def test_mock_lifecycle():
    p = MockProvider(duration=0.2)
    h = p.submit_text("red chair", {})
    states = set()
    t0 = time.time()
    while time.time() - t0 < 3:
        s = p.poll(h); states.add(s.state)
        if s.state == "completed":
            assert s.model[:4] == b"glTF" and s.progress == 100
            break
        time.sleep(0.02)
    else:
        pytest.fail("never completed")
    assert "completed" in states


def test_mock_cancel_and_unknown():
    p = MockProvider(duration=5)
    h = p.submit_text("x", {})
    assert p.cancel(h) and p.poll(h).state == "failed"
    assert p.poll("nope").state == "failed" and not p.cancel("nope")


def test_mock_empty_prompt_and_bad_image():
    p = MockProvider()
    with pytest.raises(ProviderError): p.submit_text("  ", {})
    with pytest.raises(ProviderError): p.submit_image(b"junk", "a.png", "", {})


def test_mock_image_uses_image_color():
    b = io.BytesIO(); Image.new("RGB", (8, 8), (0, 0, 255)).save(b, "PNG")
    p = MockProvider(duration=0.01); h = p.submit_image(b.getvalue(), "x.png", "robot", {})
    time.sleep(0.05)
    js, _ = glb.parse_glb(p.poll(h).model)
    assert js["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"][2] > 0.9


def test_factory():
    assert get_provider("mock").name == "mock"
    with pytest.raises(ValueError): get_provider("nope")
    with pytest.raises(ProviderError): get_provider("tripo")  # no key configured


def _tripo(handler):
    return TripoProvider("k", "https://api.test/v2", transport=httpx.MockTransport(handler))


def test_tripo_text_flow():
    glbdata = build_model("chair")
    seen = {}

    def h(req):
        seen["auth"] = req.headers["authorization"]
        if req.method == "POST" and req.url.path.endswith("/task"):
            seen["body"] = json.loads(req.content)
            return httpx.Response(200, json={"code": 0, "data": {"task_id": "t1"}})
        if req.url.path.endswith("/task/t1"):
            return httpx.Response(200, json={"code": 0, "data": {"status": "success", "progress": 100,
                                  "output": {"pbr_model": "https://cdn.test/m.glb"}}})
        if req.url.host == "cdn.test":
            return httpx.Response(200, content=glbdata)
        return httpx.Response(404, json={})
    p = _tripo(h)
    t = p.submit_text("a chair", {})
    s = p.poll(t)
    assert t == "t1" and seen["body"] == {"type": "text_to_model", "prompt": "a chair"}
    assert seen["auth"] == "Bearer k" and s.state == "completed" and s.model == glbdata


def test_tripo_image_flow_and_progress():
    def h(req):
        if req.url.path.endswith("/upload"):
            return httpx.Response(200, json={"code": 0, "data": {"image_token": "tok"}})
        if req.url.path.endswith("/task") and req.method == "POST":
            b = json.loads(req.content)
            assert b["type"] == "image_to_model" and b["file"]["file_token"] == "tok" and b["file"]["type"] == "png"
            return httpx.Response(200, json={"code": 0, "data": {"task_id": "t2"}})
        return httpx.Response(200, json={"code": 0, "data": {"status": "running", "progress": 40}})
    p = _tripo(h)
    t = p.submit_image(b"x", "a.png", "", {})
    s = p.poll(t)
    assert s.state == "processing" and s.progress == 40


def test_tripo_errors():
    p = _tripo(lambda r: httpx.Response(200, json={"code": 2002, "message": "insufficient credit"}))
    with pytest.raises(ProviderError, match="insufficient credit"): p.submit_text("x", {})
    p = _tripo(lambda r: httpx.Response(500, text="boom"))
    with pytest.raises(ProviderError, match="non-JSON"): p.submit_text("x", {})
    p = _tripo(lambda r: httpx.Response(200, json={"code": 0, "data": {"status": "failed"}}))
    assert p.poll("t").state == "failed"
    p = _tripo(lambda r: httpx.Response(200, json={"code": 0, "data": {"status": "success", "output": {}}}))
    with pytest.raises(ProviderError, match="no model URL"): p.poll("t")
