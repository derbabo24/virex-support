# ============================================================
#  VIREX BOT — COMBINED (Moderation + Tickets/Verify/Backup)
#  ----------------------------------------------------------
#  Zusammengeführt aus:
#    1) Moderation-Bot  ($-Prefix: blacklist, whitelist, giveaways,
#       vouch, product status, ban requests, word filter, Flask)
#    2) Ticket-Bot      (Slash: tickets, verify, backup/restore,
#       welcome/leave, transcripts, token refresh)
#
#  WICHTIGE MERGE-HINWEISE:
#  • Nur EIN bot-Objekt. Prefix akzeptiert "$" UND "!".
#  • on_ready / on_message / on_member_join gab es doppelt →
#    zu jeweils EINEM Handler zusammengefasst.
#  • init_db legt jetzt ALLE 4 Tabellen an
#    (blacklist, whitelist, verified_users, tickets).
#  • Der "*"-Silent-Prefix verlangt jetzt Staff (aus dem Mod-Bot),
#    da der Ticket-Bot ihn ungeschützt hatte.
#  • Staff = Rollenname (Mod-Bot) ODER Rollen-ID (Ticket-Bot).
# ============================================================

import audioop  # noqa: F401 — audioop-lts shim for Python 3.13
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import re
import io
import json
import random
import aiohttp
import asyncpg
import urllib.parse
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

# ============================================================
#  CONFIG — MODERATION
# ============================================================
PREFIX = "$"
SILENT_PREFIX = "*"
BAN_REQUEST_CHANNEL_ID = int(os.environ.get("BAN_REQUEST_CHANNEL_ID", 0))
ADMIN_ROLE_NAME = os.environ.get("ADMIN_ROLE_NAME", "Blacklist")  # darf Ban-Requests approven/denyen
STAFF_ROLE_NAME = "Trial Staff (not trusted)"
BLACKLIST_ADMIN_ROLE = "Blacklist"
# Points a Trial Staff member earns per message sent in the server (used by /leaderboard)
POINTS_PER_MESSAGE = int(os.environ.get("POINTS_PER_MESSAGE", 1) or 1)
APPROVE_CHANNEL_ID = 1524959782799147059
POST_CHANNEL_ID = 1525447920596287598
CHANGELOG_CHANNEL_ID = 1524959757499371620
CUSTOMER_ROLE_NAME = "customer"
MESSAGE_LOG_CHANNEL_ID = 1524959786871820309
VOUCH_CHANNEL_ID = 1524959744228331520
R6_GUIDE_URL = "https://virexguide.com/"

# ============================================================
#  CONFIG — TICKETS / VERIFY / BACKUP
# ============================================================
TOKEN                    = os.getenv("DISCORD_TOKEN", "")
GUILD_ID                 = int(os.getenv("GUILD_ID", 0))
TICKET_CATEGORY_ID       = int(os.getenv("TICKET_CATEGORY_ID", 0))
TRANSCRIPT_CHANNEL_ID    = int(os.getenv("TRANSCRIPT_CHANNEL_ID", 0))
STAFF_ROLE_IDS           = [int(x) for x in os.getenv("STAFF_ROLE_IDS", "").split(",") if x.strip().isdigit()]
ADMIN_ROLE_IDS           = [int(x) for x in os.getenv("ADMIN_ROLE_IDS", "").split(",") if x.strip().isdigit()]
AUTO_CLOSE_HOURS         = int(os.getenv("AUTO_CLOSE_HOURS", 24))
VIREX_LOGO               = os.getenv("VIREX_LOGO", "").strip()
VIREX_WEBSITE            = os.getenv("VIREX_WEBSITE", "https://virex.gg/")

# Unified color palette based on VX logo (deep navy + electric blue)
VIREX_COLOR              = 0x1A6FFF   # Electric blue — primary accent
VIREX_COLOR_SUCCESS      = 0x1AE8A0   # Teal-green for success
VIREX_COLOR_DANGER       = 0xE83A3A   # Soft red for errors/leave
VIREX_COLOR_WARN         = 0xF0A500   # Amber for warnings/on-hold
VIREX_COLOR_SUBTLE       = 0x1C2B50   # Dark navy for neutral embeds

# OAuth2 / Verify
CLIENT_ID                = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET            = os.getenv("DISCORD_CLIENT_SECRET", "")
WEB_BASE_URL             = os.getenv("WEB_BASE_URL", "http://localhost:5000")
VERIFIED_ROLE_ID         = int(os.getenv("VERIFIED_ROLE_ID", 0))

# Welcome / Leave channel
WELCOME_CHANNEL_ID       = int(os.getenv("WELCOME_CHANNEL_ID", 0))

# PostgreSQL (von BEIDEN Bots genutzt — eine gemeinsame DB)
DATABASE_URL             = os.environ.get("DATABASE_URL", "")

TICKET_CATEGORIES = {
    "purchase": {"label": "Purchase",               "description": "Request help with a purchase.",      "emoji": "🛒", "color": VIREX_COLOR,         "category_env": "TICKET_CAT_PURCHASE"},
    "reseller": {"label": "Apply to be a Reseller", "description": "Apply to Virex's Reseller Program.", "emoji": "💰", "color": 0xF0A500,            "category_env": "TICKET_CAT_RESELLER"},
    "claim":    {"label": "Claim Role / Key",       "description": "Claim your role or product key.",    "emoji": "🔑", "color": VIREX_COLOR_SUCCESS, "category_env": "TICKET_CAT_CLAIM"},
    "hwid":     {"label": "HWID Reset",             "description": "Request a reset for your key.",       "emoji": "🔒", "color": 0xE07B39,            "category_env": "TICKET_CAT_HWID"},
    "support":  {"label": "Get Support",            "description": "Request support from our staff.",     "emoji": "🎫", "color": VIREX_COLOR,         "category_env": "TICKET_CAT_SUPPORT"},
}

TICKET_PANEL_BANNER = os.getenv("TICKET_PANEL_BANNER", "").strip()
TICKET_OPEN_BANNER  = os.getenv("TICKET_OPEN_BANNER", "").strip()

# ============================================================
#  CONFIG — CLAIM ROLE / SELLAUTH
# ============================================================
# API key:  SellAuth Dashboard → Account → API Access
# Shop ID:  the integer in your dashboard URL / API paths
SELLAUTH_API_KEY   = os.getenv("SELLAUTH_API_KEY", "").strip()
SELLAUTH_SHOP_ID   = os.getenv("SELLAUTH_SHOP_ID", "").strip()
SELLAUTH_API_BASE  = os.getenv("SELLAUTH_API_BASE", "https://api.sellauth.com/v1").rstrip("/")
# Role granted on a successful claim. Defaults to the existing customer role.
CLAIM_ROLE_NAME    = os.getenv("CLAIM_ROLE_NAME", CUSTOMER_ROLE_NAME)
# Optional channel to log successful/failed claims (0 = disabled).
CLAIM_LOG_CHANNEL_ID = int(os.getenv("CLAIM_LOG_CHANNEL_ID", 0))
# How long (seconds) the DM verification session waits for each reply.
CLAIM_DM_TIMEOUT   = int(os.getenv("CLAIM_DM_TIMEOUT", 300))
# Only orders with one of these statuses can be claimed.
CLAIM_VALID_STATUSES = {"completed"}
# Users currently in the middle of a DM claim session (prevents double sessions).
claim_in_progress: set[int] = set()

# ─── PRODUCT STATUS ───────────────────────────────────────────────────────────
product_status: dict[str, str] = {
    "Lethal Lite":       "Testing",
    "Lethal FULL":       "Testing",
    "CRUSADER":          "Undetected",
    "Bo6 External":      "Undetected",
    "BO7/WZ Fade Chair": "Undetected",
    "ANCIENT R6s":       "Testing",
    "Vega R6":           "Online",
    "ONYX FN":           "Updating",
    "ONYX APEX":         "Updating",
    "FECURITY Apex":     "Online",
    "MEMEZ RUST":        "Online",
    "MEMEZ Lite":        "Online",
    "MEMEZ FULL":        "Online",
    "PREDATOR":          "Online",
    "ONYX SPOOFER":      "Online",
}
STATUS_DOTS = {
    "Undetected": "🟢",
    "Online":     "🟢",
    "Updating":   "🔵",
    "Testing":    "🟡",
    "Detected":   "🔴",
    "Offline":    "⚫",
}
STATUS_COLORS = {
    "Undetected": 0x57F287,
    "Online":     0x57F287,
    "Updating":   0x5865F2,
    "Testing":    0xFEE75C,
    "Detected":   0xED4245,
    "Offline":    0x95A5A6,
}

# ─── WORD FILTER ──────────────────────────────────────────────────────────────
BLACKLISTED_WORDS = [
    "spoof", "spoofed", "spoofer", "spoofing",
    "cheat", "cheats", "cheating", "cheater",
    "hack", "hacked", "hacking", "hacker",
    "aimbot", "wallhack", "esp", "triggerbot",
    "bypass", "injector", "inject",
]

# ─── LEGACY JSON (für migrate_json) ───────────────────────────────────────────
TICKETS_FILE      = "/app/data/tickets.json"
VERIFIED_FILE     = "/app/data/verified.json"

# ─── STATE ────────────────────────────────────────────────────────────────────
vouch_counter: int = 1
active_giveaways: dict = {}
db_pool: asyncpg.Pool = None
whitelist_cache: set[int] = set()   # Wortfilter-Bypass, aus DB geladen

# ============================================================
#  BOT SETUP  (nur EIN Bot-Objekt — akzeptiert "$" und "!")
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True

bot = commands.Bot(
    command_prefix=[PREFIX, "!"],
    intents=intents,
    help_command=None
)

# ============================================================
#  HTTP SERVER (Flask — serves the R6 guide)
# ============================================================
app = Flask(__name__)


@app.route('/guide')
def serve_guide():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()


def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False)

# ============================================================
#  DATABASE — EINE gemeinsame init_db für ALLE 4 Tabellen
# ============================================================
async def init_db() -> bool:
    global db_pool
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not set!")
        return False
    try:
        try:
            db_pool = await asyncpg.create_pool(
                DATABASE_URL, min_size=2, max_size=10,
                command_timeout=60, ssl='require'
            )
        except Exception as ssl_err:
            print(f"⚠️  SSL connection failed ({ssl_err}) — retrying without SSL...")
            db_pool = await asyncpg.create_pool(
                DATABASE_URL, min_size=2, max_size=10, command_timeout=60
            )

        async with db_pool.acquire() as conn:
            # ── Moderation tables ───────────────────────────────────────────
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    user_id BIGINT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    blacklisted_by BIGINT NOT NULL,
                    blacklisted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    guild_id BIGINT NOT NULL
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS whitelist (
                    user_id BIGINT PRIMARY KEY,
                    whitelisted_by BIGINT NOT NULL,
                    whitelisted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    guild_id BIGINT NOT NULL
                )
            ''')
            # ── Ticket / Verify tables ──────────────────────────────────────
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS verified_users (
                    user_id         TEXT PRIMARY KEY,
                    username        TEXT,
                    access_token    TEXT,
                    refresh_token   TEXT,
                    verified_at     TIMESTAMPTZ,
                    token_refreshed_at TIMESTAMPTZ,
                    token_expired   BOOLEAN DEFAULT FALSE,
                    last_left_guild TEXT,
                    left_at         TIMESTAMPTZ,
                    extra           JSONB DEFAULT '{}'::jsonb
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    channel_id      TEXT PRIMARY KEY,
                    user_id         BIGINT,
                    category        TEXT,
                    created_at      TIMESTAMPTZ,
                    last_activity   TIMESTAMPTZ,
                    auto_close      BOOLEAN DEFAULT TRUE,
                    status          TEXT DEFAULT 'open'
                )
            ''')
            # ── Claim-Role table ────────────────────────────────────────────
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS claimed_orders (
                    order_key   TEXT PRIMARY KEY,   -- canonical invoice id (as text)
                    invoice_id  TEXT,
                    email       TEXT,
                    claimed_by  BIGINT,
                    guild_id    BIGINT,
                    claimed_at  TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            # ── Staff leaderboard table (/leaderboard) ──────────────────────
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS staff_points (
                    user_id       BIGINT PRIMARY KEY,
                    guild_id      BIGINT NOT NULL DEFAULT 0,
                    points        BIGINT NOT NULL DEFAULT 0,
                    message_count BIGINT NOT NULL DEFAULT 0,
                    updated_at    TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            # Safety net: if staff_points already existed from an earlier
            # deploy with a different/older schema, backfill any missing
            # columns instead of erroring out on every message.
            await conn.execute('ALTER TABLE staff_points ADD COLUMN IF NOT EXISTS guild_id BIGINT NOT NULL DEFAULT 0')
            await conn.execute('ALTER TABLE staff_points ADD COLUMN IF NOT EXISTS points BIGINT NOT NULL DEFAULT 0')
            await conn.execute('ALTER TABLE staff_points ADD COLUMN IF NOT EXISTS message_count BIGINT NOT NULL DEFAULT 0')
            await conn.execute("ALTER TABLE staff_points ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()")
        print("✅ Database ready (blacklist, whitelist, verified_users, tickets, claimed_orders, staff_points)")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

# ── Blacklist DB helpers ──────────────────────────────────────────────────────
async def add_to_blacklist(user_id: int, reason: str, staff_id: int, guild_id: int) -> bool:
    if not db_pool:
        return False
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO blacklist (user_id, reason, blacklisted_by, guild_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE
                SET reason = $2, blacklisted_by = $3, blacklisted_at = NOW()
            ''', user_id, reason, staff_id, guild_id)
        return True
    except Exception as e:
        print(f"❌ Error adding to blacklist: {e}")
        return False


async def remove_from_blacklist(user_id: int) -> bool:
    if not db_pool:
        return False
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM blacklist WHERE user_id = $1', user_id)
        return True
    except Exception as e:
        print(f"❌ Error removing from blacklist: {e}")
        return False


async def is_blacklisted(user_id: int) -> bool:
    if not db_pool:
        return False
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchval('SELECT user_id FROM blacklist WHERE user_id = $1', user_id)
        return result is not None
    except Exception as e:
        print(f"❌ Error checking blacklist: {e}")
        return False


async def get_blacklist(guild_id: int) -> list:
    if not db_pool:
        return []
    try:
        async with db_pool.acquire() as conn:
            records = await conn.fetch(
                'SELECT user_id, reason, blacklisted_by, blacklisted_at FROM blacklist WHERE guild_id = $1 ORDER BY blacklisted_at DESC',
                guild_id
            )
        return records
    except Exception as e:
        print(f"❌ Error fetching blacklist: {e}")
        return []


async def get_blacklist_entry(user_id: int) -> dict:
    if not db_pool:
        return None
    try:
        async with db_pool.acquire() as conn:
            record = await conn.fetchrow(
                'SELECT user_id, reason, blacklisted_by, blacklisted_at FROM blacklist WHERE user_id = $1',
                user_id
            )
        return dict(record) if record else None
    except Exception as e:
        print(f"❌ Error fetching blacklist entry: {e}")
        return None

# ── Whitelist DB helpers ──────────────────────────────────────────────────────
async def db_add_whitelist(user_id: int, staff_id: int, guild_id: int) -> bool:
    if not db_pool:
        return False
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO whitelist (user_id, whitelisted_by, guild_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id, staff_id, guild_id)
        whitelist_cache.add(user_id)
        return True
    except Exception as e:
        print(f"❌ Error adding to whitelist: {e}")
        return False


async def db_remove_whitelist(user_id: int) -> bool:
    if not db_pool:
        return False
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM whitelist WHERE user_id = $1', user_id)
        whitelist_cache.discard(user_id)
        return True
    except Exception as e:
        print(f"❌ Error removing from whitelist: {e}")
        return False


async def db_load_whitelist() -> set[int]:
    """Load all whitelisted user IDs into the in-memory cache on startup."""
    if not db_pool:
        return set()
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT user_id FROM whitelist')
        return {r['user_id'] for r in rows}
    except Exception as e:
        print(f"❌ Error loading whitelist: {e}")
        return set()


async def db_get_whitelist(guild_id: int) -> list:
    if not db_pool:
        return []
    try:
        async with db_pool.acquire() as conn:
            return await conn.fetch(
                'SELECT user_id, whitelisted_by, whitelisted_at FROM whitelist WHERE guild_id = $1 ORDER BY whitelisted_at DESC',
                guild_id
            )
    except Exception as e:
        print(f"❌ Error fetching whitelist: {e}")
        return []

# ── Claimed-orders DB helpers ─────────────────────────────────────────────────
async def db_get_claim(order_key: str) -> dict | None:
    """Return the claim record for an order, or None if unclaimed."""
    if not db_pool:
        return None
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT order_key, invoice_id, email, claimed_by, guild_id, claimed_at '
                'FROM claimed_orders WHERE order_key = $1', str(order_key))
        return dict(row) if row else None
    except Exception as e:
        print(f"❌ Error fetching claim: {e}")
        return None


async def db_mark_order_claimed(order_key: str, invoice_id: str, email: str,
                                claimed_by: int, guild_id: int) -> bool:
    """Insert a claim. Returns False if the order was already claimed (race-safe)."""
    if not db_pool:
        return False
    try:
        async with db_pool.acquire() as conn:
            result = await conn.execute('''
                INSERT INTO claimed_orders (order_key, invoice_id, email, claimed_by, guild_id)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (order_key) DO NOTHING
            ''', str(order_key), str(invoice_id), (email or "").lower(), claimed_by, guild_id)
        # asyncpg returns "INSERT 0 1" on success, "INSERT 0 0" if the row already existed
        return result.endswith(" 1")
    except Exception as e:
        print(f"❌ Error marking order claimed: {e}")
        return False


# ============================================================
#  UTILITY
# ============================================================
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value):
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _to_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def set_logo(embed: discord.Embed):
    if VIREX_LOGO and VIREX_LOGO.startswith("https://"):
        embed.set_thumbnail(url=VIREX_LOGO)


def get_ticket_category_channel(guild: discord.Guild, cat_key: str):
    """Discord-Kategorie für diesen Ticket-Typ: eigene falls per Railway-Variable
    gesetzt, sonst TICKET_CATEGORY_ID."""
    info = TICKET_CATEGORIES.get(cat_key, {})
    env_name = info.get("category_env")
    specific = os.getenv(env_name, "").strip() if env_name else ""
    chosen = specific if specific.isdigit() else str(TICKET_CATEGORY_ID or "")
    if not chosen.isdigit():
        return None
    ch = guild.get_channel(int(chosen))
    return ch if isinstance(ch, discord.CategoryChannel) else None


def sanitize_channel_name(name: str) -> str:
    """Wandelt einen Discord-Anzeigenamen/Username in einen gültigen,
    URL-sicheren Kanalnamen um (klein geschrieben, nur a-z/0-9/-)."""
    name = name.strip().lower()
    # Umlaute grob transliterieren, damit Namen wie "Björn" nicht komplett wegfallen
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        "á": "a", "à": "a", "â": "a", "é": "e", "è": "e",
        "ê": "e", "í": "i", "î": "i", "ó": "o", "ô": "o",
        "ú": "u", "û": "u", "ñ": "n",
    }
    for src, dst in replacements.items():
        name = name.replace(src, dst)
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    if not name:
        name = "user"
    return name[:80]  # Discord-Limit ist 100 Zeichen, Platz für "ticket-"-Präfix lassen


def make_unique_ticket_channel_name(guild: discord.Guild, base_name: str) -> str:
    """Hängt bei Namenskollisionen (z.B. zwei User mit gleichem Anzeigenamen)
    eine laufende Nummer an, damit der Kanalname eindeutig bleibt."""
    existing = {c.name for c in guild.text_channels}
    channel_name = f"ticket-{base_name}"
    if channel_name not in existing:
        return channel_name
    suffix = 2
    while f"{channel_name}-{suffix}" in existing:
        suffix += 1
    return f"{channel_name}-{suffix}"

# ============================================================
#  VERIFIED USERS — DB HELPERS
# ============================================================
async def db_get_verified(user_id: str) -> dict | None:
    if not db_pool:
        return None
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM verified_users WHERE user_id = $1", user_id)
    if not row:
        return None
    d = dict(row)
    extra = d.pop("extra", {}) or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except Exception:
            extra = {}
    if not isinstance(extra, dict):
        print(f"⚠️  db_get_verified: non-dict extra for user {d.get('user_id')!r}, skipping merge (got {type(extra).__name__!r})")
        extra = {}
    d.update(extra)
    for k in ("verified_at", "token_refreshed_at", "left_at"):
        if d.get(k) and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d


async def db_set_verified(user_id: str, data: dict):
    """Upsert a verified user. Known columns are stored directly; anything else goes into extra JSONB."""
    if not db_pool:
        return
    known = {"username", "access_token", "refresh_token", "verified_at",
             "token_refreshed_at", "token_expired", "last_left_guild", "left_at"}
    base  = {k: v for k, v in data.items() if k in known}
    extra = {k: v for k, v in data.items() if k not in known and k != "user_id"}

    for k in ("verified_at", "token_refreshed_at", "left_at"):
        if isinstance(base.get(k), str):
            try:
                base[k] = datetime.fromisoformat(base[k])
            except Exception:
                base[k] = None

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO verified_users
                (user_id, username, access_token, refresh_token, verified_at,
                 token_refreshed_at, token_expired, last_left_guild, left_at, extra)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            ON CONFLICT (user_id) DO UPDATE SET
                username           = EXCLUDED.username,
                access_token       = EXCLUDED.access_token,
                refresh_token      = EXCLUDED.refresh_token,
                verified_at        = COALESCE(EXCLUDED.verified_at, verified_users.verified_at),
                token_refreshed_at = EXCLUDED.token_refreshed_at,
                token_expired      = EXCLUDED.token_expired,
                last_left_guild    = EXCLUDED.last_left_guild,
                left_at            = EXCLUDED.left_at,
                extra              = verified_users.extra || EXCLUDED.extra
        """,
            user_id,
            base.get("username"),
            base.get("access_token"),
            base.get("refresh_token"),
            base.get("verified_at"),
            base.get("token_refreshed_at"),
            base.get("token_expired", False),
            base.get("last_left_guild"),
            base.get("left_at"),
            json.dumps(extra),
        )


async def db_update_verified_field(user_id: str, **kwargs):
    """Patch individual fields on an existing row (or upsert skeleton)."""
    existing = await db_get_verified(user_id) or {"user_id": user_id}
    existing.update(kwargs)
    await db_set_verified(user_id, existing)


async def db_all_verified() -> dict:
    """Return all verified users as a {user_id: info_dict} mapping."""
    if not db_pool:
        return {}
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM verified_users")
    result = {}
    for row in rows:
        d = dict(row)
        uid = d.pop("user_id")
        extra = d.pop("extra", {}) or {}
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except Exception:
                extra = {}
        if not isinstance(extra, dict):
            print(f"⚠️  db_all_verified: non-dict extra for user {uid!r}, skipping merge (got {type(extra).__name__!r})")
            extra = {}
        d.update(extra)
        for k in ("verified_at", "token_refreshed_at", "left_at"):
            if d.get(k) and hasattr(d[k], "isoformat"):
                d[k] = d[k].isoformat()
        result[uid] = d
    return result

# ============================================================
#  TICKETS — DB HELPERS
# ============================================================
async def db_get_ticket(channel_id: str) -> dict | None:
    if not db_pool:
        return None
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tickets WHERE channel_id = $1", channel_id)
    if not row:
        return None
    d = dict(row)
    for k in ("created_at", "last_activity"):
        if d.get(k) and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d


async def db_set_ticket(channel_id: str, data: dict):
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO tickets (channel_id, user_id, category, created_at, last_activity, auto_close, status)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (channel_id) DO UPDATE SET
                user_id       = EXCLUDED.user_id,
                category      = EXCLUDED.category,
                created_at    = COALESCE(EXCLUDED.created_at, tickets.created_at),
                last_activity = EXCLUDED.last_activity,
                auto_close    = EXCLUDED.auto_close,
                status        = EXCLUDED.status
        """,
            channel_id,
            int(data.get("user_id", 0)),
            data.get("category"),
            _parse_ts(data.get("created_at")),
            _parse_ts(data.get("last_activity")),
            data.get("auto_close", True),
            data.get("status", "open"),
        )


async def db_update_ticket(channel_id: str, **kwargs):
    existing = await db_get_ticket(channel_id)
    if not existing:
        return
    existing.update(kwargs)
    await db_set_ticket(channel_id, existing)


async def db_all_tickets() -> dict:
    if not db_pool:
        return {}
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM tickets")
    result = {}
    for row in rows:
        d = dict(row)
        cid = d.pop("channel_id")
        for k in ("created_at", "last_activity"):
            if d.get(k) and hasattr(d[k], "isoformat"):
                d[k] = d[k].isoformat()
        result[cid] = d
    return result

# ============================================================
#  PERMISSION HELPERS
#  (Mod-Bot arbeitet mit Rollen-NAMEN, Ticket-Bot mit Rollen-IDs —
#   beides bleibt erhalten, is_any_staff prüft beides.)
# ============================================================
async def db_add_staff_points(user_id: int, guild_id: int, points: int) -> None:
    """Adds `points` to a user's leaderboard total (creates the row if needed)."""
    if not db_pool:
        return
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO staff_points (user_id, guild_id, points, message_count, updated_at)
            VALUES ($1, $2, $3, 1, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                points        = staff_points.points + EXCLUDED.points,
                message_count = staff_points.message_count + 1,
                guild_id      = EXCLUDED.guild_id,
                updated_at    = NOW()
        """, user_id, guild_id, points)


async def db_get_leaderboard(guild_id: int, limit: int = 10) -> list:
    if not db_pool:
        return []
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, points, message_count FROM staff_points
            WHERE guild_id = $1
            ORDER BY points DESC
            LIMIT $2
        """, guild_id, limit)
    return [dict(r) for r in rows]


def has_staff_role(user: discord.Member) -> bool:
    return STAFF_ROLE_NAME.lower() in [r.name.lower() for r in getattr(user, "roles", [])]


def has_blacklist_admin_role(user: discord.Member) -> bool:
    return BLACKLIST_ADMIN_ROLE.lower() in [r.name.lower() for r in getattr(user, "roles", [])]


def has_admin_role(user: discord.Member) -> bool:
    """Rolle, die Ban-Requests approven/denyen darf (aus Railway-Variable)."""
    return ADMIN_ROLE_NAME.lower() in [r.name.lower() for r in getattr(user, "roles", [])]


def has_customer_role(user: discord.Member) -> bool:
    return CUSTOMER_ROLE_NAME.lower() in [r.name.lower() for r in getattr(user, "roles", [])]


def is_staff(member: discord.Member) -> bool:
    """Ticket-Bot-Logik: Administrator oder Staff-/Admin-Rollen-ID."""
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    return any(r.id in STAFF_ROLE_IDS + ADMIN_ROLE_IDS for r in member.roles)


def is_admin(member: discord.Member) -> bool:
    """Ticket-Bot-Logik: Administrator oder Admin-Rollen-ID."""
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    return any(r.id in ADMIN_ROLE_IDS for r in member.roles)


def is_any_staff(member) -> bool:
    """Staff nach BEIDEN Systemen (Rollenname ODER Rollen-ID/Admin)."""
    if not isinstance(member, discord.Member):
        return False
    return has_staff_role(member) or is_staff(member)

# ============================================================
#  EMBED / FILTER HELPERS
# ============================================================
def parse_duration(duration_str: str) -> int | None:
    match = re.fullmatch(r"(\d+)([smhd])", duration_str.strip().lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    return value * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


def build_giveaway_embed(prize, winners, host_id, ends_at, entries, requirements=None) -> discord.Embed:
    description = (
        f"Click **🎉 Enter** to participate!\n\n"
        f"🏆 **Winners:** {winners}\n"
        f"👥 **Entries:** {entries}\n"
        f"🕐 **Ends:** <t:{int(ends_at.timestamp())}:R>\n"
        f"👑 **Hosted by:** <@{host_id}>"
    )
    if requirements:
        description += f"\n\n📋 **Requirements to enter:**\n{requirements}"
    embed = discord.Embed(title=f"🎉 GIVEAWAY — {prize}", description=description, color=0xFF73FA)
    embed.set_footer(text=f"Ends on {ends_at.strftime('%d.%m.%Y at %H:%M')} UTC")
    return embed


def build_status_embed() -> discord.Embed:
    embed = discord.Embed(title="📊 Current Product Status", color=0x6f2cff, timestamp=utcnow())
    items = list(product_status.items())
    col_size = (len(items) + 2) // 3
    for col_idx in range(3):
        chunk = items[col_idx * col_size:(col_idx + 1) * col_size]
        if not chunk:
            continue
        field_value = ""
        for name, status_value in chunk:
            dot = STATUS_DOTS.get(status_value, "⚫")
            field_value += f"{dot} **{name}**\n`{status_value}`\n\n"
        embed.add_field(name="\u200b", value=field_value.strip(), inline=True)
    embed.set_footer(text="Last updated")
    return embed


def check_blacklist(content: str) -> str | None:
    cleaned = re.sub(r"[*_~`|>\\]", "", content.lower())
    for word in BLACKLISTED_WORDS:
        if re.search(rf"\b{re.escape(word)}", cleaned):
            return word
    return None


async def log_deleted_message(message: discord.Message, matched_word: str):
    log_channel = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
    if not log_channel:
        return
    embed = discord.Embed(title="🚫 Message Deleted — Word Filter", color=0xFF4444, timestamp=utcnow())
    embed.add_field(name="👤 User", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
    embed.add_field(name="📍 Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="🔍 Matched Word", value=f"`{matched_word}`", inline=True)
    embed.add_field(
        name="💬 Message Content",
        value=f"```{message.content[:1000]}```" if message.content else "*empty*",
        inline=False
    )
    embed.set_thumbnail(url=message.author.display_avatar.url)
    embed.set_footer(text=f"User ID: {message.author.id}")
    await log_channel.send(embed=embed)


async def staff_check(ctx) -> bool:
    if not is_any_staff(ctx.author):
        embed = discord.Embed(
            title="❌ No Permission",
            description=f"You need at least the **{STAFF_ROLE_NAME}** role to use this command.",
            color=0xFF4444
        )
        await ctx.send(embed=embed, delete_after=5)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass
        return False
    return True


async def blacklist_admin_check(ctx) -> bool:
    if not has_blacklist_admin_role(ctx.author):
        embed = discord.Embed(
            title="❌ No Permission",
            description=f"You need the **{BLACKLIST_ADMIN_ROLE}** role to use this command.",
            color=0xFF4444
        )
        await ctx.send(embed=embed, delete_after=5)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass
        return False
    return True


async def end_giveaway(message_id: int):
    if message_id not in active_giveaways:
        return
    data = active_giveaways.pop(message_id)
    channel = bot.get_channel(data["channel_id"])
    if not channel:
        return
    try:
        msg = await channel.fetch_message(message_id)
    except discord.NotFound:
        return
    entries = list(data["entries"])
    prize = data["prize"]
    winner_count = min(data["winners"], len(entries))
    embed = discord.Embed(title=f"🎉 GIVEAWAY ENDED — {prize}", color=0x888888)
    if not entries:
        embed.description = "❌ Nobody entered. No winner was drawn."
        await msg.edit(embed=embed, view=None)
        await channel.send("❌ The giveaway ended with no participants.")
        return
    winners = random.sample(entries, winner_count)
    winner_mentions = " ".join(f"<@{w}>" for w in winners)
    embed.description = (f"**Prize:** {prize}\n**Winner(s):** {winner_mentions}\n👑 **Hosted by:** <@{data['host_id']}>")
    embed.set_footer(text="Giveaway ended")
    await msg.edit(embed=embed, view=None)
    await channel.send(f"🎉 Congratulations {winner_mentions}! You won **{prize}**!")

# ============================================================
#  TOKEN REFRESH — keeps backup tokens alive FOREVER
# ============================================================
async def refresh_token(uid: str) -> bool:
    info = await db_get_verified(uid)
    if not info:
        return False
    refresh_tok = info.get("refresh_token")
    if not refresh_tok:
        return False

    data = {
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "refresh_token",
        "refresh_token": refresh_tok,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://discord.com/api/v10/oauth2/token",
                data=data, headers=headers
            ) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    await db_update_verified_field(
                        uid,
                        access_token=token_data["access_token"],
                        refresh_token=token_data["refresh_token"],
                        token_refreshed_at=datetime.now(timezone.utc).isoformat(),
                        token_expired=False,
                    )
                    print(f"[TOKEN REFRESH] ✅ Refreshed token for user {uid}")
                    return True
                else:
                    text = await resp.text()
                    print(f"[TOKEN REFRESH] ❌ Failed for {uid}: {resp.status} {text}")
                    await db_update_verified_field(uid, token_expired=True)
                    return False
    except Exception as e:
        print(f"[TOKEN REFRESH] ❌ Exception for {uid}: {e}")
        return False

# ============================================================
#  GUILD JOIN HELPER (Backup restore)
# ============================================================
async def add_member_to_guild(user_id: int, guild_id: int, role_ids: list[int] = None) -> dict:
    uid  = str(user_id)
    info = await db_get_verified(uid)
    if not info or not info.get("access_token"):
        return {"status": "no_token", "detail": "User has not verified yet."}

    last_refresh_str = info.get("token_refreshed_at") or info.get("verified_at")
    if last_refresh_str:
        try:
            last = datetime.fromisoformat(last_refresh_str)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - last >= timedelta(days=5):
                print(f"[RESTORE] Token for {uid} is old, refreshing before restore...")
                await refresh_token(uid)
                info = await db_get_verified(uid) or info
        except Exception:
            pass

    access_token = info.get("access_token")
    if not access_token:
        return {"status": "no_token", "detail": "No access token available."}

    payload = {"access_token": access_token}
    if role_ids:
        payload["roles"] = role_ids

    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    url     = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"

    async with aiohttp.ClientSession() as session:
        async with session.put(url, json=payload, headers=headers) as resp:
            if resp.status in (200, 201):
                return {"status": "added",   "detail": "Successfully added to server."}
            elif resp.status == 204:
                return {"status": "already", "detail": "Already in server."}
            elif resp.status == 401:
                print(f"[RESTORE] 401 for {uid}, attempting token refresh...")
                refreshed = await refresh_token(uid)
                if refreshed:
                    new_info = await db_get_verified(uid) or {}
                    payload["access_token"] = new_info.get("access_token", "")
                    async with session.put(url, json=payload, headers=headers) as retry_resp:
                        if retry_resp.status in (200, 201):
                            return {"status": "added",   "detail": "Added after token refresh."}
                        elif retry_resp.status == 204:
                            return {"status": "already", "detail": "Already in server."}
                await db_update_verified_field(uid, token_expired=True)
                return {"status": "token_expired", "detail": "Access token has expired. User needs to re-verify."}
            else:
                text = await resp.text()
                return {"status": "error", "detail": f"API error {resp.status}: {text}"}

# ============================================================
#  HTML TRANSCRIPT GENERATOR
# ============================================================
def generate_transcript(channel, messages, guild):
    cat_key = ""
    if channel.topic and " | " in channel.topic:
        parts = channel.topic.split(" | ")
        if len(parts) > 1:
            cat_key = parts[1].strip()
    cat = TICKET_CATEGORIES.get(cat_key, {"label": "Support", "emoji": "🎫"})
    msgs_html = ""
    prev_id   = None
    for msg in messages:
        av  = str(msg.author.display_avatar.url) if msg.author.display_avatar else ""
        stf = any(r.id in STAFF_ROLE_IDS + ADMIN_ROLE_IDS for r in getattr(msg.author, "roles", []))
        if msg.author.id == guild.owner_id:
            bdg = '<span class="badge owner">Owner</span>'
        elif stf:
            bdg = '<span class="badge staff">Staff</span>'
        elif msg.author.bot:
            bdg = '<span class="badge bot">BOT</span>'
        else:
            bdg = ""
        att = ""
        for a in msg.attachments:
            if a.content_type and a.content_type.startswith("image"):
                att += f'<img src="{a.url}" class="att-img" alt="img">'
            else:
                att += f'<a href="{a.url}" class="att-file" target="_blank">📎 {a.filename}</a>'
        emb = ""
        for e in msg.embeds:
            ec = f"#{e.color.value:06x}" if e.color else "#1A6FFF"
            et = f"<div class='et'>{e.title}</div>" if e.title else ""
            ed = f"<div class='ed'>{e.description}</div>" if e.description else ""
            emb += f'<div class="emb" style="border-left-color:{ec}">{et}{ed}</div>'
        txt = msg.content or ""
        txt = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', txt)
        txt = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         txt)
        txt = re.sub(r'`(.+?)`',       r'<code>\1</code>',     txt)
        txt = re.sub(r'https?://\S+',  lambda m: f'<a href="{m.group()}" target="_blank">{m.group()}</a>', txt)
        ts      = msg.created_at.strftime("%d/%m/%Y %H:%M")
        same    = prev_id == msg.author.id
        prev_id = msg.author.id
        av_html  = f'<img src="{av}" class="av" alt="av">' if not same else '<div class="avs"></div>'
        hdr_html = (f'<div class="mh"><span class="un">{msg.author.display_name}</span>'
                    f'{bdg}<span class="ts">{ts}</span></div>') if not same else ""
        msgs_html += (f'<div class="mg{"" if not same else " sa"}">'
                      f'{av_html}<div class="mc">{hdr_html}<div class="mt">{txt}</div>{att}{emb}</div></div>')
    logo_html = (f'<img src="{VIREX_LOGO}" class="hl" alt="Virex" onerror="this.style.display=\'none\'">'
                 if VIREX_LOGO and VIREX_LOGO.startswith("https://") else "")
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Transcript — {channel.name}</title>
<style>:root{{--bg:#04080F;--s1:#070C18;--s2:#0A1020;--br:#0F1830;--bl:#1A6FFF;--blg:#4D8FFF;--tx:#D8E4FF;--mu:#4A5878;--sg:#1AE8A0;--ow:#F0A500;--bt:#5865F2}}
*{{box-sizing:border-box;margin:0;padding:0}}body{{background:var(--bg);color:var(--tx);font-family:'Inter',sans-serif;font-size:14px;line-height:1.6}}
.hd{{background:linear-gradient(135deg,#04080F 0%,#071228 50%,#0A1A3A 100%);border-bottom:1px solid var(--br);padding:24px 40px;display:flex;align-items:center;gap:20px}}
.hl{{width:60px;height:60px;border-radius:50%;border:2px solid var(--bl);box-shadow:0 0 12px rgba(26,111,255,0.4)}}.hi h1{{font-size:24px;color:var(--bl);font-weight:800;letter-spacing:3px}}.hi p{{color:var(--mu);font-size:12px}}
.hm{{margin-left:auto;font-size:11px;color:var(--mu)}}.hm strong{{color:var(--tx)}}
.ms{{max-width:880px;margin:0 auto;padding:20px 40px}}.mg{{display:flex;gap:12px;padding:5px 8px;border-radius:8px;margin:1px -8px}}
.av{{width:38px;height:38px;border-radius:50%;flex-shrink:0;border:1px solid var(--br)}}.avs{{width:38px;flex-shrink:0}}.mc{{flex:1}}
.mh{{display:flex;align-items:center;gap:6px;margin-bottom:2px}}.un{{font-weight:600}}.ts{{font-size:10px;color:var(--mu)}}
.badge{{font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px}}.badge.staff{{background:rgba(26,110,255,.15);color:var(--blg)}}
.badge.owner{{background:rgba(240,165,0,.15);color:var(--ow)}}.badge.bot{{background:rgba(88,101,242,.15);color:var(--bt)}}
.mt{{color:#A0B4E0;word-break:break-word}}.att-img{{max-width:380px;border-radius:8px;margin-top:6px;display:block}}
.emb{{margin-top:6px;background:var(--s2);border-left:4px solid var(--bl);border-radius:4px;padding:8px 12px}}
.ft{{text-align:center;padding:36px;border-top:1px solid var(--br);color:var(--mu);font-size:11px}}</style></head>
<body><div class="hd">{logo_html}<div class="hi"><h1>VIREX</h1><p>{cat["emoji"]} {cat["label"]} • #{channel.name}</p></div>
<div class="hm">Generated: <strong>{datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")} UTC</strong></div></div>
<div class="ms">{msgs_html}</div>
<div class="ft"><p><a href="{VIREX_WEBSITE}" style="color:var(--bl)">{VIREX_WEBSITE}</a></p></div>
</body></html>"""

# ============================================================
#  CLOSE TICKET
# ============================================================
async def close_ticket(channel, guild, closed_by=None):
    info = await db_get_ticket(str(channel.id))
    if not info:
        try:
            await channel.delete()
        except Exception:
            pass
        return
    messages = [m async for m in channel.history(limit=500, oldest_first=True)]
    html     = generate_transcript(channel, messages, guild)
    tr_ch    = guild.get_channel(TRANSCRIPT_CHANNEL_ID)
    if tr_ch:
        user       = guild.get_member(info["user_id"])
        cat        = TICKET_CATEGORIES.get(info.get("category", ""), {"label": "Support", "emoji": "🎫"})
        user_str   = user.mention if user else f"<@{info['user_id']}>"
        opened_ts  = int(datetime.fromisoformat(info["created_at"]).timestamp())
        closed_str = closed_by.mention if closed_by else "Auto-Close ⏰"
        embed = discord.Embed(
            title=f"📋 Transcript — #{channel.name}",
            description=(f"**User:** {user_str}\n**Category:** {cat['emoji']} {cat['label']}\n"
                         f"**Opened:** <t:{opened_ts}:F>\n**Closed by:** {closed_str}\n**Messages:** {len(messages)}"),
            color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Virex • Ticket System")
        set_logo(embed)
        try:
            await tr_ch.send(
                embed=embed,
                file=discord.File(io.BytesIO(html.encode()), filename=f"transcript-{channel.name}.html")
            )
        except Exception as e:
            print(f"Transcript send error: {e}")
    await db_update_ticket(str(channel.id), status="closed")
    try:
        await channel.delete()
    except Exception as e:
        print(f"Channel delete error: {e}")

# ============================================================
#  VIEWS — TICKETS
# ============================================================
class TicketQuestionsModal(discord.ui.Modal):
    def __init__(self, cat_key: str):
        cat = TICKET_CATEGORIES[cat_key]
        super().__init__(title=f"Open Ticket — {cat['label']}"[:45])
        self.cat_key = cat_key
        self.reason = discord.ui.TextInput(
            label="What is the reason for your request?",
            style=discord.TextStyle.paragraph, required=True, max_length=500)
        self.order_id = discord.ui.TextInput(
            label="What is your order ID?", required=False, max_length=100)
        self.product = discord.ui.TextInput(
            label="What product do you need help with?", required=False, max_length=200)
        self.add_item(self.reason)
        self.add_item(self.order_id)
        self.add_item(self.product)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await create_ticket_channel(
                interaction, cat_key=self.cat_key,
                reason=self.reason.value.strip(),
                order_id=self.order_id.value.strip(),
                product=self.product.value.strip())
        except Exception as e:
            print(f"[TICKET CREATE ERROR] {type(e).__name__}: {e}")
            try:
                await interaction.followup.send(f"❌ Could not create ticket: {e}", ephemeral=True)
            except discord.HTTPException:
                pass


async def create_ticket_channel(interaction: discord.Interaction, cat_key: str,
                                reason: str, order_id: str, product: str):
    guild = interaction.guild
    cat   = TICKET_CATEGORIES[cat_key]

    for ch in guild.text_channels:
        if ch.topic and f"uid-{interaction.user.id}" in ch.topic:
            await interaction.followup.send(
                f"❌ You already have an open ticket: {ch.mention}", ephemeral=True)
            return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user:   discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                        attach_files=True, read_message_history=True),
        guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                        manage_channels=True, read_message_history=True),
    }
    for rid in STAFF_ROLE_IDS + ADMIN_ROLE_IDS:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                           read_message_history=True)

    parent = get_ticket_category_channel(guild, cat_key)
    # Kanalname jetzt aus dem Discord-Usernamen statt einer laufenden Nummer.
    ticket_num    = len([c for c in guild.text_channels if c.name.startswith("ticket-")]) + 1
    base_name     = sanitize_channel_name(interaction.user.name)
    channel_name  = make_unique_ticket_channel_name(guild, base_name)

    try:
        channel = await guild.create_text_channel(
            name=channel_name, overwrites=overwrites, category=parent,
            topic=f"uid-{interaction.user.id} | {cat_key} | open")
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Could not create ticket: {e}", ephemeral=True)
        return

    await db_set_ticket(str(channel.id), {
        "user_id": interaction.user.id, "category": cat_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
        "auto_close": True, "status": "open"})

    await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

    embed = discord.Embed(
        title=f"{cat['emoji']} {cat['label']} — Ticket #{ticket_num:04d}",
        description=(
            "Thank you for creating a support ticket. While you wait for a support "
            "agent to promptly assist you in your inquiry, please review the "
            "information you provided below.\n\n"
            "**While you wait...**\n"
            "👤 A support agent will be with you shortly. Please provide clear "
            "screenshots if an error has occurred.\n\n"
            "**NO MOD WILL REQUEST THE TRANSFER OF A TICKET TO DMS FOR PAYMENTS. "
            "CONTACT MANAGEMENT IF THIS HAPPENS!**"),
        color=cat["color"], timestamp=datetime.now(timezone.utc))
    if VIREX_LOGO and VIREX_LOGO.startswith("https://"):
        embed.set_author(name="Support Ticket", icon_url=VIREX_LOGO)
    else:
        embed.set_author(name="Support Ticket")
    embed.add_field(name="What is the reason for your request?",
                    value=f"> {reason}" if reason else "> —", inline=False)
    embed.add_field(name="What is your order ID?",
                    value=f"> {order_id}" if order_id else "> —", inline=False)
    embed.add_field(name="What product do you need help with?",
                    value=f"> {product}" if product else "> —", inline=False)
    if TICKET_OPEN_BANNER.startswith("https://"):
        embed.set_image(url=TICKET_OPEN_BANNER)
    embed.set_footer(text="Virex • Premium Products 💎")

    await channel.send(content=interaction.user.mention, embed=embed, view=TicketControlView())


class TicketSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Select a category to open a ticket...",
            min_values=1, max_values=1, custom_id="virex_ticket_select",
            options=[
                discord.SelectOption(label=v["label"], description=v["description"],
                                     emoji=v["emoji"], value=k)
                for k, v in TICKET_CATEGORIES.items()])

    async def callback(self, interaction: discord.Interaction):
        cat_key = self.values[0]
        guild = interaction.guild
        for ch in guild.text_channels:
            if ch.topic and f"uid-{interaction.user.id}" in ch.topic:
                await interaction.response.send_message(
                    f"❌ You already have an open ticket: {ch.mention}", ephemeral=True)
                return
        await interaction.response.send_modal(TicketQuestionsModal(cat_key))


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="virex_close_ticket")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        info = await db_get_ticket(str(interaction.channel.id))
        if not info:
            await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True)
            return
        if not is_staff(interaction.user) and info["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Only staff or the ticket owner can close this.", ephemeral=True)
            return
        await interaction.response.send_message("🔒 Closing in 5 seconds...")
        await asyncio.sleep(5)
        await close_ticket(interaction.channel, interaction.guild, closed_by=interaction.user)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.success, emoji="✋", custom_id="virex_claim_ticket")
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Only staff can claim tickets.", ephemeral=True)
            return
        await interaction.response.send_message(embed=discord.Embed(
            description=f"✋ **{interaction.user.mention}** has claimed this ticket!", color=VIREX_COLOR))


class StoreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Visit Store", style=discord.ButtonStyle.link,
                                        url=VIREX_WEBSITE, emoji="🌐", row=0))

    @discord.ui.button(label="Open Purchase Ticket", style=discord.ButtonStyle.primary,
                       emoji="🛒", custom_id="virex_store_ticket", row=1)
    async def store_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        view   = discord.ui.View(timeout=60)
        select = TicketSelect()
        select.options = [o for o in select.options if o.value == "purchase"]
        view.add_item(select)
        await interaction.response.send_message("Select ticket type:", view=view, ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self, oauth_url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="Verify with Discord", style=discord.ButtonStyle.link, url=oauth_url, emoji="🔐"))

# ============================================================
#  VIEW — POST APPROVAL (Moderation)
# ============================================================
class ApproveView(discord.ui.View):
    def __init__(self, link: str, author: discord.Member):
        super().__init__(timeout=300)
        self.link   = link
        self.author = author

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_any_staff(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to approve posts.", ephemeral=True)
            return
        post_channel = bot.get_channel(POST_CHANNEL_ID)
        if not post_channel:
            await interaction.response.send_message("❌ Post channel not found.", ephemeral=True)
            return
        embed = discord.Embed(
            title="🎬 New Video Posted",
            description=f"{self.link}\n\nMake sure to like and comment on the video.\nSubscribe for more content.",
            color=0x2F3136
        )
        embed.set_footer(text=f"Posted by {self.author}")
        await post_channel.send(content="@everyone", embed=embed)
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("✅ Post approved and sent.", ephemeral=True)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_any_staff(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to deny posts.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("🚫 Post denied.", ephemeral=True)

# ============================================================
#  VIEW — BAN REQUEST (persistent, survives restarts)
# ============================================================
class BanRequestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def _get_user_id(self, interaction: discord.Interaction) -> int | None:
        # User-ID aus dem Embed-Footer lesen ("User ID: 123...")
        try:
            embed = interaction.message.embeds[0]
            footer = embed.footer.text or ""
            return int(footer.replace("User ID:", "").strip())
        except Exception:
            return None

    @discord.ui.button(label="✅ Approve — Lifetime Ban", style=discord.ButtonStyle.green,
                       custom_id="virex_ban_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the **{ADMIN_ROLE_NAME}** role to approve ban requests.", ephemeral=True)
            return
        uid = self._get_user_id(interaction)
        if not uid:
            await interaction.response.send_message("❌ Could not read the user ID from this request.", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            await interaction.guild.ban(discord.Object(id=uid), reason=f"Ban request approved by {interaction.user}")
            result = f"🔨 **LIFETIME BAN** — approved by {interaction.user.mention}"
            color = 0x57F287
        except discord.NotFound:
            result = f"⚠️ Approved by {interaction.user.mention}, but user not found."
            color = 0xF39C12
        except discord.Forbidden:
            result = f"⚠️ Approved by {interaction.user.mention}, but I'm missing ban permissions."
            color = 0xF39C12
        except Exception as e:
            result = f"⚠️ Approved by {interaction.user.mention}, but ban failed: {e}"
            color = 0xF39C12
        embed = interaction.message.embeds[0]
        embed.color = color
        embed.add_field(name="📋 Decision", value=result, inline=False)
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red,
                       custom_id="virex_ban_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the **{ADMIN_ROLE_NAME}** role to deny ban requests.", ephemeral=True)
            return
        await interaction.response.defer()
        embed = interaction.message.embeds[0]
        embed.color = 0x888888
        embed.add_field(name="📋 Decision",
                        value=f"🚫 **Denied** by {interaction.user.mention} — no ban was issued.",
                        inline=False)
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(embed=embed, view=self)

# ============================================================
#  VIEW — GIVEAWAY
# ============================================================
class GiveawayView(discord.ui.View):
    def __init__(self, message_id: int):
        super().__init__(timeout=None)
        self.message_id = message_id

    @discord.ui.button(label="🎉 Enter", style=discord.ButtonStyle.primary, custom_id="giveaway_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.message_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway has already ended.", ephemeral=True)
            return
        data = active_giveaways[self.message_id]
        user_id = interaction.user.id
        if user_id in data["entries"]:
            data["entries"].discard(user_id)
            await interaction.response.send_message("✅ You have **left** the giveaway.", ephemeral=True)
        else:
            data["entries"].add(user_id)
            await interaction.response.send_message(f"🎉 You are now entered in the giveaway for **{data['prize']}**!", ephemeral=True)
        try:
            embed = build_giveaway_embed(data["prize"], data["winners"], data["host_id"],
                                         data["ends_at"], len(data["entries"]), data.get("requirements"))
            await interaction.message.edit(embed=embed)
        except Exception:
            pass

# ============================================================
#  BACKGROUND TASKS
# ============================================================
@tasks.loop(minutes=30)
async def auto_close_task():
    now      = datetime.now(timezone.utc)
    all_t    = await db_all_tickets()
    to_close = []
    for cid, info in all_t.items():
        if info.get("status") != "open":
            continue
        if not info.get("auto_close", True):
            continue
        if not info.get("last_activity"):
            continue
        last = datetime.fromisoformat(info["last_activity"])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if now - last >= timedelta(hours=AUTO_CLOSE_HOURS):
            to_close.append(cid)
    for cid in to_close:
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            continue
        channel = guild.get_channel(int(cid))
        if channel:
            try:
                await channel.send("⏰ Auto-closing due to inactivity...")
                await close_ticket(channel, guild)
            except Exception as e:
                print(f"Auto-close error for {cid}: {e}")


@auto_close_task.before_loop
async def before_auto_close():
    await bot.wait_until_ready()


@tasks.loop(hours=6)
async def token_refresh_loop():
    now       = datetime.now(timezone.utc)
    all_v     = await db_all_verified()
    refreshed = failed = 0
    for uid, info in all_v.items():
        if not info.get("refresh_token"):
            continue
        if info.get("token_expired"):
            continue
        last_refresh_str = info.get("token_refreshed_at") or info.get("verified_at")
        if not last_refresh_str:
            continue
        try:
            last_refresh = datetime.fromisoformat(last_refresh_str)
            if last_refresh.tzinfo is None:
                last_refresh = last_refresh.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if now - last_refresh >= timedelta(days=6):
            success = await refresh_token(uid)
            if success:
                refreshed += 1
            else:
                failed += 1
            await asyncio.sleep(0.5)
    if refreshed or failed:
        print(f"[TOKEN REFRESH] ✅ Refreshed: {refreshed} | ❌ Failed: {failed}")


@token_refresh_loop.before_loop
async def before_token_refresh():
    await bot.wait_until_ready()

# ============================================================
#  EVENTS  (jeweils EIN Handler — beide Bots zusammengeführt)
# ============================================================
# ============================================================
#  CLAIM ROLE — SELLAUTH ORDER VERIFICATION
# ============================================================
def _norm(s) -> str:
    return str(s or "").strip().lower()


def _order_id_candidates(inv: dict) -> set[str]:
    """All identifier strings that could legitimately represent this invoice,
    so we match whatever format the customer pastes (numeric id, salt, or the
    full unique_id like 'ba1181294bc7a-0000000000971')."""
    cands: set[str] = set()
    iid  = str(inv.get("id", "")).strip()
    salt = str(inv.get("salt", "")).strip()
    uid  = str(inv.get("unique_id", "")).strip()
    if iid:
        cands.add(iid)
    if salt:
        cands.add(salt)
    if uid:
        cands.add(uid)
    if salt and iid.isdigit():
        cands.add(f"{salt}-{int(iid):013d}")   # reconstruct unique_id format
    return {c.lower() for c in cands if c}


def _order_matches(inv: dict, raw_order_id: str) -> bool:
    raw = _norm(raw_order_id)
    if not raw:
        return False
    cands = _order_id_candidates(inv)
    if raw in cands:
        return True
    # If the user pasted a unique_id-style string, also try its numeric tail.
    if "-" in raw:
        tail = raw.rsplit("-", 1)[-1].lstrip("0") or "0"
        if tail in cands:
            return True
    # If they pasted only the numeric id, compare int-wise to invoice id.
    if raw.isdigit() and str(inv.get("id", "")).isdigit():
        return int(raw) == int(inv["id"])
    return False


async def sellauth_lookup_order(order_id_raw: str, email: str) -> dict:
    """Look an order up in SellAuth by email, then match the order id locally.

    Returns:
        {"ok": True,  "invoice": {...}}                         on a valid match
        {"ok": False, "reason": "<machine reason>", "detail": "<human text>"}
    """
    if not SELLAUTH_API_KEY or not SELLAUTH_SHOP_ID:
        return {"ok": False, "reason": "not_configured",
                "detail": "The claim system is not configured yet. Please contact staff."}

    url = f"{SELLAUTH_API_BASE}/shops/{SELLAUTH_SHOP_ID}/invoices"
    headers = {
        "Authorization": f"Bearer {SELLAUTH_API_KEY}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
    # Filter by email server-side; we match the order id + status ourselves.
    params = {"email": email.strip(), "perPage": 100}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                text = await resp.text()
                if resp.status == 401:
                    print("[CLAIM] SellAuth 401 — check SELLAUTH_API_KEY")
                    return {"ok": False, "reason": "auth_error",
                            "detail": "The claim system could not authenticate with the store. Please contact staff."}
                if resp.status == 404:
                    return {"ok": False, "reason": "shop_not_found",
                            "detail": "Store not found. Please contact staff (check SELLAUTH_SHOP_ID)."}
                if resp.status != 200:
                    print(f"[CLAIM] SellAuth {resp.status}: {text[:300]}")
                    return {"ok": False, "reason": "api_error",
                            "detail": f"The store returned an error ({resp.status}). Please try again later."}
                try:
                    data = await resp.json()
                except Exception:
                    print(f"[CLAIM] SellAuth non-JSON response: {text[:300]}")
                    return {"ok": False, "reason": "api_error",
                            "detail": "Unexpected response from the store. Please try again later."}
    except asyncio.TimeoutError:
        return {"ok": False, "reason": "timeout",
                "detail": "The store took too long to respond. Please try again in a moment."}
    except Exception as e:
        print(f"[CLAIM] SellAuth exception: {type(e).__name__}: {e}")
        return {"ok": False, "reason": "exception",
                "detail": "Could not reach the store right now. Please try again later."}

    invoices = data.get("data", data if isinstance(data, list) else [])
    if not isinstance(invoices, list):
        invoices = []

    # 1) find an invoice whose id matches (email already filtered, but double-check it)
    matched = None
    for inv in invoices:
        if not isinstance(inv, dict):
            continue
        if _norm(inv.get("email")) != _norm(email):
            continue
        if _order_matches(inv, order_id_raw):
            matched = inv
            break

    if not matched:
        return {"ok": False, "reason": "no_match",
                "detail": "No order was found matching that **order ID** and **email**.\n"
                          "Double-check both and make sure you use the email you ordered with."}

    # 2) status must be a completed/paid order
    if _norm(matched.get("status")) not in CLAIM_VALID_STATUSES:
        return {"ok": False, "reason": "not_completed",
                "detail": f"That order is not completed (status: `{matched.get('status')}`). "
                          "Only fully paid orders can be claimed."}

    return {"ok": True, "invoice": matched}


async def _claim_log(guild: discord.Guild, embed: discord.Embed):
    if not CLAIM_LOG_CHANNEL_ID:
        return
    ch = guild.get_channel(CLAIM_LOG_CHANNEL_ID) if guild else None
    if ch:
        try:
            await ch.send(embed=embed)
        except discord.HTTPException:
            pass


async def process_claim(member: discord.Member, guild: discord.Guild,
                        order_id_raw: str, email: str) -> tuple[bool, str]:
    """Verify an order and grant the claim role. Returns (success, message)."""
    lookup = await sellauth_lookup_order(order_id_raw, email)
    if not lookup["ok"]:
        return False, f"❌ {lookup['detail']}"

    inv        = lookup["invoice"]
    order_key  = str(inv.get("id"))            # canonical dedupe key
    inv_email  = inv.get("email", email)

    # Already claimed?
    existing = await db_get_claim(order_key)
    if existing:
        if existing["claimed_by"] == member.id:
            return False, "ℹ️ You have **already claimed** this order — you should already have the role."
        return False, ("❌ This order has **already been claimed** by another account. "
                       "If you believe this is a mistake, please open a support ticket.")

    # Find + grant the role
    role = discord.utils.find(lambda r: r.name.lower() == CLAIM_ROLE_NAME.lower(), guild.roles)
    if not role:
        return False, f"❌ The `{CLAIM_ROLE_NAME}` role does not exist on the server. Please contact staff."
    if role >= guild.me.top_role:
        return False, "❌ I can't assign the role because it's above my highest role. Please contact staff."

    # Reserve the order atomically BEFORE assigning, so it can't be double-claimed.
    reserved = await db_mark_order_claimed(order_key, order_key, inv_email, member.id, guild.id)
    if not reserved:
        return False, ("❌ This order has **already been claimed**. "
                       "If you believe this is a mistake, please open a support ticket.")

    try:
        await member.add_roles(role, reason=f"Claimed SellAuth order {order_key}")
    except discord.Forbidden:
        return False, "❌ I don't have permission to give you the role. Please contact staff."
    except discord.HTTPException as e:
        print(f"[CLAIM] add_roles failed: {e}")
        return False, "❌ Something went wrong assigning the role. Please try again or contact staff."

    # Log
    log_embed = discord.Embed(
        title="✅ Customer Role Claimed",
        color=VIREX_COLOR_SUCCESS, timestamp=datetime.now(timezone.utc))
    log_embed.add_field(name="User",     value=f"{member.mention} (`{member.id}`)", inline=True)
    log_embed.add_field(name="Order ID", value=f"`{order_key}`", inline=True)
    log_embed.add_field(name="Email",    value=f"`{inv_email}`", inline=False)
    log_embed.set_footer(text="Virex • Claim System")
    await _claim_log(guild, log_embed)

    return True, (f"✅ **Verified!** You've been given the **{role.name}** role in **{guild.name}**.\n"
                  f"Thank you for your purchase! 💎")


async def start_claim_dm(interaction: discord.Interaction):
    """Runs the button → DM → order id → email → verify flow."""
    user  = interaction.user
    guild = interaction.guild

    if user.id in claim_in_progress:
        await interaction.response.send_message(
            "⏳ You already have a claim session open — check your DMs.", ephemeral=True)
        return

    # Try to open a DM first so we can tell the user immediately if DMs are closed.
    try:
        dm = await user.create_dm()
        await dm.send(embed=discord.Embed(
            title="🔑 Claim Your Customer Role",
            description=("Let's verify your purchase.\n\n"
                         "**Step 1/2 — Reply with your `Order ID`.**\n"
                         "You can find it on your SellAuth receipt / order confirmation.\n\n"
                         f"*You have {CLAIM_DM_TIMEOUT // 60} minutes. Type `cancel` to stop.*"),
            color=VIREX_COLOR))
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I couldn't DM you. Please enable **Direct Messages** from server members "
            "(Privacy Settings) and click the button again.", ephemeral=True)
        return

    await interaction.response.send_message(
        "📩 Check your **DMs** — I've sent you the verification steps.", ephemeral=True)

    claim_in_progress.add(user.id)

    def check(m: discord.Message) -> bool:
        return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)

    try:
        # Step 1 — order id
        try:
            msg_order = await bot.wait_for("message", check=check, timeout=CLAIM_DM_TIMEOUT)
        except asyncio.TimeoutError:
            await dm.send("⌛ Timed out. Click the button again when you're ready.")
            return
        order_id = msg_order.content.strip()
        if order_id.lower() == "cancel":
            await dm.send("❌ Cancelled.")
            return

        # Step 2 — email
        await dm.send(embed=discord.Embed(
            title="📧 Step 2/2 — Email",
            description=("Now reply with the **email address you used for the order**.\n\n"
                         f"*Type `cancel` to stop.*"),
            color=VIREX_COLOR))
        try:
            msg_email = await bot.wait_for("message", check=check, timeout=CLAIM_DM_TIMEOUT)
        except asyncio.TimeoutError:
            await dm.send("⌛ Timed out. Click the button again when you're ready.")
            return
        email = msg_email.content.strip()
        if email.lower() == "cancel":
            await dm.send("❌ Cancelled.")
            return

        # Re-fetch member (in case cache is stale) and verify
        member = guild.get_member(user.id) if guild else None
        if member is None:
            await dm.send("❌ I couldn't find you in the server. Please rejoin and try again.")
            return

        await dm.send("🔎 Verifying your order, one moment...")
        success, result_msg = await process_claim(member, guild, order_id, email)
        await dm.send(result_msg)

    except Exception as e:
        print(f"[CLAIM DM] {type(e).__name__}: {e}")
        try:
            await dm.send("❌ Something went wrong. Please try again later or open a ticket.")
        except discord.HTTPException:
            pass
    finally:
        claim_in_progress.discard(user.id)


class ClaimRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Customer Role", style=discord.ButtonStyle.primary,
                       emoji="🔑", custom_id="virex_claim_role")
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            await interaction.response.send_message("❌ Use this in the server.", ephemeral=True)
            return
        await start_claim_dm(interaction)


@bot.command(name="claimrole")
async def cmd_claimrole(ctx: commands.Context):
    """Post the 'Claim Customer Role' verification panel (staff only)."""
    if not is_any_staff(ctx.author):
        await ctx.reply("❌ You don't have permission to use this.", mention_author=False)
        return

    embed = discord.Embed(
        title="🔑 Claim Your Customer Role",
        description=("Press the button below and verify your order via **DM**.\n\n"
                     "You'll be asked for your **Order ID** and the **email** you ordered with. "
                     "If they match a completed order that hasn't been claimed yet, you'll "
                     "instantly receive the customer role."),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc))
    set_logo(embed)
    embed.set_footer(text="Virex • Verification System")

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass

    await ctx.send(embed=embed, view=ClaimRoleView())


@bot.event
async def on_ready():
    global whitelist_cache
    print(f"✅ Virex Bot online — {bot.user}")

    await bot.change_presence(activity=discord.Game(name="virex.gg | $commands"))

    # Whitelist-Cache laden (Moderation)
    whitelist_cache = await db_load_whitelist()
    print(f"✅ Whitelist cache loaded: {len(whitelist_cache)} user(s)")

    # Persistente Views (überleben Neustarts)
    bot.add_view(BanRequestView())
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    bot.add_view(StoreView())
    bot.add_view(ClaimRoleView())

    # Background-Tasks
    if not auto_close_task.is_running():
        auto_close_task.start()
        print("🔄 Auto-close task started (runs every 30min)")
    if not token_refresh_loop.is_running():
        token_refresh_loop.start()
        print("🔄 Token refresh loop started (runs every 6h)")

    # Slash-Commands syncen
    # Global sync (propagates to Discord within up to ~1h, but is what
    # actually clears out renamed/removed commands like the old /r6guide).
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s) globally (may take up to 1h to update everywhere)")
    except Exception as e:
        print(f"❌ Failed to sync commands globally: {e}")

    # Guild-specific sync — appears INSTANTLY in your server, so you don't
    # have to wait for the global propagation above while testing.
    if GUILD_ID:
        try:
            guild_obj = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            guild_synced = await bot.tree.sync(guild=guild_obj)
            print(f"✅ Synced {len(guild_synced)} slash command(s) instantly to guild {GUILD_ID}")
        except Exception as e:
            print(f"❌ Failed to sync commands to guild {GUILD_ID}: {e}")

    # Flask nur einmal starten
    if not hasattr(bot, 'flask_started'):
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        bot.flask_started = True
        print("✅ Flask HTTP server started on port 8080")

    print("✅ All Virex systems ready!")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ── DMs: skip guild-only moderation (word filter, silent prefix, ticket
    #    activity). The claim-role flow collects order id / email here via
    #    wait_for, which fires independently of this handler.
    if message.guild is None:
        await bot.process_commands(message)
        return

    # ── Silent prefix "*" — sendet als Bot (nur Staff!) ──────────────────────
    if message.content.startswith(SILENT_PREFIX):
        if not is_any_staff(message.author):
            return
        content = message.content[len(SILENT_PREFIX):].strip()
        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass
        if content:
            await message.channel.send(content)
        return

    # ── Word filter (Staff + Whitelist umgehen ihn) ──────────────────────────
    staff_member   = is_any_staff(message.author)
    is_whitelisted = message.author.id in whitelist_cache
    if not staff_member and not is_whitelisted:
        matched = check_blacklist(message.content)
        if matched:
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            warn_embed = discord.Embed(
                title="⚠️ Message Removed",
                description=(
                    f"{message.author.mention}, one or more words in your message are **not allowed** on this server.\n\n"
                    "**Please rephrase your message. Examples:**\n"
                    "• `cheat` → `chair`\n"
                    "• `spoof` → `woof`\n"
                    "• `spoofer` → `woofer`\n"
                    "• `hack` → `h4ck`"
                ),
                color=0x6f2cff
            )
            warn_embed.set_footer(text="Virex — Word Filter")
            try:
                await message.channel.send(
                    content=message.author.mention,
                    embed=warn_embed,
                    delete_after=10
                )
            except discord.Forbidden:
                pass
            await log_deleted_message(message, matched)
            return

    # ── Staff-Leaderboard: Punkte für Trial Staff (not trusted) sammeln ──────
    if db_pool and has_staff_role(message.author):
        try:
            await db_add_staff_points(message.author.id, message.guild.id, POINTS_PER_MESSAGE)
        except Exception as e:
            print(f"[LEADERBOARD] {e}")

    # ── Ticket last_activity aktualisieren ───────────────────────────────────
    if db_pool:
        try:
            cid  = str(message.channel.id)
            info = await db_get_ticket(cid)
            if info and info.get("status") == "open":
                await db_update_ticket(cid, last_activity=datetime.now(timezone.utc).isoformat())
        except Exception as e:
            print(f"[TICKET ACTIVITY] {e}")

    await bot.process_commands(message)


@bot.event
async def on_member_join(member: discord.Member):
    # 1) Blacklist-Auto-Ban (Moderation)
    if await is_blacklisted(member.id):
        try:
            blacklist_entry = await get_blacklist_entry(member.id)
            reason = blacklist_entry['reason'] if blacklist_entry else "Blacklisted"
            await member.ban(reason=f"Blacklisted: {reason}")
            log_channel = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(title="🔨 Auto-Ban — Blacklist", color=0xFF0000, timestamp=utcnow())
                embed.add_field(name="👤 User", value=f"{member} (`{member.id}`)", inline=False)
                embed.add_field(name="📝 Reason", value=reason, inline=False)
                embed.set_footer(text="Auto-banned on join")
                await log_channel.send(embed=embed)
            return  # kein Welcome für gebannte User
        except Exception as e:
            print(f"❌ Error auto-banning {member.id}: {e}")

    # 2) Welcome-Nachricht (Ticket-Bot)
    if not WELCOME_CHANNEL_ID:
        return
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return
    member_count = member.guild.member_count
    joined_ts    = int(member.joined_at.timestamp()) if member.joined_at else int(datetime.now(timezone.utc).timestamp())
    account_ts   = int(member.created_at.timestamp())
    embed = discord.Embed(
        title="👋 Welcome to Virex!",
        description=(
            f"Hey {member.mention}, welcome to the **Virex** server! 🎉\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔐 **Get started:** Verify your account to unlock all channels.\n"
            f"🌐 **Shop:** [{VIREX_WEBSITE}]({VIREX_WEBSITE})\n"
            "🎫 **Support:** Open a ticket if you need help.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*You are member **#{member_count}** — glad to have you!*"
        ),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(name=f"{member.display_name} joined!",
                     icon_url=member.display_avatar.url if member.display_avatar else None)
    embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
    if VIREX_LOGO and VIREX_LOGO.startswith("https://"):
        embed.set_image(url=VIREX_LOGO)
    embed.add_field(name="📅 Account Created", value=f"<t:{account_ts}:R>", inline=True)
    embed.add_field(name="📥 Joined Server",   value=f"<t:{joined_ts}:R>",  inline=True)
    embed.add_field(name="👥 Member Count",    value=f"`{member_count}`",   inline=True)
    embed.set_footer(text="Virex • Welcome 🔵")
    await channel.send(content=member.mention, embed=embed)


@bot.event
async def on_member_remove(member: discord.Member):
    uid = str(member.id)
    info = await db_get_verified(uid)
    if info:
        await db_update_verified_field(
            uid,
            last_left_guild=str(member.guild.id),
            left_at=datetime.now(timezone.utc).isoformat(),
        )
        print(f"[BACKUP] 📤 {member.name} ({uid}) left {member.guild.name} — token saved in DB")
    if not WELCOME_CHANNEL_ID:
        return
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return
    member_count = member.guild.member_count
    account_ts   = int(member.created_at.timestamp())
    embed = discord.Embed(
        title="📤 Member Left",
        description=(
            f"**{member.display_name}** has left the server.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*We now have **{member_count}** members.*"
        ),
        color=VIREX_COLOR_DANGER, timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(name=f"{member.display_name} left",
                     icon_url=member.display_avatar.url if member.display_avatar else None)
    embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
    embed.add_field(name="📅 Account Created", value=f"<t:{account_ts}:R>", inline=True)
    embed.add_field(name="👥 Members Now",     value=f"`{member_count}`",   inline=True)
    embed.set_footer(text="Virex • Goodbye 🔵")
    await channel.send(embed=embed)


@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handled NUR den smedia-Ticket-Button. Alle anderen Views laufen normal weiter."""
    if interaction.type != discord.InteractionType.component:
        return
    if not interaction.data or interaction.data.get("custom_id") != "virex_media_ticket":
        return

    # Defer immediately — channel creation + DB write can take >3s.
    await interaction.response.defer(ephemeral=True, thinking=True)

    guild = interaction.guild
    for ch in guild.text_channels:
        if ch.topic and f"uid-{interaction.user.id}" in ch.topic:
            await interaction.followup.send(
                f"❌ You already have an open ticket: {ch.mention}", ephemeral=True)
            return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user:   discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }
    for rid in STAFF_ROLE_IDS + ADMIN_ROLE_IDS:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    cat_channel = guild.get_channel(TICKET_CATEGORY_ID)
    # Kanalname jetzt aus dem Discord-Usernamen statt einer laufenden Nummer.
    base_name    = sanitize_channel_name(interaction.user.name)
    channel_name = make_unique_ticket_channel_name(guild, base_name)
    try:
        ch = await guild.create_text_channel(
            name=channel_name, overwrites=overwrites, category=cat_channel,
            topic=f"uid-{interaction.user.id} | support | open"
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Could not create ticket: {e}", ephemeral=True)
        return

    await db_set_ticket(str(ch.id), {
        "user_id": interaction.user.id, "category": "support",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
        "auto_close": True, "status": "open"
    })
    await interaction.followup.send(f"✅ Ticket created: {ch.mention}", ephemeral=True)

    embed = discord.Embed(
        title="🎬 Media Creator Application",
        description=(f"Welcome, {interaction.user.mention}! 👋\n\n"
                     "**You've applied for the Virex Media Creator program.**\n\n"
                     "Please share your **channel link, follower count, average views** and any relevant clips below.\n"
                     "Our team will review your profile and get back to you shortly."),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    set_logo(embed)
    embed.set_footer(text="Virex • Media Creator Program 🎬")
    await ch.send(content=interaction.user.mention, embed=embed, view=TicketControlView())


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing arguments.", delete_after=5)
        return
    print(f"[ERROR] {error}")

# ============================================================
#  PREFIX COMMANDS ($)
# ============================================================
@bot.command(name="commands")
async def commands_list(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    embed = discord.Embed(title="📋 Virex Bot — Command List", color=0x6f2cff)
    embed.add_field(
        name="📌 Prefix Commands (`$`)",
        value=(
            "`$commands` — Shows this command list\n"
            "`$manual` — AnyDesk manual guide\n"
            "`$msinfo` — msinfo32 fix info (€10 manual)\n"
            "`$activate` — Windows activation guide\n"
            "`$tempvsperm` — Temp vs Perm Woofer info\n"
            "`$proof` — Purchase proof instructions\n"
            "`$ban <user_id> <reason>` — Send a ban request (admins approve/deny)\n"
            "`$scam` — Post a scam warning (@everyone)\n"
            "`$anydesk` — AnyDesk setup guide\n\n"
            "**🔒 Blacklist Commands (Admin only):**\n"
            "`$blacklist <user_id> <reason>` — Add user to blacklist\n"
            "`$unblacklist <user_id>` — Remove user from blacklist\n"
            "`$blist` — Show all blacklisted users"
        ),
        inline=False
    )
    embed.add_field(
        name="⚡ Slash — Moderation & Community",
        value=(
            "`/post <link>` — Submit a video for approval\n"
            "`/changelog <game> <update>` — Post a game update\n"
            "`/giveaway <duration> <winners> <prize> [requirements]` — Start a giveaway\n"
            "`/gend <message_id>` — End a giveaway immediately\n"
            "`/greroll <channel> <message_id>` — Reroll a giveaway winner\n"
            "`/status` — Show current product status\n"
            "`/setstatus <product> <status>` — Manually update a product's status\n"
            "`/vouch <stars> <message>` — Leave a vouch (customers only)\n"
            "`/whitelist @user` — Whitelist a user (bypasses word filter)\n"
            "`/unwhitelist @user` — Remove whitelist from a user\n"
            "`/whitelistview` — Show all whitelisted users\n"
            "`/guide` — Vega R6 setup guide\n"
            f"`/leaderboard` — {STAFF_ROLE_NAME} activity leaderboard ({STAFF_ROLE_NAME} only)"
        ),
        inline=False
    )
    embed.add_field(
        name="🎫 Slash — Tickets, Verify & Backup",
        value=(
            "`/panel` — Send the ticket panel (Admin)\n"
            "`/store` — Send the store panel (Admin)\n"
            "`/close` — Close the current ticket (Staff)\n"
            "`/add <user>` — Add a user to the ticket (Staff)\n"
            "`/remove <user>` — Remove a user from the ticket (Staff)\n"
            "`/rename <name>` — Rename the current ticket (Staff)\n"
            "`/autoclose <enabled>` — Toggle auto-close (Staff)\n"
            "`/smedia` — Media Creator announcement (Admin)\n"
            "`/verifypanel` — Send the verification panel (Admin)\n"
            "`/backup_restore <user_id>` — Restore one user (Admin)\n"
            "`/backup_restore_all` — Restore all users (Admin)\n"
            "`/backup_list` — Show backup list (Admin)\n"
            "`/backup_stats` — Show backup statistics (Admin)\n"
            "`/token_refresh_now` — Force token refresh (Admin)\n"
            "`/migrate_json` — Import JSON into PostgreSQL (Admin)"
        ),
        inline=False
    )
    embed.add_field(name="🔇 Silent Prefix (`*`)", value="`*<text>` — Send a message anonymously", inline=False)
    embed.set_footer(text=f"All staff commands require the {STAFF_ROLE_NAME} role • Virex Team")
    await ctx.send(embed=embed)

# ─── BLACKLIST PREFIX COMMANDS ────────────────────────────────────────────────
@bot.command(name="blacklist")
async def blacklist_user(ctx, user_id: str = None, *, reason: str = None):
    if not await blacklist_admin_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    if not user_id or not reason:
        embed = discord.Embed(title="❌ Incorrect Usage", description="Usage: `$blacklist <user_id> <reason>`", color=0xFF4444)
        await ctx.send(embed=embed, delete_after=10)
        return
    try:
        uid = int(user_id)
    except ValueError:
        await ctx.send(embed=discord.Embed(title="❌ Invalid User ID", description="User ID must be a number.", color=0xFF4444), delete_after=10)
        return
    try:
        user = await bot.fetch_user(uid)
        user_display = f"{user} (`{uid}`)"
        avatar = user.display_avatar.url
    except Exception:
        user_display = f"Unknown User (`{uid}`)"
        avatar = None
    success = await add_to_blacklist(uid, reason, ctx.author.id, ctx.guild.id)
    if success:
        try:
            member = await ctx.guild.fetch_member(uid)
            await member.ban(reason=f"Blacklisted: {reason}")
            ban_status = "✅ User has been banned from the server"
        except discord.NotFound:
            ban_status = "⚠️ User is not a member of the server"
        except discord.Forbidden:
            ban_status = "⚠️ Could not ban user (missing permissions)"
        except Exception as e:
            ban_status = f"⚠️ Could not ban user: {e}"
        embed = discord.Embed(title="✅ User Blacklisted", color=0xFF0000)
        embed.add_field(name="👤 User", value=user_display, inline=False)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.add_field(name="⏰ Timestamp", value=utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.add_field(name="🔨 Ban Status", value=ban_status, inline=False)
        if avatar:
            embed.set_thumbnail(url=avatar)
        embed.set_footer(text=f"Blacklisted by {ctx.author} • Virex Team")
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=discord.Embed(title="❌ Database Error", description="Failed to add user to blacklist.", color=0xFF4444), delete_after=10)


@bot.command(name="unblacklist")
async def unblacklist_user(ctx, user_id: str = None):
    if not await blacklist_admin_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    if not user_id:
        await ctx.send(embed=discord.Embed(title="❌ Incorrect Usage", description="Usage: `$unblacklist <user_id>`", color=0xFF4444), delete_after=10)
        return
    try:
        uid = int(user_id)
    except ValueError:
        await ctx.send(embed=discord.Embed(title="❌ Invalid User ID", description="User ID must be a number.", color=0xFF4444), delete_after=10)
        return
    if not await is_blacklisted(uid):
        await ctx.send(embed=discord.Embed(title="❌ Not Blacklisted", description=f"User `{uid}` is not on the blacklist.", color=0xFF4444), delete_after=10)
        return
    entry = await get_blacklist_entry(uid)
    success = await remove_from_blacklist(uid)
    if success:
        try:
            user = await bot.fetch_user(uid)
            user_display = f"{user} (`{uid}`)"
            avatar = user.display_avatar.url
        except Exception:
            user_display = f"Unknown User (`{uid}`)"
            avatar = None
        embed = discord.Embed(title="✅ User Removed from Blacklist", color=0x00FF00)
        embed.add_field(name="👤 User", value=user_display, inline=False)
        embed.add_field(name="📝 Previous Reason", value=entry['reason'], inline=False)
        embed.add_field(name="⏰ Was Blacklisted Since", value=entry['blacklisted_at'].strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        if avatar:
            embed.set_thumbnail(url=avatar)
        embed.set_footer(text=f"Removed by {ctx.author} • Virex Team")
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=discord.Embed(title="❌ Database Error", description="Failed to remove user from blacklist.", color=0xFF4444), delete_after=10)


@bot.command(name="blist")
async def list_blacklist(ctx):
    if not await blacklist_admin_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    records = await get_blacklist(ctx.guild.id)
    if not records:
        await ctx.send(embed=discord.Embed(title="📋 Blacklist", description="No users are currently blacklisted.", color=0x57F287))
        return
    embeds = []
    items_per_page = 5
    for i in range(0, len(records), items_per_page):
        chunk = records[i:i + items_per_page]
        embed = discord.Embed(title=f"📋 Blacklist — Page {len(embeds) + 1}", color=0xFF0000)
        for record in chunk:
            try:
                user = await bot.fetch_user(record['user_id'])
                user_display = f"{user}"
            except Exception:
                user_display = "Unknown User"
            try:
                staff = await bot.fetch_user(record['blacklisted_by'])
                staff_display = f"{staff}"
            except Exception:
                staff_display = "Unknown Staff"
            value = (
                f"**User ID:** `{record['user_id']}`\n"
                f"**Reason:** {record['reason']}\n"
                f"**Blacklisted By:** {staff_display}\n"
                f"**Date:** {record['blacklisted_at'].strftime('%d.%m.%Y at %H:%M:%S UTC')}"
            )
            embed.add_field(name=user_display, value=value, inline=False)
        embed.set_footer(text=f"Total: {len(records)} user(s) • Virex Team")
        embeds.append(embed)
    if embeds:
        await ctx.send(embed=embeds[0])

# ─── INFO PREFIX COMMANDS ─────────────────────────────────────────────────────
@bot.command(name="manual")
async def manual(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    embed = discord.Embed(title="📖 AnyDesk Manual — Virex", color=0x5865F2)
    embed.add_field(name="💰 Perm Guide Assistance", value="For **€20** you can hire a Staff member *(NOT Trial Staff)* to perform the Perm Guide for you via **AnyDesk**.", inline=False)
    embed.add_field(name="⚠️ Note", value="This is different from the ASUS Manual.", inline=False)
    embed.set_footer(text="Virex Team")
    await ctx.send(embed=embed)


@bot.command(name="msinfo")
async def msinfo(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    embed = discord.Embed(
        title="🛠️ msinfo32 Fix — Manual Assistance",
        description=(
            "If your **msinfo32** (System Information) is not working, showing "
            "errors, or won't open correctly, our staff can fix it for you."
        ),
        color=0x5865F2
    )
    embed.add_field(
        name="💰 Price",
        value="This manual fix is available for **€10**.",
        inline=False
    )
    embed.add_field(
        name="🧑‍🔧 What We Do",
        value=(
            "- Repair / restore your msinfo32\n"
            "- Make sure it opens and displays correctly\n"
            "- Done manually by a Staff member *(NOT Trial Staff)* via **AnyDesk**"
        ),
        inline=False
    )
    embed.add_field(
        name="📋 How to Get It",
        value="Open a support ticket and let a Staff member know you want the **msinfo32 fix**.",
        inline=False
    )
    embed.set_footer(text="Virex Team")
    await ctx.send(embed=embed)


@bot.command(name="activate")
async def activate(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    embed = discord.Embed(title="🪟 Windows Activation Guide", description="Follow the steps below to activate Windows.", color=0x00B4D8)
    embed.add_field(name="1️⃣ Open PowerShell as Administrator", value="Press Windows → type `PowerShell` → Run as Administrator", inline=False)
    embed.add_field(name="2️⃣ Run this command", value="```irm https://get.activated.win/ | iex```", inline=False)
    embed.add_field(name="3️⃣ Press `4`", value="\u200b", inline=True)
    embed.add_field(name="4️⃣ Activate Windows → `1`", value="\u200b", inline=True)
    embed.add_field(name="5️⃣ Auto-Renewal → `5`", value="\u200b", inline=True)
    embed.set_footer(text="Virex Team")
    await ctx.send(embed=embed)


@bot.command(name="tempvsperm")
async def tempvsperm(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    embed = discord.Embed(title="🐾 Temp vs Perm Woofer", color=0xF4A261)
    embed.add_field(name="🔒 Permanent Woofer", value="- Permanent serial changes\n- Requires Windows reinstall\n- Long-term security", inline=False)
    embed.add_field(name="⏳ Temporary Woofer", value="- Lasts one session\n- Resets after restart\n- No reinstall needed", inline=False)
    embed.set_footer(text="Virex Team")
    await ctx.send(embed=embed)


@bot.command(name="proof")
async def proof(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    embed = discord.Embed(title="📸 Submit Purchase Proof", description="Follow the instructions below carefully.", color=0x2ECC71)
    embed.add_field(name="📧 Email Confirmation", value="- Screenshot your confirmation email\n- Amount & date must be visible", inline=False)
    embed.add_field(name="💳 Payment Proof", value="- Screenshot PayPal/Crypto transaction\n- Amount & recipient visible", inline=False)
    embed.add_field(name="⚠️ Important", value="Fake screenshots = permanent ban.", inline=False)
    embed.set_footer(text="Virex Team")
    await ctx.send(embed=embed)


@bot.command(name="ban")
async def ban_request(ctx, user_id: str = None, *, reason: str = None):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    if not user_id or not reason:
        await ctx.send(embed=discord.Embed(title="❌ Incorrect Usage", description="Usage: `$ban <user_id> <reason>`", color=0xFF4444), delete_after=5)
        return
    if not user_id.strip().isdigit():
        await ctx.send(embed=discord.Embed(title="❌ Invalid User ID", description="User ID must be a number.", color=0xFF4444), delete_after=5)
        return
    try:
        target_user = await bot.fetch_user(int(user_id))
        user_display = f"{target_user} (`{user_id}`)"
        avatar = target_user.display_avatar.url
    except Exception:
        user_display = f"Unknown User (`{user_id}`)"
        avatar = None
    embed = discord.Embed(title="🔨 Ban Request", color=0xFF0000)
    embed.add_field(name="👤 User", value=user_display, inline=False)
    embed.add_field(name="🛡️ Requested By", value=f"{ctx.author}", inline=False)
    embed.add_field(name="📝 Reason", value=reason, inline=False)
    if avatar:
        embed.set_thumbnail(url=avatar)
    embed.set_footer(text=f"User ID: {user_id}")
    ban_channel = bot.get_channel(BAN_REQUEST_CHANNEL_ID)
    if ban_channel:
        await ban_channel.send(embed=embed, view=BanRequestView())
        await ctx.send(embed=discord.Embed(
            title="✅ Ban Request Sent",
            description=f"Request sent to {ban_channel.mention} — admins can now approve or deny it.",
            color=0x00FF00), delete_after=5)
    else:
        await ctx.send("❌ Ban request channel not found. Set `BAN_REQUEST_CHANNEL_ID` in Railway variables.", delete_after=5)


@bot.command(name="scam")
async def scam(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    embed = discord.Embed(
        title="🚨 SCAM WARNING – PLEASE READ! 🚨",
        description=(
            "We've had reports of people sending DMs claiming that "
            "**'Virex is a scam'** or **'detected'**.\n\n"
            "⚠️ This is happening across multiple servers.\n\n"
            "👉 What you should do:\n"
            "🚫 Do NOT buy anything from them\n"
            "🔒 Block the user\n"
            "📸 Take screenshots\n"
            "🎟️ Open a support ticket"
        ),
        color=0x6f2cff
    )
    embed.set_image(url="https://i.imgur.com/t1JeHvA.png")
    embed.set_footer(text="Virex Team")
    await ctx.send(content="@everyone @here", embed=embed)


@bot.command(name="anydesk")
async def anydesk(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass
    embed = discord.Embed(
        title="🖥️ AnyDesk Setup Guide",
        description=(
            "**Step 1: Download AnyDesk**\n"
            "[Click here and install.](https://anydesk.com/en/downloads)\n\n"
            "**Step 2: Run AnyDesk**\n"
            "Open the .exe file, sync date & time if errors occur.\n\n"
            "**Step 3: Provide Your ID**\n"
            "Copy your AnyDesk ID into your Discord ticket.\n\n"
            "**Step 4: Grant Full Permissions**\n"
            "Wait for staff to connect, then grant full access."
        ),
        color=0x2F3136
    )
    embed.set_footer(text="Virex Team")
    await ctx.send(embed=embed)

# ============================================================
#  SLASH — MODERATION & COMMUNITY
# ============================================================
@bot.tree.command(name="post", description="Submit a video for approval")
@app_commands.describe(link="Video link to submit")
async def post(interaction: discord.Interaction, link: str):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message(f"❌ You need the **{STAFF_ROLE_NAME}** role to use this command.", ephemeral=True)
        return
    approve_channel = bot.get_channel(APPROVE_CHANNEL_ID)
    if not approve_channel:
        await interaction.response.send_message("❌ Approval channel not found.", ephemeral=True)
        return
    embed = discord.Embed(title="📬 New Post Request", description=f"**User:** {interaction.user.mention}\n**Link:** {link}", color=0xffcc00)
    embed.set_footer(text=f"Submitted by {interaction.user}")
    await approve_channel.send(embed=embed, view=ApproveView(link, interaction.user))
    await interaction.response.send_message("✅ Your post has been submitted for approval.", ephemeral=True)


@bot.tree.command(name="changelog", description="Post a game update to the changelog channel")
@app_commands.describe(game="Name of the game that was updated", update="Description of what changed")
async def changelog(interaction: discord.Interaction, game: str, update: str):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message(f"❌ You need the **{STAFF_ROLE_NAME}** role to use this command.", ephemeral=True)
        return
    changelog_channel = bot.get_channel(CHANGELOG_CHANNEL_ID)
    if not changelog_channel:
        await interaction.response.send_message("❌ Changelog channel not found.", ephemeral=True)
        return
    customer_role = discord.utils.find(lambda r: r.name.lower() == CUSTOMER_ROLE_NAME.lower(), interaction.guild.roles)
    embed = discord.Embed(title=f"🔄 {game} — Update", description=update, color=0x6f2cff)
    embed.set_footer(text=f"Posted by {interaction.user} • Virex Team")
    ping_content = customer_role.mention if customer_role else f"@{CUSTOMER_ROLE_NAME}"
    await changelog_channel.send(content=ping_content, embed=embed)
    await interaction.response.send_message(f"✅ Changelog for **{game}** has been posted!", ephemeral=True)


@bot.tree.command(name="leaderboard", description=f"Show the {STAFF_ROLE_NAME} activity leaderboard ({STAFF_ROLE_NAME} only)")
async def leaderboard(interaction: discord.Interaction):
    if not has_staff_role(interaction.user):
        await interaction.response.send_message(
            f"❌ You need the **{STAFF_ROLE_NAME}** role to use this command.", ephemeral=True)
        return
    if not db_pool:
        await interaction.response.send_message("❌ Database not available right now.", ephemeral=True)
        return

    await interaction.response.defer()
    rows = await db_get_leaderboard(interaction.guild.id, limit=10)

    embed = discord.Embed(
        title=f"🏆 {STAFF_ROLE_NAME} — Leaderboard",
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    set_logo(embed)

    if not rows:
        embed.description = "No activity has been tracked yet."
    else:
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, row in enumerate(rows):
            member = interaction.guild.get_member(row["user_id"])
            name   = member.mention if member else f"<@{row['user_id']}>"
            rank   = medals[i] if i < len(medals) else f"`#{i + 1}`"
            lines.append(f"{rank} {name} — **{row['points']}** pts ({row['message_count']} messages)")
        embed.description = "\n".join(lines)

    embed.set_footer(text=f"{POINTS_PER_MESSAGE} point(s) per message • Virex Team")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="guide", description="Shows the Vega R6 setup guide")
async def guide(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Vega R6 — Setup Guide",
        description=f"**[🔗 Click here to open the full guide]({R6_GUIDE_URL})**",
        color=0x0A84FF
    )
    embed.set_footer(text="Virex Team • virex.gg")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="status", description="Show the current product status")
async def status(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_status_embed())


@bot.tree.command(name="setstatus", description="Manually set a product's status (Staff only)")
@app_commands.describe(product="Product name (e.g. CRUSADER, ONYX FN)", new_status="New status to set")
@app_commands.choices(new_status=[
    app_commands.Choice(name="🟢 Undetected", value="Undetected"),
    app_commands.Choice(name="🟢 Online",     value="Online"),
    app_commands.Choice(name="🔵 Updating",   value="Updating"),
    app_commands.Choice(name="🟡 Testing",    value="Testing"),
    app_commands.Choice(name="🔴 Detected",   value="Detected"),
    app_commands.Choice(name="⚫ Offline",    value="Offline"),
])
async def setstatus(interaction: discord.Interaction, product: str, new_status: str):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message(f"❌ You need the **{STAFF_ROLE_NAME}** role to change product status.", ephemeral=True)
        return
    matched = next((k for k in product_status if k.lower() == product.lower()), None)
    if not matched:
        product_list = "\n".join(f"• {p}" for p in product_status.keys())
        await interaction.response.send_message(f"❌ Product **{product}** not found.\n\n**Available products:**\n{product_list}", ephemeral=True)
        return
    old_status = product_status[matched]
    product_status[matched] = new_status
    embed = discord.Embed(
        title="✅ Status Updated",
        description=(
            f"**Product:** {matched}\n"
            f"**Old Status:** {STATUS_DOTS.get(old_status, '⚫')} {old_status}\n"
            f"**New Status:** {STATUS_DOTS.get(new_status, '⚫')} {new_status}"
        ),
        color=STATUS_COLORS.get(new_status, 0x888888)
    )
    embed.set_footer(text=f"Updated by {interaction.user} • Virex Team")
    await interaction.response.send_message(embed=embed)

# ─── WHITELIST SLASH COMMANDS ─────────────────────────────────────────────────
@bot.tree.command(name="whitelist", description="Whitelist a user — they can write any word without the filter blocking them (Staff only)")
@app_commands.describe(member="The user to whitelist")
async def cmd_whitelist(interaction: discord.Interaction, member: discord.Member):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message(f"❌ You need the **{STAFF_ROLE_NAME}** role to use this command.", ephemeral=True)
        return
    if member.id in whitelist_cache:
        embed = discord.Embed(
            title="⚠️ Already Whitelisted",
            description=f"{member.mention} is already on the whitelist.",
            color=0xF39C12
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    success = await db_add_whitelist(member.id, interaction.user.id, interaction.guild.id)
    if success:
        embed = discord.Embed(
            title="✅ User Whitelisted",
            description=f"{member.mention} can now write any word without the word filter blocking them.",
            color=0x57F287
        )
        embed.add_field(name="👤 User",       value=f"{member} (`{member.id}`)", inline=True)
        embed.add_field(name="🛡️ Added By",   value=f"{interaction.user}",       inline=True)
        embed.add_field(name="⏰ Timestamp",  value=utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Virex — Whitelist")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Database error. Failed to whitelist user.", ephemeral=True)


@bot.tree.command(name="unwhitelist", description="Remove a user from the whitelist (Staff only)")
@app_commands.describe(member="The user to remove from the whitelist")
async def cmd_unwhitelist(interaction: discord.Interaction, member: discord.Member):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message(f"❌ You need the **{STAFF_ROLE_NAME}** role to use this command.", ephemeral=True)
        return
    if member.id not in whitelist_cache:
        embed = discord.Embed(
            title="⚠️ Not Whitelisted",
            description=f"{member.mention} is not on the whitelist.",
            color=0xF39C12
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    success = await db_remove_whitelist(member.id)
    if success:
        embed = discord.Embed(
            title="🚫 Whitelist Removed",
            description=f"{member.mention} is no longer whitelisted. The word filter applies to them again.",
            color=0xE74C3C
        )
        embed.add_field(name="👤 User",       value=f"{member} (`{member.id}`)", inline=True)
        embed.add_field(name="🛡️ Removed By", value=f"{interaction.user}",       inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Virex — Whitelist")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Database error. Failed to remove user from whitelist.", ephemeral=True)


@bot.tree.command(name="whitelistview", description="Show all whitelisted users (Staff only)")
async def cmd_whitelistview(interaction: discord.Interaction):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message(f"❌ You need the **{STAFF_ROLE_NAME}** role to use this command.", ephemeral=True)
        return
    records = await db_get_whitelist(interaction.guild.id)
    if not records:
        embed = discord.Embed(
            title="📋 Whitelist",
            description="No users are currently whitelisted.",
            color=0x57F287
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    lines = []
    for record in records:
        try:
            user = await bot.fetch_user(record['user_id'])
            user_display = f"{user.mention}"
        except Exception:
            user_display = "Unknown"
        try:
            staff = await bot.fetch_user(record['whitelisted_by'])
            staff_display = str(staff)
        except Exception:
            staff_display = "Unknown"
        ts = record['whitelisted_at'].strftime("%d.%m.%Y %H:%M")
        lines.append(f"• {user_display} (`{record['user_id']}`) — added by **{staff_display}** on {ts}")
    embed = discord.Embed(
        title=f"📋 Whitelist — {len(records)} user(s)",
        description="\n".join(lines),
        color=0x57F287
    )
    embed.set_footer(text="These users bypass the word filter • Virex Team")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ─── VOUCH COMMAND ────────────────────────────────────────────────────────────
@bot.tree.command(name="vouch", description="Leave a vouch for Virex (customers only)")
@app_commands.describe(stars="Your rating (1–5 stars)", message="Your vouch message")
@app_commands.choices(stars=[
    app_commands.Choice(name="⭐ 1 Star",          value=1),
    app_commands.Choice(name="⭐⭐ 2 Stars",        value=2),
    app_commands.Choice(name="⭐⭐⭐ 3 Stars",      value=3),
    app_commands.Choice(name="⭐⭐⭐⭐ 4 Stars",    value=4),
    app_commands.Choice(name="⭐⭐⭐⭐⭐ 5 Stars",  value=5),
])
async def vouch(interaction: discord.Interaction, stars: int, message: str):
    global vouch_counter
    if not has_customer_role(interaction.user):
        await interaction.response.send_message("❌ You need the **customer** role to leave a vouch.\nPurchase a product first to receive this role.", ephemeral=True)
        return
    vouch_channel = bot.get_channel(VOUCH_CHANNEL_ID)
    if not vouch_channel:
        await interaction.response.send_message("❌ Vouch channel not found. Contact an admin.", ephemeral=True)
        return
    star_display = "⭐" * stars
    now = utcnow()
    vouch_num = vouch_counter
    vouch_counter += 1
    embed = discord.Embed(title="New vouch created!", color=0x57F287)
    embed.add_field(name="Stars",       value=star_display,   inline=False)
    embed.add_field(name="Vouch:",      value=message,        inline=False)
    embed.add_field(name="Vouch N°:",   value=str(vouch_num), inline=True)
    embed.add_field(name="Vouched at:", value=now.strftime("%A, %B %d, %Y %I:%M %p"), inline=True)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text=f"Vouched by {interaction.user} • Virex Team")
    await vouch_channel.send(content=f"Vouched by: {interaction.user.mention}", embed=embed)
    await interaction.response.send_message("✅ Your vouch has been submitted, thank you!", ephemeral=True)

# ─── GIVEAWAY SLASH COMMANDS ──────────────────────────────────────────────────
@bot.tree.command(name="giveaway", description="Start a giveaway")
@app_commands.describe(duration="Duration e.g. 10m, 2h, 1d", winners="Number of winners", prize="What is being given away?", requirements="Optional requirements to enter")
async def giveaway_start(interaction: discord.Interaction, duration: str, winners: int, prize: str, requirements: str = None):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ You need the staff role to start a giveaway.", ephemeral=True)
        return
    seconds = parse_duration(duration)
    if not seconds:
        await interaction.response.send_message("❌ Invalid duration. Examples: `10s`, `5m`, `2h`, `1d`", ephemeral=True)
        return
    if winners < 1:
        await interaction.response.send_message("❌ At least 1 winner required.", ephemeral=True)
        return
    ends_at = utcnow() + timedelta(seconds=seconds)
    embed = build_giveaway_embed(prize, winners, interaction.user.id, ends_at, 0, requirements)
    await interaction.response.send_message("✅ Starting giveaway...", ephemeral=True)
    msg = await interaction.channel.send(content="@everyone", embed=embed)
    active_giveaways[msg.id] = {
        "channel_id": interaction.channel.id,
        "prize": prize,
        "winners": winners,
        "host_id": interaction.user.id,
        "ends_at": ends_at,
        "entries": set(),
        "requirements": requirements
    }
    view = GiveawayView(msg.id)
    await msg.edit(view=view)
    asyncio.create_task(_giveaway_timer(msg.id, seconds))


async def _giveaway_timer(message_id: int, seconds: int):
    await asyncio.sleep(seconds)
    await end_giveaway(message_id)


@bot.tree.command(name="gend", description="End a giveaway immediately (by message ID)")
@app_commands.describe(message_id="The message ID of the giveaway embed")
async def giveaway_end(interaction: discord.Interaction, message_id: str):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ You need the staff role.", ephemeral=True)
        return
    try:
        mid = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return
    if mid not in active_giveaways:
        await interaction.response.send_message("❌ No active giveaway found with that ID.", ephemeral=True)
        return
    await interaction.response.send_message("✅ Ending giveaway...", ephemeral=True)
    await end_giveaway(mid)


@bot.tree.command(name="greroll", description="Reroll a winner from a giveaway embed")
@app_commands.describe(channel="The channel where the giveaway was held", message_id="The message ID of the giveaway embed")
async def giveaway_reroll(interaction: discord.Interaction, channel: discord.TextChannel, message_id: str):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ You need the staff role.", ephemeral=True)
        return
    try:
        mid = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return
    if mid not in active_giveaways:
        await interaction.response.send_message("❌ Giveaway not found in memory.", ephemeral=True)
        return
    entries = list(active_giveaways[mid]["entries"])
    prize   = active_giveaways[mid]["prize"]
    if not entries:
        await interaction.response.send_message("❌ No entries to reroll from.", ephemeral=True)
        return
    new_winner = random.choice(entries)
    try:
        await channel.fetch_message(mid)
    except discord.NotFound:
        await interaction.response.send_message("❌ Message not found in that channel.", ephemeral=True)
        return
    await channel.send(f"🔁 Reroll! The new winner of **{prize}** is <@{new_winner}>! Congratulations!")
    await interaction.response.send_message(f"✅ Rerolled! New winner: <@{new_winner}>", ephemeral=True)

# ============================================================
#  SLASH — TICKETS
# ============================================================
@bot.tree.command(name="panel", description="Send the Virex ticket panel (Admin only)")
@app_commands.guild_only()
async def cmd_panel(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="🎫 Virex Support Tickets",
        description=("**Need help? Open a ticket below!**\n\n"
                     "🛒 **Purchase** — Help with buying a product\n"
                     "💰 **Reseller** — Apply to our reseller program\n"
                     "🔑 **Claim Key** — Claim your role or product key\n"
                     "🔒 **HWID Reset** — Reset your hardware ID\n"
                     "🎫 **Support** — General support\n\n"
                     f"🌐 **Shop:** [{VIREX_WEBSITE}]({VIREX_WEBSITE})\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n*Select a category from the dropdown below.*"),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    set_logo(embed)
    embed.set_footer(text="Virex • Premium Products 💎")
    if TICKET_PANEL_BANNER.startswith("https://"):
        embed.set_image(url=TICKET_PANEL_BANNER)
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.followup.send("✅ Panel sent!", ephemeral=True)


@bot.tree.command(name="store", description="Send the Virex store panel (Admin only)")
@app_commands.guild_only()
async def cmd_store(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="💎 VIREX",
        description=("**Welcome to Virex — Premium Products & Services**\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                     f"🌐 **Website (Instant Delivery):**\n[**{VIREX_WEBSITE}**]({VIREX_WEBSITE})\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                     "💳 **Payment Methods**\n\n**🖥️ Website**\n"
                     "├ 💳 Credit / Debit Card\n├  Apple Pay\n├ 🔷 iDEAL\n└ 🪙 Cryptocurrency\n\n"
                     "**🎫 Ticket Orders**\n"
                     "├ 💵 Cash App\n├ 🅿️ PayPal F&F\n├ 🎟️ Crypto Voucher\n└ 🟡 Binance Giftcards\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n*Questions? Open a support ticket!*"),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    set_logo(embed)
    embed.set_footer(text="Virex • Premium Products 💎")
    await interaction.channel.send(embed=embed, view=StoreView())
    await interaction.followup.send("✅ Store panel sent!", ephemeral=True)


@bot.tree.command(name="close", description="Close the current ticket (Staff only)")
@app_commands.guild_only()
async def cmd_close(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    info = await db_get_ticket(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)
        return
    await interaction.response.send_message("🔒 Closing in 5 seconds...")
    await asyncio.sleep(5)
    await close_ticket(interaction.channel, interaction.guild, closed_by=interaction.user)


@bot.tree.command(name="add", description="Add a user to the current ticket (Staff only)")
@app_commands.describe(user="User to add")
@app_commands.guild_only()
async def cmd_add(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    info = await db_get_ticket(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True)
        return
    await interaction.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
    await interaction.response.send_message(
        embed=discord.Embed(description=f"✅ {user.mention} added.", color=VIREX_COLOR_SUCCESS))


@bot.tree.command(name="remove", description="Remove a user from the current ticket (Staff only)")
@app_commands.describe(user="User to remove")
@app_commands.guild_only()
async def cmd_remove(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    info = await db_get_ticket(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True)
        return
    await interaction.channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(
        embed=discord.Embed(description=f"✅ {user.mention} removed.", color=VIREX_COLOR_DANGER))


@bot.tree.command(name="rename", description="Rename the current ticket (Staff only)")
@app_commands.describe(name="New name for this ticket, e.g. 'john' -> ticket-john")
@app_commands.guild_only()
async def cmd_rename(interaction: discord.Interaction, name: str):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    info = await db_get_ticket(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True)
        return

    base_name = sanitize_channel_name(name)
    new_name  = f"ticket-{base_name}"
    existing  = {c.name for c in interaction.guild.text_channels if c.id != interaction.channel.id}
    if new_name in existing:
        suffix = 2
        while f"{new_name}-{suffix}" in existing:
            suffix += 1
        new_name = f"{new_name}-{suffix}"

    old_name = interaction.channel.name
    try:
        await interaction.channel.edit(name=new_name, reason=f"Renamed by {interaction.user}")
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ Could not rename channel: {e}", ephemeral=True)
        return

    await interaction.response.send_message(embed=discord.Embed(
        description=f"✏️ Ticket renamed from `{old_name}` to `{new_name}` by {interaction.user.mention}.",
        color=VIREX_COLOR))


@bot.tree.command(name="autoclose", description="Enable or disable auto-close for this ticket (Staff only)")
@app_commands.describe(enabled="True = on  |  False = off")
@app_commands.guild_only()
async def cmd_autoclose(interaction: discord.Interaction, enabled: bool):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    info = await db_get_ticket(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True)
        return
    await db_update_ticket(str(interaction.channel.id), auto_close=enabled)
    status_txt = "✅ enabled" if enabled else "❌ disabled"
    await interaction.response.send_message(
        embed=discord.Embed(description=f"Auto-close is now **{status_txt}** for this ticket.", color=VIREX_COLOR))

# ============================================================
#  SLASH — SMEDIA
# ============================================================
@bot.tree.command(name="smedia", description="Send a Looking for Media Creators announcement (Admin only)")
@app_commands.describe(
    channel="Channel to send to (defaults to current channel)",
    ping_everyone="Ping @everyone with the announcement (default: True)"
)
@app_commands.guild_only()
async def cmd_smedia(
    interaction: discord.Interaction,
    channel: discord.TextChannel = None,
    ping_everyone: bool = True,
):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    target = channel or interaction.channel
    await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(
        title="🎬 LOOKING FOR MEDIA CREATORS!",
        description=(
            "We are looking for **high quality applicants** who can promote our products consistently!\n"
            "Ensure you meet the requirements before applying!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 **Universal Requirements**\n"
            "├ 🎥 Record in at least **1080p60fps**\n"
            "├ 🎮 Be mechanically **good** at the game you're making media for\n"
            "├ 💻 Be experienced in using **cheating software**\n"
            "├ 📡 Interest in **LIVE streaming** is highly preferred\n"
            "└ 👁️ Higher LIVE viewers = **higher weekly payouts**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎫 **If you want to apply, open a ticket below!**"
        ),
        color=VIREX_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    set_logo(embed)
    embed.set_footer(text="Virex • Media Creator Program 🎬")

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(
        label="Apply — Open a Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="virex_media_ticket"
    ))

    content = "@everyone" if ping_everyone else None
    try:
        await target.send(content=content, embed=embed, view=view)
        await interaction.followup.send(
            f"✅ Media Creator announcement sent to {target.mention}!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to send: {e}", ephemeral=True)

# ============================================================
#  SLASH — VERIFY
# ============================================================
@bot.tree.command(name="verifypanel", description="Send the verification panel (Admin only)")
@app_commands.guild_only()
async def cmd_verifypanel(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    redirect_uri     = f"{WEB_BASE_URL}/callback"
    encoded_redirect = urllib.parse.quote(redirect_uri, safe="")
    oauth_url = (
        "https://discord.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={encoded_redirect}"
        "&response_type=code"
        "&scope=identify%20guilds.join"
    )
    embed = discord.Embed(
        title="🔐 Virex Verification",
        description=("**Verify your Discord account to gain full access.**\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                     "🔒 **Why verify?**\n"
                     "Keeps our server safe from bots and raiders.\n\n"
                     "✅ **What happens?**\n"
                     "You receive the **Verified** role and unlock all channels.\n\n"
                     "🌐 **How?**\n"
                     "Click the button — log in with Discord on our secure page.\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n"
                     "*We do not store your password or personal data.*"),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    set_logo(embed)
    embed.set_footer(text="Virex • Secure Verification 🔐")
    await interaction.channel.send(embed=embed, view=VerifyView(oauth_url))
    await interaction.followup.send("✅ Verify panel sent!", ephemeral=True)

# ============================================================
#  SLASH — BACKUP / RESTORE
# ============================================================
@bot.tree.command(name="backup_restore", description="Restore a single user back to this server (Admin only)")
@app_commands.describe(user_id="Discord User ID of the person to restore")
@app_commands.guild_only()
async def cmd_backup_restore(interaction: discord.Interaction, user_id: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    if not user_id.strip().isdigit():
        await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    result = await add_member_to_guild(int(user_id), interaction.guild.id)
    colors = {"added": VIREX_COLOR_SUCCESS, "already": VIREX_COLOR,
              "no_token": VIREX_COLOR_DANGER, "token_expired": VIREX_COLOR_WARN, "error": VIREX_COLOR_DANGER}
    icons  = {"added": "✅", "already": "ℹ️", "no_token": "❌", "token_expired": "⚠️", "error": "❌"}
    embed  = discord.Embed(
        title=f"{icons.get(result['status'], '❓')} Backup Restore",
        description=f"**User:** <@{user_id}>\n**Result:** {result['detail']}",
        color=colors.get(result["status"], VIREX_COLOR_SUBTLE),
        timestamp=datetime.now(timezone.utc)
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="backup_restore_all", description="Restore ALL verified users back to this server (Admin only)")
@app_commands.guild_only()
async def cmd_backup_restore_all(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    all_v = await db_all_verified()
    if not all_v:
        await interaction.response.send_message("📭 No verified users in backup.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    added, already, failed, expired = [], [], [], []
    total = len(all_v)
    for uid, info in all_v.items():
        result = await add_member_to_guild(int(uid), interaction.guild.id)
        name   = info.get("username", uid)
        if result["status"] == "added":
            added.append(name)
        elif result["status"] == "already":
            already.append(name)
        elif result["status"] == "token_expired":
            expired.append(name)
        else:
            failed.append(f"{name} — {result['detail']}")
        await asyncio.sleep(0.5)

    def fmt_list(lst, limit=20):
        if not lst:
            return "—"
        shown = lst[:limit]
        extra = len(lst) - limit
        text  = ", ".join(f"`{x}`" for x in shown)
        if extra > 0:
            text += f" *+{extra} more*"
        return text

    embed = discord.Embed(
        title="📦 Backup Restore — Complete",
        description=(f"**Total in backup:** {total}\n\n"
                     f"✅ **Added ({len(added)}):** {fmt_list(added)}\n\n"
                     f"ℹ️ **Already in server ({len(already)}):** {fmt_list(already)}\n\n"
                     f"⚠️ **Token expired ({len(expired)}):** {fmt_list(expired)}\n\n"
                     f"❌ **Failed ({len(failed)}):** {fmt_list(failed)}"),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Restore completed • {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC")
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="backup_list", description="Show all users in the backup (Admin only)")
@app_commands.guild_only()
async def cmd_backup_list(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    all_v = await db_all_verified()
    if not all_v:
        await interaction.response.send_message("📭 Backup is empty.", ephemeral=True)
        return
    lines = []
    for uid, info in all_v.items():
        name        = info.get("username", "unknown")
        date        = str(info.get("verified_at", ""))[:10]
        refreshed   = str(info.get("token_refreshed_at") or "")[:10]
        refresh_str = f" 🔄 refreshed {refreshed}" if refreshed else ""
        expired     = " ⚠️ token expired" if info.get("token_expired") else ""
        left        = " 📤 left server"    if info.get("left_at")       else ""
        lines.append(f"• `{name}` (<@{uid}>) — {date}{refresh_str}{expired}{left}")
    chunks, chunk, length = [], [], 0
    for line in lines:
        if length + len(line) > 3800:
            chunks.append(chunk)
            chunk, length = [line], len(line)
        else:
            chunk.append(line)
            length += len(line)
    if chunk:
        chunks.append(chunk)
    for i, ch in enumerate(chunks):
        embed = discord.Embed(
            title=f"📦 Backup List {'(cont.)' if i > 0 else ''}",
            description="\n".join(ch), color=VIREX_COLOR
        )
        if i == 0:
            embed.set_footer(text=f"Total: {len(all_v)} users in backup")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="backup_stats", description="Show backup statistics (Admin only)")
@app_commands.guild_only()
async def cmd_backup_stats(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    all_v     = await db_all_verified()
    total     = len(all_v)
    expired   = sum(1 for v in all_v.values() if v.get("token_expired"))
    left      = sum(1 for v in all_v.values() if v.get("left_at"))
    refreshed = sum(1 for v in all_v.values() if v.get("token_refreshed_at"))
    active    = total - expired
    embed = discord.Embed(
        title="📊 Backup Statistics",
        description=(f"👥 **Total in backup:** `{total}`\n"
                     f"✅ **Active tokens:** `{active}`\n"
                     f"🔄 **Auto-refreshed tokens:** `{refreshed}`\n"
                     f"⚠️ **Expired tokens:** `{expired}` *(users need to re-verify)*\n"
                     f"📤 **Left server:** `{left}`\n\n"
                     f"💡 *Token refresh runs every 6h — backup tokens stay alive forever.*\n"
                     f"💡 *Use `/backup_restore_all` to restore everyone to this server.*"),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Virex • Member Backup System")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="token_refresh_now", description="Force refresh all backup tokens now (Admin only)")
@app_commands.guild_only()
async def cmd_token_refresh_now(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    all_v = await db_all_verified()
    total = len(all_v)
    refreshed = failed = skipped = 0
    for uid, info in all_v.items():
        if not info.get("refresh_token"):
            skipped += 1
            continue
        success = await refresh_token(uid)
        if success:
            refreshed += 1
        else:
            failed += 1
        await asyncio.sleep(0.3)
    embed = discord.Embed(
        title="🔄 Token Refresh Complete",
        description=(f"**Total users:** `{total}`\n"
                     f"✅ **Refreshed:** `{refreshed}`\n"
                     f"❌ **Failed:** `{failed}` *(user needs to re-verify)*\n"
                     f"⏭️ **Skipped:** `{skipped}` *(no refresh token stored)*"),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Virex • Token Management")
    await interaction.followup.send(embed=embed, ephemeral=True)

# ============================================================
#  MIGRATE — import existing JSON data into PostgreSQL
# ============================================================
@bot.tree.command(name="migrate_json", description="Import existing JSON files into PostgreSQL (Admin only, run once)")
@app_commands.guild_only()
async def cmd_migrate_json(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)

    v_count = t_count = 0

    # verified.json
    v_data = load_json(VERIFIED_FILE)
    for uid, info in v_data.items():
        await db_set_verified(uid, info)
        v_count += 1

    # tickets.json
    t_data = load_json(TICKETS_FILE)
    for cid, info in t_data.items():
        await db_set_ticket(cid, info)
        t_count += 1

    embed = discord.Embed(
        title="✅ JSON → PostgreSQL Migration Complete",
        description=(f"👥 **Verified users imported:** `{v_count}`\n"
                     f"🎫 **Tickets imported:** `{t_count}`"),
        color=VIREX_COLOR_SUCCESS, timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Virex • Database Migration")
    await interaction.followup.send(embed=embed, ephemeral=True)

# ============================================================
#  START
# ============================================================
async def main():
    if not TOKEN:
        print("❌ DISCORD_TOKEN environment variable not found.")
        return
    db_initialized = await init_db()
    if not db_initialized:
        print("⚠️ Warning: Database not initialized. Some features may not work.")
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
    
