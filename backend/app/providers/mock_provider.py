"""Offline provider: builds a deterministic procedural GLB from prompt keywords / image colours."""
import io, time, uuid, hashlib
from .base import Provider, ProviderStatus, ProviderError
from ..processing import shapes as S
from ..processing.glb import build_glb

COLORS = {"red": (.8, .1, .1), "blue": (.1, .3, .85), "green": (.15, .65, .25), "gold": (.95, .75, .2),
          "golden": (.95, .75, .2), "silver": (.75, .77, .8), "wooden": (.55, .35, .18), "wood": (.55, .35, .18),
          "stone": (.5, .5, .52), "black": (.08, .08, .1), "white": (.92, .92, .92), "purple": (.5, .2, .75),
          "orange": (.95, .5, .1), "yellow": (.95, .85, .15), "pink": (.95, .45, .7), "steel": (.62, .65, .7)}
METALLIC = ("metal", "metallic", "steel", "silver", "gold", "golden", "chrome", "robot", "sword")


import re
ACCENT = re.compile(r"\b\w+\s+(?:eyes?|glow\w*|lights?|accents?|trim|handle|grip)\b")


def pick_color(text):
    t = ACCENT.sub(" ", text.lower())  # "glowing blue eyes" must not recolour the whole body
    for k, v in COLORS.items():
        if k in t:
            return v
    h = hashlib.md5(t.encode()).digest()
    return tuple(0.3 + 0.6 * b / 255 for b in h[:3])


def build_model(prompt: str, base=None) -> bytes:
    t = prompt.lower()
    c = base or pick_color(t)
    col = (*c, 1.0)
    dark = (c[0] * .35, c[1] * .35, c[2] * .35, 1.0)
    glow = (.2, .8, 1.0, 1.0)
    m = 0.55 if any(k in t for k in METALLIC) else 0.15
    kw = dict(color=col, metal=m, rough=0.4 if m > .5 else 0.7)
    dk = dict(color=dark, metal=m, rough=0.5)
    if "chair" in t:
        parts = [S.box((0, .0, 0), (1, .12, 1), name="seat", **kw), S.box((0, .6, -.45), (1, 1.1, .1), name="back", **kw)]
        parts += [S.box((x, -.5, z), (.1, .9, .1), name="leg", **dk) for x in (-.4, .4) for z in (-.4, .4)]
    elif "sword" in t:
        parts = [S.box((0, .8, 0), (.18, 2.0, .04), name="blade", **kw), S.box((0, -.25, 0), (.8, .12, .12), name="guard", **dk),
                 S.cylinder((0, -.7, 0), (.07, .8, .07), name="grip", **dk), S.sphere((0, -1.15, 0), (.13, .13, .13), name="pommel", color=(.95, .75, .2, 1), metal=.6, rough=.3)]
    elif "castle" in t or "tower" in t:
        parts = [S.box((0, 0, 0), (2, 1.2, 2), name="keep", **kw)]
        for x in (-1, 1):
            for z in (-1, 1):
                parts += [S.cylinder((x, .35, z), (.4, 1.9, .4), name="turret", **dk), S.cylinder((x, 1.55, z), (.5, .6, .5), top=0, name="roof", color=(.6, .15, .15, 1))]
    elif "car" in t:
        parts = [S.box((0, 0, 0), (2.4, .5, 1.1), name="body", **kw), S.box((.1, .45, 0), (1.2, .45, .95), name="cabin", **dk)]
        parts += [S.cylinder((x, -.25, z), (.28, .22, .28), name="wheel", color=(.05, .05, .05, 1)) for x in (-.8, .8) for z in (-.55, .55)]
        parts = _fix_wheels(parts)
    elif "dog" in t or "cat" in t or "animal" in t:
        parts = [S.box((0, .4, 0), (1.3, .6, .55), name="body", **kw), S.box((.85, .8, 0), (.5, .45, .45), name="head", **kw)]
        parts += [S.box((x, -.1, z), (.14, .7, .14), name="leg", **dk) for x in (-.5, .5) for z in (-.2, .2)]
        parts += [S.sphere((1.08, .85, z), (.06, .06, .06), name="eye", color=glow, metal=0, rough=.2) for z in (-.1, .1)]
    elif "helmet" in t:
        parts = [S.sphere((0, 0, 0), (1, 1.05, 1), name="dome", **kw), S.box((.55, -.1, 0), (.15, .5, .5), name="visor", **dk)]
    elif "robot" in t:
        parts = [S.box((0, .2, 0), (.9, 1.0, .6), name="torso", **kw), S.box((0, 1.05, 0), (.6, .5, .5), name="head", **kw)]
        parts += [S.sphere((.15, 1.12, .27), (.07, .07, .07), name="eye", color=glow, metal=0, rough=.2), S.sphere((-.15, 1.12, .27), (.07, .07, .07), name="eye", color=glow, metal=0, rough=.2)]
        parts += [S.box((x, .25, 0), (.2, .9, .2), name="arm", **dk) for x in (-.65, .65)]
        parts += [S.box((x, -.6, 0), (.25, .8, .25), name="leg", **dk) for x in (-.25, .25)]
    elif "ring" in t or "donut" in t or "torus" in t:
        parts = [S.torus(scale=(1, 1, 1), R=1.0, r=.35, name="ring", **kw)]
    elif "tree" in t:
        parts = [S.cylinder((0, 0, 0), (.15, 1.2, .15), name="trunk", color=(.4, .25, .1, 1)), S.sphere((0, 1.0, 0), (.7, .7, .7), name="leaves", color=(.15, .6, .2, 1)), ]
    else:
        parts = [S.sphere((0, 0, 0), (.9, .9, .9), name="body", **kw), S.torus((0, 0, 0), R=1.25, r=.08, name="ring", **dk)]
    return build_glb(parts)


def _fix_wheels(parts):
    """Rebuild wheels with their axis along Z (swap Y/Z of the cylinder vertices around their centre)."""
    import numpy as np
    for p in parts:
        if p["name"] == "wheel":
            pos = p["positions"]
            c = (pos.max(0) + pos.min(0)) / 2
            q = pos - c
            q = q[:, [0, 2, 1]]
            p["positions"] = (q + c).astype(np.float32)
            n = p["normals"][:, [0, 2, 1]]
            p["normals"] = n.astype(np.float32)
            p["indices"] = p["indices"].reshape(-1, 3)[:, [0, 2, 1]].reshape(-1)
    return parts


class MockProvider(Provider):
    name = "mock"

    def __init__(self, duration=3.0):
        self.duration = duration
        self.jobs = {}

    def _new(self, glb_fn):
        h = "mock_" + uuid.uuid4().hex[:12]
        self.jobs[h] = {"t0": time.time(), "fn": glb_fn, "cancel": False}
        return h

    def submit_text(self, prompt, opts):
        if not prompt.strip():
            raise ProviderError("Empty prompt")
        return self._new(lambda: build_model(prompt))

    def submit_image(self, image, filename, prompt, opts):
        from PIL import Image
        try:
            im = Image.open(io.BytesIO(image)).convert("RGB").resize((16, 16))
        except Exception as e:
            raise ProviderError(f"Unreadable image: {e}")
        import numpy as np
        avg = tuple(float(x) for x in np.asarray(im).reshape(-1, 3).mean(0) / 255)
        hint = prompt or filename
        return self._new(lambda: build_model(hint + " ", base=avg))

    def poll(self, handle):
        j = self.jobs.get(handle)
        if not j:
            return ProviderStatus("failed", message="Unknown job")
        if j["cancel"]:
            return ProviderStatus("failed", message="Cancelled")
        f = (time.time() - j["t0"]) / max(self.duration, 0.01)
        if f < 0.2:
            return ProviderStatus("queued", int(f * 100), "Request accepted")
        if f < 1:
            return ProviderStatus("processing", int(f * 100), "Generating geometry and materials")
        return ProviderStatus("completed", 100, "Done", j["fn"]())

    def cancel(self, handle):
        if handle in self.jobs:
            self.jobs[handle]["cancel"] = True
            return True
        return False
