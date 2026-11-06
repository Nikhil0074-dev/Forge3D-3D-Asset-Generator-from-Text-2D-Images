"""Tripo3D hosted-API adapter. Endpoint shapes follow Tripo's public docs but have NOT been verified against the live
service in this build (no API key / network). Tests exercise it through an httpx.MockTransport."""
import httpx
from .base import Provider, ProviderStatus, ProviderError

MAP = {"queued": "queued", "running": "processing", "success": "completed", "failed": "failed",
       "cancelled": "failed", "unknown": "failed", "banned": "failed", "expired": "failed"}


class TripoProvider(Provider):
    name = "tripo"

    def __init__(self, api_key, base="https://api.tripo3d.ai/v2/openapi", transport=None):
        if not api_key:
            raise ProviderError("TRIPO_API_KEY is not configured")
        self.client = httpx.Client(base_url=base, headers={"Authorization": f"Bearer {api_key}"},
                                   timeout=60, transport=transport)

    def _check(self, r):
        try:
            body = r.json()
        except Exception:
            raise ProviderError(f"Provider returned non-JSON (HTTP {r.status_code})")
        if r.status_code >= 400 or body.get("code", 0) != 0:
            raise ProviderError(f"Provider error: {body.get('message', r.status_code)}")
        return body.get("data", {})

    def submit_text(self, prompt, opts):
        d = self._check(self.client.post("/task", json={"type": "text_to_model", "prompt": prompt}))
        return d["task_id"]

    def submit_image(self, image, filename, prompt, opts):
        up = self._check(self.client.post("/upload", files={"file": (filename, image)}))
        ext = filename.rsplit(".", 1)[-1].lower().replace("jpg", "jpeg")
        d = self._check(self.client.post("/task", json={"type": "image_to_model",
                        "file": {"type": ext, "file_token": up["image_token"]}}))
        return d["task_id"]

    def poll(self, handle):
        d = self._check(self.client.get(f"/task/{handle}"))
        state = MAP.get(d.get("status", "unknown"), "failed")
        if state != "completed":
            return ProviderStatus(state, d.get("progress"), d.get("status", ""))
        out = d.get("output", {})
        url = out.get("pbr_model") or out.get("model") or out.get("base_model")
        if not url:
            raise ProviderError("Completed task has no model URL")
        r = httpx.get(url, timeout=120, follow_redirects=True) if self.client._transport is None \
            else self.client.get(url)
        if r.status_code != 200:
            raise ProviderError(f"Model download failed (HTTP {r.status_code})")
        return ProviderStatus("completed", 100, "Done", r.content)

    def cancel(self, handle):
        return False  # not assumed to be supported
