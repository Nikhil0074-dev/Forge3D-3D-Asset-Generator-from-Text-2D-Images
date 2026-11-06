from .. import config
from .mock_provider import MockProvider
from .tripo_provider import TripoProvider


def get_provider(name=None):
    name = name or config.PROVIDER
    if name == "tripo":
        return TripoProvider(config.TRIPO_API_KEY, config.TRIPO_BASE)
    if name == "mock":
        return MockProvider(config.MOCK_DURATION)
    raise ValueError(f"Unknown provider: {name}")
