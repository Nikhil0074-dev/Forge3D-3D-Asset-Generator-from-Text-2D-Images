"""In-process worker threads. For production swap for a Redis-backed queue (see docs/architecture.md)."""
import threading, time
from pathlib import Path
from . import db, config
from .providers.base import ProviderError
from .processing import glb

POLL = 0.4
TIMEOUT = 600


def start(provider, jid, kind, prompt, image=None, filename=None, opts=None):
    t = threading.Thread(target=_run, args=(provider, jid, kind, prompt, image, filename, opts or {}), daemon=True)
    t.start()
    return t


def _fail(jid, msg):
    db.update_job(jid, status="failed", error_message=msg, message="Failed", completed_at=time.time())


def _run(provider, jid, kind, prompt, image, filename, opts):
    try:
        handle = provider.submit_text(prompt, opts) if kind == "text-to-3d" \
            else provider.submit_image(image, filename, prompt, opts)
        db.update_job(jid, handle=handle)
        t0 = time.time()
        while True:
            if db.get_job(jid)["status"] == "cancelled":
                provider.cancel(handle)
                return
            st = provider.poll(handle)
            if st.state == "failed":
                return _fail(jid, st.message or "Provider reported failure")
            if st.state == "completed":
                break
            db.update_job(jid, status=st.state, progress=st.progress if st.progress is not None else -1, message=st.message)
            if time.time() - t0 > TIMEOUT:
                return _fail(jid, "Generation timed out")
            time.sleep(POLL)
        db.update_job(jid, status="processing", progress=95, message="Validating and processing model")
        data = st.model
        stats = glb.analyze(data)  # raises ModelError on malformed output
        aid = db.new_id("asset")
        fp = config.STORAGE / "generated" / f"{aid}.glb"
        fp.write_bytes(data)
        tp = config.STORAGE / "thumbnails" / f"{aid}.png"
        tp.write_bytes(glb.thumbnail_png(data))
        name = (prompt or filename or "Untitled").strip()[:48] or "Untitled"
        db.create_asset(id=aid, job_id=jid, name=name, generation_type=kind, provider=provider.name, format="glb",
                        file_path=str(fp), thumbnail_path=str(tp), file_size=len(data), prompt=prompt or "", stats=stats)
        db.update_job(jid, status="completed", progress=100, message="Ready for preview", asset_id=aid, completed_at=time.time())
    except (ProviderError, glb.ModelError) as e:
        _fail(jid, str(e))
    except Exception as e:  # never leave a job hanging
        _fail(jid, f"Unexpected error: {e}")
