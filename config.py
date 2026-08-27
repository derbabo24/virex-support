import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", ".")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")

# UI Colors (Hex format for Discord Embeds)
COLOR_PRIMARY = 0x5865F2    # Blurple
COLOR_SUCCESS = 0x57F287    # Green
COLOR_WARNING = 0xFEE75C    # Yellow
COLOR_ERROR = 0xED4245      # Red
COLOR_INFO = 0x5865F2       # Blue
COLOR_MOD = 0xE67E22        # Orange
COLOR_PROTECT = 0x9B59B6    # Purple

# Emojis for clean status messages
EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"
EMOJI_WARNING = "⚠️"
EMOJI_SHIELD = "🛡️"
EMOJI_HAMMER = "🔨"
EMOJI_MUTE = "🔇"
EMOJI_WARN = "⚠️"
EMOJI_LOCK = "🔒"
EMOJI_UNLOCK = "🔓"
EMOJI_ENVELOPE = "✉️"
EMOJI_TICKET = "🎫"
EMOJI_INFO = "ℹ️"
