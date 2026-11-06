import os, tempfile
_tmp = tempfile.mkdtemp()
os.environ.update(STORAGE_DIR=_tmp, GEN_PROVIDER="mock", MOCK_DURATION="0.3", RATE_LIMIT_PER_MIN="1000")
import io, time, pytest
from fastapi.testclient import TestClient
from PIL import Image
from app import jobs, main, db
jobs.POLL = 0.05


@pytest.fixture(scope="session")
def client():
    return TestClient(main.app)


@pytest.fixture
def png():
    b = io.BytesIO()
    Image.new("RGB", (64, 48), (200, 30, 30)).save(b, "PNG")
    return b.getvalue()


def wait(client, jid, timeout=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"/api/generation/{jid}").json()
        if r["status"] in ("completed", "failed", "cancelled"):
            return r
        time.sleep(0.05)
    raise AssertionError("job did not finish")


@pytest.fixture
def make_asset(client):
    def _m(prompt="a red chair"):
        jid = client.post("/api/generation/text", json={"prompt": prompt}).json()["job_id"]
        r = wait(client, jid)
        assert r["status"] == "completed", r
        return r["asset_id"]
    return _m
