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
