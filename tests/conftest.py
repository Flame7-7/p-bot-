import os
import sys
from pathlib import Path

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("DISCORD_CLIENT_ID", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
