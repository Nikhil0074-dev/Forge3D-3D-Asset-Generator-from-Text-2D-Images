import io, time, collections
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import config, db, jobs
from .providers import get_provider
from .processing import glb

app = FastAPI(title="3D Asset Generator", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
db.init()
_provider = None
_hits = collections.defaultdict(list)


def provider():
    global _provider
    if _provider is None:
        _provider = get_provider()
    return _provider


def rate_limit(request: Request):
    ip, now = request.client.host if request.client else "?", time.time()
    _hits[ip] = [t for t in _hits[ip] if now - t < 60]
    if len(_hits[ip]) >= config.RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Rate limit exceeded; try again in a minute")
    _hits[ip].append(now)


class TextReq(BaseModel):
    prompt: str = Field(..., min_length=1)
    style: str = "realistic"
    quality: str = "standard"
    output_format: str = "glb"


def sniff_image(b: bytes):
    if b[:8] == b"\x89PNG\r\n\x1a\n": return "png"
    if b[:3] == b"\xff\xd8\xff": return "jpeg"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP": return "webp"
    return None


@app.get("/api/health")
def health():
    return {"status": "ok", "provider": config.PROVIDER}


def _job_out(j):
    prog = j["progress"] if j["progress"] is not None and j["progress"] >= 0 else None
    return {"job_id": j["id"], "status": j["status"], "progress": prog, "message": j["message"],
            "error": j["error_message"], "asset_id": j["asset_id"], "generation_type": j["generation_type"]}


@app.post("/api/generation/text", status_code=202)
def gen_text(req: TextReq, request: Request):
    rate_limit(request)
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(422, "Prompt must not be blank")
    if len(prompt) > config.MAX_PROMPT_CHARS:
        raise HTTPException(422, f"Prompt exceeds {config.MAX_PROMPT_CHARS} characters")
    if req.output_format != "glb":
        raise HTTPException(422, "Generation output is GLB; use the export endpoint for other formats")
    jid = db.create_job("text-to-3d", prompt, provider().name, req.model_dump())
    jobs.start(provider(), jid, "text-to-3d", prompt, opts=req.model_dump())
    return {"job_id": jid, "status": "queued", "message": "3D generation request submitted"}


@app.post("/api/generation/image", status_code=202)
async def gen_image(request: Request, file: UploadFile = File(...), prompt: str = Form(""), style: str = Form("realistic")):
    rate_limit(request)
    data = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Image exceeds {config.MAX_UPLOAD_BYTES // 1024 // 1024} MB limit")
    kind = sniff_image(data)
    if not kind:
        raise HTTPException(415, "Unsupported image type (use PNG, JPEG or WebP)")
    from PIL import Image
    try:
        w, h = Image.open(io.BytesIO(data)).size
    except Exception:
        raise HTTPException(422, "Corrupt or unreadable image")
    if max(w, h) > config.MAX_IMAGE_DIM:
        raise HTTPException(422, f"Image larger than {config.MAX_IMAGE_DIM}px on one side")
    safe = f"upload.{'jpg' if kind == 'jpeg' else kind}"  # never trust the client filename
    jid = db.create_job("image-to-3d", prompt, provider().name, {"style": style, "image": safe})
    (config.STORAGE / "uploads" / f"{jid}.{kind}").write_bytes(data)
    jobs.start(provider(), jid, "image-to-3d", prompt, image=data, filename=safe, opts={"style": style})
    return {"job_id": jid, "status": "queued", "message": "3D generation request submitted"}


@app.get("/api/generation/{job_id}")
def job_status(job_id: str):
    j = db.get_job(job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    return _job_out(j)


@app.post("/api/generation/{job_id}/cancel")
def job_cancel(job_id: str):
    j = db.get_job(job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    if j["status"] in ("completed", "failed", "cancelled"):
        raise HTTPException(409, f"Job already {j['status']}")
    db.update_job(job_id, status="cancelled", message="Cancelled", completed_at=time.time())
    return {"job_id": job_id, "status": "cancelled"}


def _asset_out(a):
    return {"asset_id": a["id"], "name": a["name"], "generation_type": a["generation_type"], "provider": a["provider"],
            "format": a["format"], "status": "completed", "created_at": a["created_at"], "file_size": a["file_size"],
            "prompt": a["prompt"], "stats": a["stats"], "thumbnail": f"/api/assets/{a['id']}/thumbnail"}


def _need(aid):
    a = db.get_asset(aid)
    if not a:
        raise HTTPException(404, "Asset not found")
    return a


@app.get("/api/assets")
def assets(search: str = "", type: str = ""):
    return [_asset_out(a) for a in db.list_assets(search, type)]


@app.get("/api/assets/{aid}")
def asset(aid: str):
    return _asset_out(_need(aid))


class Rename(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


@app.patch("/api/assets/{aid}")
def rename(aid: str, body: Rename):
    _need(aid)
    db.rename_asset(aid, body.name.strip())
    return _asset_out(db.get_asset(aid))


@app.delete("/api/assets/{aid}", status_code=204)
def delete(aid: str):
    a = _need(aid)
    for p in (a["file_path"], a["thumbnail_path"]):
        Path(p).unlink(missing_ok=True)
    db.delete_asset(aid)
    return Response(status_code=204)


@app.get("/api/assets/{aid}/thumbnail")
def thumb(aid: str):
    return FileResponse(_need(aid)["thumbnail_path"], media_type="image/png")


@app.get("/api/assets/{aid}/preview")
def preview(aid: str):
    return FileResponse(_need(aid)["file_path"], media_type="model/gltf-binary")


@app.get("/api/assets/{aid}/download")
def download(aid: str):
    a = _need(aid)
    return FileResponse(a["file_path"], media_type="model/gltf-binary", filename=f"{_slug(a['name'])}.glb")


def _slug(s):
    return "".join(c if c.isalnum() else "_" for c in s)[:40].strip("_") or "model"


class ExportReq(BaseModel):
    format: str


@app.post("/api/assets/{aid}/export")
def export(aid: str, body: ExportReq):
    a = _need(aid)
    data = Path(a["file_path"]).read_bytes()
    fmt, slug = body.format.lower(), _slug(a["name"])
    try:
        if fmt == "glb":
            out, mt, fn = data, "model/gltf-binary", f"{slug}.glb"
        elif fmt == "gltf":
            out, mt, fn = glb.glb_to_gltf(data), "model/gltf+json", f"{slug}.gltf"
        elif fmt == "obj":
            out, mt, fn = glb.glb_to_obj_zip(data, slug), "application/zip", f"{slug}_obj.zip"
        else:
            raise HTTPException(422, "Unsupported format (glb, gltf, obj)")
    except glb.ModelError as e:
        raise HTTPException(422, f"Export failed: {e}")
    return Response(out, media_type=mt, headers={"Content-Disposition": f'attachment; filename="{fn}"'})


_dist = config.ROOT / "frontend" / "dist"
if _dist.exists():  # serve built frontend from the same origin in production
    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
