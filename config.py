"""Load settings from environment (set DISCORD_TOKEN before run)."""
import os

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()
