import os
import sys
from pathlib import Path

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("DISCORD_CLIENT_ID", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


import pytest


@pytest.fixture(autouse=True)
def _isolate_database_globals():
    """Each test builds its own engine; never reuse one bound to a finished event loop."""
    import database.connection as dbc

    dbc._engine = None
    dbc._session_factory = None
    yield
    dbc._engine = None
    dbc._session_factory = None


@pytest.fixture(autouse=True)
def _restore_cog_modules():
    """bot.load_extension() replaces entries in sys.modules; put the originals back so
    later tests that monkeypatch a cog module patch the same module their classes use."""
    import sys

    snapshot = {k: v for k, v in sys.modules.items() if k.startswith("cogs.")}
    yield
    for key in [k for k in sys.modules if k.startswith("cogs.")]:
        if key not in snapshot:
            del sys.modules[key]
    for key, module in snapshot.items():
        sys.modules[key] = module
        parent, _, child = key.rpartition(".")
        if parent in sys.modules:  # `import a.b.c as m` resolves through the parent's attribute
            setattr(sys.modules[parent], child, module)
