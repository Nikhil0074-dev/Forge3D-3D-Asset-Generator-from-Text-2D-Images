# Architecture

```
React + R3F viewer ──/api──▶ FastAPI ──▶ job runner (thread per job) ──▶ Provider adapter (mock | tripo)
                                │                                          │ GLB bytes
                                ▼                                          ▼
                        SQLite (jobs, assets)  ◀── processing/glb.py (validate · analyse · thumbnail · convert)
                                │
                        storage/{uploads,generated,thumbnails}
```

* **Provider adapter** (`providers/base.py`): `submit_text`, `submit_image`, `poll`, `cancel`. Progress is `None` when a
  provider can't report it, and the UI then shows an indeterminate bar instead of a fake percentage.
* **Job lifecycle**: `queued → processing → completed | failed | cancelled`. Every provider/model error becomes a `failed`
  job with a message; a worker never leaves a job hanging.
* **Model processing** (`processing/glb.py`, pure Python + NumPy): GLB parsing with bounds checks, rejection of external
  buffer URIs, stats (vertices, triangles, meshes, materials, bbox), software-rendered thumbnails, GLB→glTF (embedded
  buffer) and GLB→OBJ+MTL (ZIP).
* **Security**: magic-byte sniffing of uploads (never the client filename or MIME), size + dimension limits, per-IP rate
  limit, API keys only in backend env, CORS restricted to the dev origin.

## API
| Method | Path | Notes |
|---|---|---|
| POST | `/api/generation/text` | `{prompt, style, quality, output_format:"glb"}` → 202 `{job_id}` |
| POST | `/api/generation/image` | multipart `file`, `prompt`, `style` → 202 |
| GET | `/api/generation/{id}` | status, progress (nullable), error, asset_id |
| POST | `/api/generation/{id}/cancel` | 409 if already finished |
| GET | `/api/assets?search=&type=` | library |
| GET/PATCH/DELETE | `/api/assets/{id}` | metadata / rename / delete |
| GET | `/api/assets/{id}/preview` · `/thumbnail` · `/download` | GLB, PNG, GLB attachment |
| POST | `/api/assets/{id}/export` | `{format: glb|gltf|obj}` |
| GET | `/api/health` | |

## Moving to production
Replace the thread runner with a Redis-backed worker (RQ/Celery) so jobs survive restarts, move SQLite → PostgreSQL,
add authentication + per-user asset ownership, and serve assets from private object storage with signed URLs.
