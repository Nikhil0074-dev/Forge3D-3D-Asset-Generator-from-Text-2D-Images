import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STORAGE = Path(os.environ.get("STORAGE_DIR", ROOT / "storage"))
DB_PATH = Path(os.environ.get("DB_PATH", STORAGE / "assets.db"))
PROVIDER = os.environ.get("GEN_PROVIDER", "mock")  # mock | tripo
TRIPO_API_KEY = os.environ.get("TRIPO_API_KEY", "")
TRIPO_BASE = os.environ.get("TRIPO_BASE", "https://api.tripo3d.ai/v2/openapi")
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 8 * 1024 * 1024))
MAX_IMAGE_DIM = int(os.environ.get("MAX_IMAGE_DIM", 4096))
MAX_PROMPT_CHARS = 1000
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", 30))
MOCK_DURATION = float(os.environ.get("MOCK_DURATION", 3.0))
for d in ("uploads", "generated", "thumbnails", "exports"):
    (STORAGE / d).mkdir(parents=True, exist_ok=True)
