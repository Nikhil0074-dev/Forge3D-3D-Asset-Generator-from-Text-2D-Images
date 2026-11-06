from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderStatus:
    state: str                 # queued | processing | completed | failed
    progress: Optional[int] = None   # None => indeterminate (never invent percentages)
    message: str = ""
    model: Optional[bytes] = None    # GLB bytes when completed


class ProviderError(RuntimeError):
    pass


class Provider:
    name = "base"

    def submit_text(self, prompt: str, opts: dict) -> str: raise NotImplementedError
    def submit_image(self, image: bytes, filename: str, prompt: str, opts: dict) -> str: raise NotImplementedError
    def poll(self, handle: str) -> ProviderStatus: raise NotImplementedError
    def cancel(self, handle: str) -> bool: return False
