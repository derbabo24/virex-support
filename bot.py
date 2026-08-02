# ============================================================
#  XENIX BOT — COMBINED (Moderation + Tickets/Verify/Backup + KeyAuth)
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
OWNER_IDS = [int(x) for x in os.environ.get("OWNER_ID", "").replace(" ", "").split(",") if x.isdigit()]
BAN_REQUEST_CHANNEL_ID = int(os.environ.get("BAN_REQUEST_CHANNEL_ID", 0))
ADMIN_ROLE_NAME = os.environ.get("ADMIN_ROLE_NAME", "Blacklist")
STAFF_ROLE_NAME = "Trial Staff (not trusted)"
BLACKLIST_ADMIN_ROLE = "Blacklist"
POINTS_PER_MESSAGE = int(os.environ.get("POINTS_PER_MESSAGE", 1) or 1)
APPROVE_CHANNEL_ID = 1532469937929453820
POST_CHANNEL_ID = 1532468677566398616
CHANGELOG_CHANNEL_ID = 1532469302563704914
CUSTOMER_ROLE_NAME = "customer"
MESSAGE_LOG_CHANNEL_ID = 1532470227386765375
VOUCH_CHANNEL_ID = 1532470227386765375
R6_GUIDE_URL = "https://xenixguide.com/"
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
XENIX_LOGO               = os.getenv("XENIX_LOGO", "").strip()
XENIX_WEBSITE            = os.getenv("XENIX_WEBSITE", "https://xenix.gg/")
# Unified color palette based on XENIX logo (all-purple)
XENIX_COLOR              = 0x8B2FFF   # Vivid violet — primary accent
XENIX_COLOR_SUCCESS      = 0xD0A2FF   # Light lavender for success
XENIX_COLOR_DANGER       = 0x5B0FA8   # Deep purple for errors/leave
XENIX_COLOR_WARN         = 0xB35CFF   # Orchid for warnings/on-hold
XENIX_COLOR_SUBTLE       = 0x2B1B4F   # Dark purple for neutral embeds
# OAuth2 / Verify
CLIENT_ID                = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET            = os.getenv("DISCORD_CLIENT_SECRET", "")
WEB_BASE_URL             = os.getenv("WEB_BASE_URL", "http://localhost:5000")
VERIFIED_ROLE_ID         = int(os.getenv("VERIFIED_ROLE_ID", 0))
# Welcome / Leave channel
WELCOME_CHANNEL_ID       = int(os.getenv("WELCOME_CHANNEL_ID", 0))
DATABASE_URL             = os.environ.get("DATABASE_URL", "")
# ============================================================
#  CONFIG — KEYAUTH SELLER API
# ============================================================
KEYAUTH_SELLER_KEY     = os.getenv("KEYAUTH_SELLER_KEY", "").strip()
KEYAUTH_DEFAULT_MASK   = os.getenv("KEYAUTH_DEFAULT_MASK", "XenixLT-******-******-******").strip()
KEYAUTH_DEFAULT_LEVEL  = int(os.getenv("KEYAUTH_DEFAULT_LEVEL", 1))
KEYAUTH_INSTRUCTION_URL= os.getenv("KEYAUTH_INSTRUCTION_URL", "https://xenixguide.com/").strip()
KEYAUTH_API_BASE       = "https://keyauth.win/api/seller/"
TICKET_CATEGORIES = {
    "purchase": {"label": "Purchase",               "description": "Request help with a purchase.",      "emoji": "🛒", "color": XENIX_COLOR,         "category_env": "TICKET_CAT_PURCHASE"},
    "reseller": {"label": "Apply to be a Reseller", "description": "Apply to Xenix's Reseller Program.", "emoji": "💰", "color": 0xB35CFF,            "category_env": "TICKET_CAT_RESELLER"},
    "claim":    {"label": "Claim Role / Key",       "description": "Claim your role or product key.",    "emoji": "🔑", "color": XENIX_COLOR_SUCCESS, "category_env": "TICKET_CAT_CLAIM"},
    "hwid":     {"label": "HWID Reset",             "description": "Request a reset for your key.",       "emoji": "🔒", "color": 0xB35CFF,            "category_env": "TICKET_CAT_HWID"},
    "support":  {"label": "Get Support",            "description": "Request support from our staff.",     "emoji": "🎫", "color": XENIX_COLOR,         "category_env": "TICKET_CAT_SUPPORT"},
}
TICKET_PANEL_BANNER = os.getenv("TICKET_PANEL_BANNER", "").strip()
TICKET_OPEN_BANNER  = os.getenv("TICKET_OPEN_BANNER", "").strip()
SUGGESTION_CHANNEL_ID = int(os.getenv("SUGGESTION_CHANNEL_ID", 0))
SUGGESTION_BANNER     = os.getenv("SUGGESTION_BANNER", "").strip()
SELLAUTH_API_KEY   = os.getenv("SELLAUTH_API_KEY", "").strip()
SELLAUTH_SHOP_ID   = os.getenv("SELLAUTH_SHOP_ID", "").strip()
SELLAUTH_API_BASE  = os.getenv("SELLAUTH_API_BASE", "https://api.sellauth.com/v1").rstrip("/")
CLAIM_ROLE_NAME    = os.getenv("CLAIM_ROLE_NAME", CUSTOMER_ROLE_NAME)
CLAIM_LOG_CHANNEL_ID = int(os.getenv("CLAIM_LOG_CHANNEL_ID", 0))
CLAIM_DM_TIMEOUT   = int(os.getenv("CLAIM_DM_TIMEOUT", 300))
CLAIM_VALID_STATUSES = {"completed"}
claim_in_progress: set[int] = set()
# ─── PRODUCT STATUS ───────────────────────────────────────────────────────────
product_status: dict[str, str] = {
    "Vega R6":           "Updating",
    "ONYX FN":           "Undetected",
    "Temp Spoofer":      "Undetected",
    "Perm SPOOFER":      "Undetected",
    "Valorant Full":     "Undetected",
    "Fn Accounts":       "Online",
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
    "Undetected": 0xD0A2FF,
    "Online":     0xD0A2FF,
    "Updating":   0x8B2FFF,
    "Testing":    0xB35CFF,
    "Detected":   0x5B0FA8,
    "Offline":    0x2B1B4F,
}
BLACKLISTED_WORDS = [
    "spoof", "spoofed", "spoofer", "spoofing",
    "cheat", "cheats", "cheating", "cheater",
    "hack", "hacked", "hacking", "hacker",
    "aimbot", "wallhack", "esp", "triggerbot",
    "bypass", "injector", "inject",
]
TICKETS_FILE      = "/app/data/tickets.json"
VERIFIED_FILE     = "/app/data/verified.json"
vouch_counter: int = 1
active_giveaways: dict = {}
db_pool: asyncpg.Pool = None
whitelist_cache: set[int] = set()
silent_perm_cache: set[int] = set()
# ============================================================
#  BOT SETUP
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
#  FLASK SERVER
# ============================================================
app = Flask(__name__)
@app.route('/guide')
def serve_guide():
    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    return "Xenix Guide"
def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False)
# ============================================================
#  KEYAUTH API HELPER FUNCTIONS
# ============================================================
async def keyauth_request(params: dict) -> dict:
    """Helper to query KeyAuth Seller API."""
    if not KEYAUTH_SELLER_KEY:
        return {"success": False, "message": "KEYAUTH_SELLER_KEY variable is missing in environment settings!"}
    request_params = {
        "sellerkey": KEYAUTH_SELLER_KEY,
        **params
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(KEYAUTH_API_BASE, params=request_params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    try:
                        return await resp.json(content_type=None)
                    except Exception:
                        text = await resp.text()
                        return {"success": False, "message": f"Non-JSON response from KeyAuth: {text[:200]}"}
                else:
                    text = await resp.text()
                    return {"success": False, "message": f"KeyAuth API HTTP {resp.status}: {text[:200]}"}
    except Exception as e:
        return {"success": False, "message": f"KeyAuth Connection Error: {e}"}
async def keyauth_generate_key(expiry_days: int = 99999, level: int = None, mask: str = None) -> dict:
    """Generate a KeyAuth key (expiry 99999 = Lifetime / Perm)."""
    lvl = level if level is not None else KEYAUTH_DEFAULT_LEVEL
    msk = mask if mask else KEYAUTH_DEFAULT_MASK
    params = {
        "type": "add",
        "expiry": expiry_days,
        "mask": msk,
        "level": lvl,
        "amount": 1
    }
    res = await keyauth_request(params)
    if res.get("success"):
        key = res.get("key") or (res.get("keys")[0] if isinstance(res.get("keys"), list) and res.get("keys") else None)
        if key:
            return {"success": True, "key": key, "message": res.get("message")}
    return {"success": False, "message": res.get("message", "Failed to generate key.")}
async def keyauth_get_info(key: str) -> dict:
    """Fetch Key information."""
    params = {"type": "info", "key": key}
    return await keyauth_request(params)
async def keyauth_ban_key(key: str, reason: str = "Banned via Bot") -> dict:
    """Ban a Key."""
    params = {"type": "ban", "key": key, "reason": reason}
    return await keyauth_request(params)
async def keyauth_unban_key(key: str) -> dict:
    """Unban a Key."""
    params = {"type": "unban", "key": key}
    return await keyauth_request(params)
async def keyauth_del_key(key: str) -> dict:
    """Delete a Key."""
    params = {"type": "del", "key": key}
    return await keyauth_request(params)
def build_key_dm_embed(key: str, product: str = "Perm Spoofer", duration: str = "Lifetime", instruction: str = None) -> discord.Embed:
    """Builds DM embed in Xenix colors matching Aqua style screenshot."""
    instr_url = instruction or KEYAUTH_INSTRUCTION_URL
    embed = discord.Embed(
        title="Xenix | Key Generation",
        description=(
            f"● Key Generation Request Successful.\n"
            f"● Your License for `{product}` is:\n\n"
            f"```{key}```\n\n"
            f"● **Duration:** {duration}\n"
            f"● **Product:** {product}\n"
            f"● **Instruction:** {instr_url}"
        ),
        color=XENIX_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    if XENIX_LOGO and XENIX_LOGO.startswith("https://"):
        embed.set_thumbnail(url=XENIX_LOGO)
        embed.set_footer(text="Auth - Xenix", icon_url=XENIX_LOGO)
    else:
        embed.set_footer(text="Auth - Xenix")
    return embed
# ============================================================
#  DATABASE INIT
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
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS silent_perms (
                    user_id BIGINT PRIMARY KEY,
                    granted_by BIGINT NOT NULL,
                    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    guild_id BIGINT NOT NULL
                )
            ''')
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
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS claimed_orders (
                    order_key   TEXT PRIMARY KEY,
                    invoice_id  TEXT,
                    email       TEXT,
                    claimed_by  BIGINT,
                    guild_id    BIGINT,
                    claimed_at  TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS staff_points (
                    user_id       BIGINT PRIMARY KEY,
                    guild_id      BIGINT NOT NULL DEFAULT 0,
                    points        BIGINT NOT NULL DEFAULT 0,
                    message_count BIGINT NOT NULL DEFAULT 0,
                    updated_at    TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            await conn.execute('ALTER TABLE staff_points ADD COLUMN IF NOT EXISTS guild_id BIGINT NOT NULL DEFAULT 0')
            await conn.execute('ALTER TABLE staff_points ADD COLUMN IF NOT EXISTS points BIGINT NOT NULL DEFAULT 0')
            await conn.execute('ALTER TABLE staff_points ADD COLUMN IF NOT EXISTS message_count BIGINT NOT NULL DEFAULT 0')
            await conn.execute("ALTER TABLE staff_points ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()")
        print("✅ Database ready")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
# ── Blacklist DB helpers ──────────────────────────────────────────────────────
async def add_to_blacklist(user_id: int, reason: str, staff_id: int, guild_id: int) -> bool:
    if not db_pool: return False
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
    if not db_pool: return False
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM blacklist WHERE user_id = $1', user_id)
        return True
    except Exception as e:
        print(f"❌ Error removing from blacklist: {e}")
        return False
async def is_blacklisted(user_id: int) -> bool:
    if not db_pool: return False
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchval('SELECT user_id FROM blacklist WHERE user_id = $1', user_id)
        return result is not None
    except Exception as e:
        print(f"❌ Error checking blacklist: {e}")
        return False
async def get_blacklist(guild_id: int) -> list:
    if not db_pool: return []
    try:
        async with db_pool.acquire() as conn:
            return await conn.fetch('SELECT user_id, reason, blacklisted_by, blacklisted_at FROM blacklist WHERE guild_id = $1 ORDER BY blacklisted_at DESC', guild_id)
    except Exception as e:
        print(f"❌ Error fetching blacklist: {e}")
        return []
async def get_blacklist_entry(user_id: int) -> dict:
    if not db_pool: return None
    try:
        async with db_pool.acquire() as conn:
            record = await conn.fetchrow('SELECT user_id, reason, blacklisted_by, blacklisted_at FROM blacklist WHERE user_id = $1', user_id)
        return dict(record) if record else None
    except Exception as e:
        print(f"❌ Error fetching blacklist entry: {e}")
        return None
# ── Whitelist DB helpers ──────────────────────────────────────────────────────
async def db_add_whitelist(user_id: int, staff_id: int, guild_id: int) -> bool:
    if not db_pool: return False
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('INSERT INTO whitelist (user_id, whitelisted_by, guild_id) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING', user_id, staff_id, guild_id)
        whitelist_cache.add(user_id)
        return True
    except Exception as e:
        print(f"❌ Error adding to whitelist: {e}")
        return False
async def db_remove_whitelist(user_id: int) -> bool:
    if not db_pool: return False
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM whitelist WHERE user_id = $1', user_id)
        whitelist_cache.discard(user_id)
        return True
    except Exception as e:
        print(f"❌ Error removing from whitelist: {e}")
        return False
async def db_load_whitelist() -> set[int]:
    if not db_pool: return set()
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT user_id FROM whitelist')
        return {r['user_id'] for r in rows}
    except Exception as e:
        print(f"❌ Error loading whitelist: {e}")
        return set()
async def db_get_whitelist(guild_id: int) -> list:
    if not db_pool: return []
    try:
        async with db_pool.acquire() as conn:
            return await conn.fetch('SELECT user_id, whitelisted_by, whitelisted_at FROM whitelist WHERE guild_id = $1 ORDER BY whitelisted_at DESC', guild_id)
    except Exception as e:
        print(f"❌ Error fetching whitelist: {e}")
        return []
# ── Silent-prefix permission DB helpers ───────────────────────────────────────
async def db_add_silent_perm(user_id: int, granted_by: int, guild_id: int) -> bool:
    if not db_pool: return False
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('INSERT INTO silent_perms (user_id, granted_by, guild_id) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING', user_id, granted_by, guild_id)
        silent_perm_cache.add(user_id)
        return True
    except Exception as e:
        print(f"❌ Error adding silent perm: {e}")
        return False
async def db_remove_silent_perm(user_id: int) -> bool:
    if not db_pool: return False
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM silent_perms WHERE user_id = $1', user_id)
        silent_perm_cache.discard(user_id)
        return True
    except Exception as e:
        print(f"❌ Error removing silent perm: {e}")
        return False
async def db_load_silent_perms() -> set[int]:
    if not db_pool: return set()
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT user_id FROM silent_perms')
        return {r['user_id'] for r in rows}
    except Exception as e:
        print(f"❌ Error loading silent perms: {e}")
        return set()
async def db_get_silent_perms(guild_id: int) -> list:
    if not db_pool: return []
    try:
        async with db_pool.acquire() as conn:
            return await conn.fetch('SELECT user_id, granted_by, granted_at FROM silent_perms WHERE guild_id = $1 ORDER BY granted_at DESC', guild_id)
    except Exception as e:
        print(f"❌ Error fetching silent perms: {e}")
        return []
# ── Claimed-orders DB helpers ─────────────────────────────────────────────────
async def db_get_claim(order_key: str) -> dict | None:
    if not db_pool: return None
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow('SELECT order_key, invoice_id, email, claimed_by, guild_id, claimed_at FROM claimed_orders WHERE order_key = $1', str(order_key))
        return dict(row) if row else None
    except Exception as e:
        print(f"❌ Error fetching claim: {e}")
        return None
async def db_mark_order_claimed(order_key: str, invoice_id: str, email: str, claimed_by: int, guild_id: int) -> bool:
    if not db_pool: return False
    try:
        async with db_pool.acquire() as conn:
            result = await conn.execute('''
                INSERT INTO claimed_orders (order_key, invoice_id, email, claimed_by, guild_id)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (order_key) DO NOTHING
            ''', str(order_key), str(invoice_id), (email or "").lower(), claimed_by, guild_id)
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
    if not value: return None
    if hasattr(value, "isoformat"): return value
    try: return datetime.fromisoformat(str(value))
    except Exception: return None
def load_json(path):
    if os.path.exists(path):
        with open(path) as f: return json.load(f)
    return {}
def set_logo(embed: discord.Embed):
    if XENIX_LOGO and XENIX_LOGO.startswith("https://"):
        embed.set_thumbnail(url=XENIX_LOGO)
def get_ticket_category_channel(guild: discord.Guild, cat_key: str):
    info = TICKET_CATEGORIES.get(cat_key, {})
    env_name = info.get("category_env")
    specific = os.getenv(env_name, "").strip() if env_name else ""
    chosen = specific if specific.isdigit() else str(TICKET_CATEGORY_ID or "")
    if not chosen.isdigit(): return None
    ch = guild.get_channel(int(chosen))
    return ch if isinstance(ch, discord.CategoryChannel) else None
def sanitize_channel_name(name: str) -> str:
    name = name.strip().lower()
    replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
    for src, dst in replacements.items(): name = name.replace(src, dst)
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return (name or "user")[:80]
def make_unique_ticket_channel_name(guild: discord.Guild, base_name: str) -> str:
    existing = {c.name for c in guild.text_channels}
    channel_name = f"ticket-{base_name}"
    if channel_name not in existing: return channel_name
    suffix = 2
    while f"{channel_name}-{suffix}" in existing: suffix += 1
    return f"{channel_name}-{suffix}"
# ============================================================
#  VERIFIED USERS — DB HELPERS
# ============================================================
async def db_get_verified(user_id: str) -> dict | None:
    if not db_pool: return None
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM verified_users WHERE user_id = $1", user_id)
    if not row: return None
    d = dict(row)
    extra = d.pop("extra", {}) or {}
    if isinstance(extra, str):
        try: extra = json.loads(extra)
        except Exception: extra = {}
    if isinstance(extra, dict): d.update(extra)
    for k in ("verified_at", "token_refreshed_at", "left_at"):
        if d.get(k) and hasattr(d[k], "isoformat"): d[k] = d[k].isoformat()
    return d
async def db_set_verified(user_id: str, data: dict):
    if not db_pool: return
    known = {"username", "access_token", "refresh_token", "verified_at", "token_refreshed_at", "token_expired", "last_left_guild", "left_at"}
    base  = {k: v for k, v in data.items() if k in known}
    extra = {k: v for k, v in data.items() if k not in known and k != "user_id"}
    for k in ("verified_at", "token_refreshed_at", "left_at"):
        if isinstance(base.get(k), str):
            try: base[k] = datetime.fromisoformat(base[k])
            except Exception: base[k] = None
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO verified_users (user_id, username, access_token, refresh_token, verified_at, token_refreshed_at, token_expired, last_left_guild, left_at, extra)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            ON CONFLICT (user_id) DO UPDATE SET username=EXCLUDED.username, access_token=EXCLUDED.access_token, refresh_token=EXCLUDED.refresh_token, verified_at=COALESCE(EXCLUDED.verified_at, verified_users.verified_at), token_refreshed_at=EXCLUDED.token_refreshed_at, token_expired=EXCLUDED.token_expired, last_left_guild=EXCLUDED.last_left_guild, left_at=EXCLUDED.left_at, extra=verified_users.extra || EXCLUDED.extra
        """, user_id, base.get("username"), base.get("access_token"), base.get("refresh_token"), base.get("verified_at"), base.get("token_refreshed_at"), base.get("token_expired", False), base.get("last_left_guild"), base.get("left_at"), json.dumps(extra))
async def db_update_verified_field(user_id: str, **kwargs):
    existing = await db_get_verified(user_id) or {"user_id": user_id}
    existing.update(kwargs)
    await db_set_verified(user_id, existing)
async def db_all_verified() -> dict:
    if not db_pool: return {}
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM verified_users")
    result = {}
    for row in rows:
        d = dict(row)
        uid = d.pop("user_id")
        extra = d.pop("extra", {}) or {}
        if isinstance(extra, str):
            try: extra = json.loads(extra)
            except Exception: extra = {}
        if isinstance(extra, dict): d.update(extra)
        for k in ("verified_at", "token_refreshed_at", "left_at"):
            if d.get(k) and hasattr(d[k], "isoformat"): d[k] = d[k].isoformat()
        result[uid] = d
    return result
# ============================================================
#  TICKETS — DB HELPERS
# ============================================================
async def db_get_ticket(channel_id: str) -> dict | None:
    if not db_pool: return None
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM tickets WHERE channel_id = $1", channel_id)
    if not row: return None
    d = dict(row)
    for k in ("created_at", "last_activity"):
        if d.get(k) and hasattr(d[k], "isoformat"): d[k] = d[k].isoformat()
    return d
async def db_set_ticket(channel_id: str, data: dict):
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO tickets (channel_id, user_id, category, created_at, last_activity, auto_close, status)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (channel_id) DO UPDATE SET user_id=EXCLUDED.user_id, category=EXCLUDED.category, created_at=COALESCE(EXCLUDED.created_at, tickets.created_at), last_activity=EXCLUDED.last_activity, auto_close=EXCLUDED.auto_close, status=EXCLUDED.status
        """, channel_id, int(data.get("user_id", 0)), data.get("category"), _parse_ts(data.get("created_at")), _parse_ts(data.get("last_activity")), data.get("auto_close", True), data.get("status", "open"))
async def db_update_ticket(channel_id: str, **kwargs):
    existing = await db_get_ticket(channel_id)
    if existing:
        existing.update(kwargs)
        await db_set_ticket(channel_id, existing)
async def db_all_tickets() -> dict:
    if not db_pool: return {}
    async with db_pool.acquire() as conn: rows = await conn.fetch("SELECT * FROM tickets")
    result = {}
    for row in rows:
        d = dict(row)
        cid = d.pop("channel_id")
        for k in ("created_at", "last_activity"):
            if d.get(k) and hasattr(d[k], "isoformat"): d[k] = d[k].isoformat()
        result[cid] = d
    return result
async def db_add_staff_points(user_id: int, guild_id: int, points: int) -> None:
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO staff_points (user_id, guild_id, points, message_count, updated_at)
            VALUES ($1, $2, $3, 1, NOW())
            ON CONFLICT (user_id) DO UPDATE SET points=staff_points.points+EXCLUDED.points, message_count=staff_points.message_count+1, guild_id=EXCLUDED.guild_id, updated_at=NOW()
        """, user_id, guild_id, points)
async def db_get_leaderboard(guild_id: int, limit: int = 10) -> list:
    if not db_pool: return []
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, points, message_count FROM staff_points WHERE guild_id = $1 ORDER BY points DESC LIMIT $2", guild_id, limit)
    return [dict(r) for r in rows]
def has_staff_role(user: discord.Member) -> bool:
    return STAFF_ROLE_NAME.lower() in [r.name.lower() for r in getattr(user, "roles", [])]
def has_blacklist_admin_role(user: discord.Member) -> bool:
    return BLACKLIST_ADMIN_ROLE.lower() in [r.name.lower() for r in getattr(user, "roles", [])]
def has_admin_role(user: discord.Member) -> bool:
    return ADMIN_ROLE_NAME.lower() in [r.name.lower() for r in getattr(user, "roles", [])]
def has_customer_role(user: discord.Member) -> bool:
    return CUSTOMER_ROLE_NAME.lower() in [r.name.lower() for r in getattr(user, "roles", [])]
def is_staff(member: discord.Member) -> bool:
    if not isinstance(member, discord.Member): return False
    if member.guild_permissions.administrator: return True
    return any(r.id in STAFF_ROLE_IDS + ADMIN_ROLE_IDS for r in member.roles)
def is_admin(member: discord.Member) -> bool:
    if not isinstance(member, discord.Member): return False
    if member.guild_permissions.administrator: return True
    return any(r.id in ADMIN_ROLE_IDS for r in member.roles)
def is_any_staff(member) -> bool:
    if not isinstance(member, discord.Member): return False
    return has_staff_role(member) or is_staff(member)
def is_bot_owner(user) -> bool:
    return getattr(user, "id", None) in OWNER_IDS
def parse_duration(duration_str: str) -> int | None:
    match = re.fullmatch(r"(\d+)([smhd])", duration_str.strip().lower())
    if not match: return None
    value, unit = int(match.group(1)), match.group(2)
    return value * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
def build_giveaway_embed(prize, winners, host_id, ends_at, entries, requirements=None) -> discord.Embed:
    description = f"Click **🎉 Enter** to participate!\n\n🏆 **Winners:** {winners}\n👥 **Entries:** {entries}\n🕐 **Ends:** <t:{int(ends_at.timestamp())}:R>\n👑 **Hosted by:** <@{host_id}>"
    if requirements: description += f"\n\n📋 **Requirements to enter:**\n{requirements}"
    embed = discord.Embed(title=f"🎉 GIVEAWAY — {prize}", description=description, color=0xB35CFF)
    embed.set_footer(text=f"Ends on {ends_at.strftime('%d.%m.%Y at %H:%M')} UTC")
    return embed
def build_status_embed() -> discord.Embed:
    embed = discord.Embed(title="📊 Current Product Status", color=0x8B2FFF, timestamp=utcnow())
    items = list(product_status.items())
    col_size = (len(items) + 2) // 3
    for col_idx in range(3):
        chunk = items[col_idx * col_size:(col_idx + 1) * col_size]
        if not chunk: continue
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
        if re.search(rf"\b{re.escape(word)}", cleaned): return word
    return None
async def log_deleted_message(message: discord.Message, matched_word: str):
    log_channel = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
    if not log_channel: return
    embed = discord.Embed(title="🚫 Message Deleted — Word Filter", color=0x5B0FA8, timestamp=utcnow())
    embed.add_field(name="👤 User", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
    embed.add_field(name="📍 Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="🔍 Matched Word", value=f"`{matched_word}`", inline=True)
    embed.add_field(name="💬 Message Content", value=f"```{message.content[:1000]}```" if message.content else "*empty*", inline=False)
    embed.set_thumbnail(url=message.author.display_avatar.url)
    embed.set_footer(text=f"User ID: {message.author.id}")
    await log_channel.send(embed=embed)
async def staff_check(ctx) -> bool:
    if not is_any_staff(ctx.author):
        embed = discord.Embed(title="❌ No Permission", description=f"You need at least the **{STAFF_ROLE_NAME}** role to use this command.", color=0x5B0FA8)
        await ctx.send(embed=embed, delete_after=5)
        try: await ctx.message.delete()
        except Exception: pass
        return False
    return True
async def blacklist_admin_check(ctx) -> bool:
    if not has_blacklist_admin_role(ctx.author):
        embed = discord.Embed(title="❌ No Permission", description=f"You need the **{BLACKLIST_ADMIN_ROLE}** role to use this command.", color=0x5B0FA8)
        await ctx.send(embed=embed, delete_after=5)
        try: await ctx.message.delete()
        except Exception: pass
        return False
    return True
async def end_giveaway(message_id: int):
    if message_id not in active_giveaways: return
    data = active_giveaways.pop(message_id)
    channel = bot.get_channel(data["channel_id"])
    if not channel: return
    try: msg = await channel.fetch_message(message_id)
    except discord.NotFound: return
    entries = list(data["entries"])
    prize = data["prize"]
    winner_count = min(data["winners"], len(entries))
    embed = discord.Embed(title=f"🎉 GIVEAWAY ENDED — {prize}", color=0x2B1B4F)
    if not entries:
        embed.description = "❌ Nobody entered. No winner was drawn."
        await msg.edit(embed=embed, view=None)
        await channel.send("❌ The giveaway ended with no participants.")
        return
    winners = random.sample(entries, winner_count)
    winner_mentions = " ".join(f"<@{w}>" for w in winners)
    embed.description = f"**Prize:** {prize}\n**Winner(s):** {winner_mentions}\n👑 **Hosted by:** <@{data['host_id']}>"
    embed.set_footer(text="Giveaway ended")
    await msg.edit(embed=embed, view=None)
    await channel.send(f"🎉 Congratulations {winner_mentions}! You won **{prize}**!")
async def refresh_token(uid: str) -> bool:
    info = await db_get_verified(uid)
    if not info or not info.get("refresh_token"): return False
    data = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "refresh_token", "refresh_token": info["refresh_token"]}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://discord.com/api/v10/oauth2/token", data=data, headers=headers) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    await db_update_verified_field(uid, access_token=token_data["access_token"], refresh_token=token_data["refresh_token"], token_refreshed_at=datetime.now(timezone.utc).isoformat(), token_expired=False)
                    return True
                else:
                    await db_update_verified_field(uid, token_expired=True)
                    return False
    except Exception: return False
async def add_member_to_guild(user_id: int, guild_id: int, role_ids: list[int] = None) -> dict:
    uid  = str(user_id)
    info = await db_get_verified(uid)
    if not info or not info.get("access_token"): return {"status": "no_token", "detail": "User has not verified yet."}
    access_token = info.get("access_token")
    payload = {"access_token": access_token}
    if role_ids: payload["roles"] = role_ids
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    url     = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"
    async with aiohttp.ClientSession() as session:
        async with session.put(url, json=payload, headers=headers) as resp:
            if resp.status in (200, 201): return {"status": "added", "detail": "Successfully added to server."}
            elif resp.status == 204: return {"status": "already", "detail": "Already in server."}
            elif resp.status == 401:
                refreshed = await refresh_token(uid)
                if refreshed:
                    new_info = await db_get_verified(uid) or {}
                    payload["access_token"] = new_info.get("access_token", "")
                    async with session.put(url, json=payload, headers=headers) as retry_resp:
                        if retry_resp.status in (200, 201): return {"status": "added", "detail": "Added after token refresh."}
                        elif retry_resp.status == 204: return {"status": "already", "detail": "Already in server."}
                await db_update_verified_field(uid, token_expired=True)
                return {"status": "token_expired", "detail": "Access token has expired."}
            else:
                text = await resp.text()
                return {"status": "error", "detail": f"API error {resp.status}: {text}"}
def generate_transcript(channel, messages, guild):
    cat_key = ""
    if channel.topic and " | " in channel.topic:
        parts = channel.topic.split(" | ")
        if len(parts) > 1: cat_key = parts[1].strip()
    cat = TICKET_CATEGORIES.get(cat_key, {"label": "Support", "emoji": "🎫"})
    msgs_html = ""
    prev_id   = None
    for msg in messages:
        av  = str(msg.author.display_avatar.url) if msg.author.display_avatar else ""
        stf = any(r.id in STAFF_ROLE_IDS + ADMIN_ROLE_IDS for r in getattr(msg.author, "roles", []))
        bdg = '<span class="badge owner">Owner</span>' if msg.author.id == guild.owner_id else ('<span class="badge staff">Staff</span>' if stf else ('<span class="badge bot">BOT</span>' if msg.author.bot else ""))
        txt = msg.content or ""
        txt = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', txt)
        txt = re.sub(r'`(.+?)`', r'<code>\1</code>', txt)
        ts      = msg.created_at.strftime("%d/%m/%Y %H:%M")
        same    = prev_id == msg.author.id
        prev_id = msg.author.id
        av_html  = f'<img src="{av}" class="av" alt="av">' if not same else '<div class="avs"></div>'
        hdr_html = f'<div class="mh"><span class="un">{msg.author.display_name}</span>{bdg}<span class="ts">{ts}</span></div>' if not same else ""
        msgs_html += f'<div class="mg{"" if not same else " sa"}">{av_html}<div class="mc">{hdr_html}<div class="mt">{txt}</div></div></div>'
    return f"<html><body>{msgs_html}</body></html>"
async def close_ticket(channel, guild, closed_by=None):
    info = await db_get_ticket(str(channel.id))
    if not info:
        try: await channel.delete()
        except Exception: pass
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
            description=f"**User:** {user_str}\n**Category:** {cat['emoji']} {cat['label']}\n**Opened:** <t:{opened_ts}:F>\n**Closed by:** {closed_str}\n**Messages:** {len(messages)}",
            color=XENIX_COLOR, timestamp=datetime.now(timezone.utc)
        )
        set_logo(embed)
        try:
            await tr_ch.send(embed=embed, file=discord.File(io.BytesIO(html.encode()), filename=f"transcript-{channel.name}.html"))
        except Exception as e: print(f"Transcript error: {e}")
    await db_update_ticket(str(channel.id), status="closed")
    try: await channel.delete()
    except Exception: pass
class TicketQuestionsModal(discord.ui.Modal):
    def __init__(self, cat_key: str):
        cat = TICKET_CATEGORIES[cat_key]
        super().__init__(title=f"Open Ticket — {cat['label']}"[:45])
        self.cat_key = cat_key
        self.reason = discord.ui.TextInput(label="What is the reason for your request?", style=discord.TextStyle.paragraph, required=True, max_length=500)
        self.order_id = discord.ui.TextInput(label="What is your order ID?", required=False, max_length=100)
        self.product = discord.ui.TextInput(label="What product do you need help with?", required=False, max_length=200)
        self.add_item(self.reason)
        self.add_item(self.order_id)
        self.add_item(self.product)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await create_ticket_channel(interaction, cat_key=self.cat_key, reason=self.reason.value.strip(), order_id=self.order_id.value.strip(), product=self.product.value.strip())
async def create_ticket_channel(interaction: discord.Interaction, cat_key: str, reason: str, order_id: str, product: str):
    guild = interaction.guild
    cat   = TICKET_CATEGORIES[cat_key]
    for ch in guild.text_channels:
        if ch.topic and f"uid-{interaction.user.id}" in ch.topic:
            await interaction.followup.send(f"❌ You already have an open ticket: {ch.mention}", ephemeral=True)
            return
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user:   discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
        guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }
    for rid in STAFF_ROLE_IDS + ADMIN_ROLE_IDS:
        role = guild.get_role(rid)
        if role: overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    parent = get_ticket_category_channel(guild, cat_key)
    ticket_num    = len([c for c in guild.text_channels if c.name.startswith("ticket-")]) + 1
    base_name     = sanitize_channel_name(interaction.user.name)
    channel_name  = make_unique_ticket_channel_name(guild, base_name)
    try:
        channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites, category=parent, topic=f"uid-{interaction.user.id} | {cat_key} | open")
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Could not create ticket: {e}", ephemeral=True)
        return
    await db_set_ticket(str(channel.id), {"user_id": interaction.user.id, "category": cat_key, "created_at": datetime.now(timezone.utc).isoformat(), "last_activity": datetime.now(timezone.utc).isoformat(), "auto_close": True, "status": "open"})
    await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)
    embed = discord.Embed(title=f"{cat['emoji']} {cat['label']} — Ticket #{ticket_num:04d}", description="Thank you for creating a ticket.", color=cat["color"], timestamp=datetime.now(timezone.utc))
    set_logo(embed)
    embed.add_field(name="Reason", value=reason or "—", inline=False)
    embed.add_field(name="Order ID", value=order_id or "—", inline=False)
    embed.add_field(name="Product", value=product or "—", inline=False)
    await channel.send(content=interaction.user.mention, embed=embed, view=TicketControlView())
class TicketSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select a category to open a ticket...", min_values=1, max_values=1, custom_id="xenix_ticket_select", options=[discord.SelectOption(label=v["label"], description=v["description"], emoji=v["emoji"], value=k) for k, v in TICKET_CATEGORIES.items()])
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketQuestionsModal(self.values[0]))
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="xenix_close_ticket")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing in 5 seconds...")
        await asyncio.sleep(5)
        await close_ticket(interaction.channel, interaction.guild, closed_by=interaction.user)
    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.success, emoji="✋", custom_id="xenix_claim_ticket")
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Only staff can claim tickets.", ephemeral=True)
            return
        await interaction.response.send_message(embed=discord.Embed(description=f"✋ **{interaction.user.mention}** has claimed this ticket!", color=XENIX_COLOR))
# ============================================================
#  KEYAUTH COMMANDS & SLASHS
# ============================================================
@bot.tree.command(name="onetime", description="Generate a 1-day/custom key and DM it directly to a user")
@app_commands.describe(
    user="The user who will receive the key per DM",
    product="Product name (default: Perm Spoofer)",
    mask="Key mask pattern (optional)"
)
async def cmd_onetime(interaction: discord.Interaction, user: discord.User, product: str = "Perm Spoofer", mask: str = None):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ You need Staff permissions to generate keys.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    gen_result = await keyauth_generate_key(expiry_days=1, mask=mask)
    if not gen_result.get("success"):
        await interaction.followup.send(f"❌ KeyAuth Generation Error: {gen_result.get('message')}", ephemeral=True)
        return
    key = gen_result["key"]
    embed = build_key_dm_embed(key=key, product=product, duration="1 Day")
    try:
        dm_channel = await user.create_dm()
        await dm_channel.send(embed=embed)
        dm_status = f"✅ Key successfully sent via DM to {user.mention}!"
    except discord.Forbidden:
        dm_status = f"⚠️ Key generated, but could not DM {user.mention} (User has DMs closed)."
    except Exception as e:
        dm_status = f"⚠️ Key generated, but failed to send DM: {e}"
    staff_embed = discord.Embed(
        title="🔑 1-Day Key Generated & Sent",
        description=f"{dm_status}\n\n**Generated Key:** `{key}`\n**Recipient:** {user.mention} (`{user.id}`)\n**Product:** {product}\n**Duration:** 1 Day",
        color=XENIX_COLOR_SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    staff_embed.set_footer(text=f"Generated by {interaction.user}")
    await interaction.followup.send(embed=staff_embed, ephemeral=True)
@bot.tree.command(name="lifetime", description="Generate a Lifetime/Perm key and DM it directly to a user")
@app_commands.describe(
    user="The user who will receive the key per DM",
    product="Product name (default: Perm Spoofer)",
    mask="Key mask pattern (optional)"
)
async def cmd_lifetime(interaction: discord.Interaction, user: discord.User, product: str = "Perm Spoofer", mask: str = None):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ You need Staff permissions to generate keys.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    gen_result = await keyauth_generate_key(expiry_days=99999, mask=mask)
    if not gen_result.get("success"):
        await interaction.followup.send(f"❌ KeyAuth Generation Error: {gen_result.get('message')}", ephemeral=True)
        return
    key = gen_result["key"]
    embed = build_key_dm_embed(key=key, product=product, duration="Lifetime")
    try:
        dm_channel = await user.create_dm()
        await dm_channel.send(embed=embed)
        dm_status = f"✅ Key successfully sent via DM to {user.mention}!"
    except discord.Forbidden:
        dm_status = f"⚠️ Key generated, but could not DM {user.mention} (User has DMs closed)."
    except Exception as e:
        dm_status = f"⚠️ Key generated, but failed to send DM: {e}"
    staff_embed = discord.Embed(
        title="🔑 Lifetime Key Generated & Sent",
        description=f"{dm_status}\n\n**Generated Key:** `{key}`\n**Recipient:** {user.mention} (`{user.id}`)\n**Product:** {product}\n**Duration:** Lifetime",
        color=XENIX_COLOR_SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    staff_embed.set_footer(text=f"Generated by {interaction.user}")
    await interaction.followup.send(embed=staff_embed, ephemeral=True)
key_group = app_commands.Group(name="key", description="KeyAuth Key Management Commands (Staff only)")
@key_group.command(name="generate", description="Generate a KeyAuth key")
@app_commands.describe(duration_days="Duration in days (use 99999 for Lifetime/Perm)", product="Product name label", mask="Key mask pattern (optional)")
async def key_cmd_generate(interaction: discord.Interaction, duration_days: int = 99999, product: str = "Perm Spoofer", mask: str = None):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    res = await keyauth_generate_key(expiry_days=duration_days, mask=mask)
    if res.get("success"):
        dur_str = "Lifetime" if duration_days >= 99999 else f"{duration_days} Days"
        embed = discord.Embed(title="🔑 Key Generated Successfully", description=f"**Key:** `{res['key']}`\n**Product:** {product}\n**Duration:** {dur_str}", color=XENIX_COLOR_SUCCESS)
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(f"❌ Key generation failed: {res.get('message')}", ephemeral=True)
@key_group.command(name="info", description="Check key information & status (used/unused, HWID, IP, etc.)")
@app_commands.describe(key="The KeyAuth key to query")
async def key_cmd_info(interaction: discord.Interaction, key: str):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    res = await keyauth_get_info(key)
    if not res.get("success") and "message" in res and "not found" in res.get("message", "").lower():
        await interaction.followup.send(f"❌ Key `{key}` was not found in KeyAuth.", ephemeral=True)
        return
    is_used = res.get("used", False) or res.get("status", "").lower() == "used" or bool(res.get("hwid"))
    used_status_str = "🟢 **USED**" if is_used else "🔵 **UNUSED / NOT REDEEMED**"
    if res.get("banned", False) or res.get("status", "").lower() == "banned":
        used_status_str = "🔴 **BANNED**"
    embed = discord.Embed(title=f"🔍 Key Information — {key}", color=XENIX_COLOR if is_used else XENIX_COLOR_SUCCESS, timestamp=datetime.now(timezone.utc))
    embed.add_field(name="Status", value=used_status_str, inline=False)
    embed.add_field(name="HWID", value=f"`{res.get('hwid') or 'None'}`", inline=False)
    embed.add_field(name="Used By User", value=f"`{res.get('usedby') or res.get('username') or 'N/A'}`", inline=True)
    embed.add_field(name="Expiry Date", value=f"`{res.get('expiry') or 'Lifetime'}`", inline=True)
    embed.add_field(name="Last Login", value=f"`{res.get('lastlogin') or 'Never'}`", inline=True)
    if res.get("banreason"):
        embed.add_field(name="Ban Reason", value=f"`{res.get('banreason')}`", inline=False)
    embed.set_footer(text="KeyAuth System • Xenix")
    await interaction.followup.send(embed=embed, ephemeral=True)
@key_group.command(name="ban", description="Ban a KeyAuth key")
@app_commands.describe(key="The KeyAuth key to ban", reason="Reason for the ban")
async def key_cmd_ban(interaction: discord.Interaction, key: str, reason: str = "Banned via Bot"):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    res = await keyauth_ban_key(key, reason)
    if res.get("success"):
        embed = discord.Embed(title="🔨 Key Banned", description=f"Key `{key}` has been **banned**.\n**Reason:** {reason}", color=XENIX_COLOR_DANGER)
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(f"❌ Failed to ban key: {res.get('message')}", ephemeral=True)
@key_group.command(name="unban", description="Unban a KeyAuth key")
@app_commands.describe(key="The KeyAuth key to unban")
async def key_cmd_unban(interaction: discord.Interaction, key: str):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    res = await keyauth_unban_key(key)
    if res.get("success"):
        embed = discord.Embed(title="✅ Key Unbanned", description=f"Key `{key}` has been **unbanned**.", color=XENIX_COLOR_SUCCESS)
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(f"❌ Failed to unban key: {res.get('message')}", ephemeral=True)
@key_group.command(name="delete", description="Delete a KeyAuth key permanently")
@app_commands.describe(key="The KeyAuth key to delete")
async def key_cmd_delete(interaction: discord.Interaction, key: str):
    if not is_any_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    res = await keyauth_del_key(key)
    if res.get("success"):
        embed = discord.Embed(title="🗑️ Key Deleted", description=f"Key `{key}` has been permanently deleted from KeyAuth.", color=XENIX_COLOR_DANGER)
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(f"❌ Failed to delete key: {res.get('message')}", ephemeral=True)
bot.tree.add_command(key_group)
# ── Prefix Commands for KeyAuth ($keyinfo, $keyban) ──────────────────────────
@bot.command(name="keyinfo")
async def prefix_keyinfo(ctx, key: str = None):
    if not await staff_check(ctx): return
    if not key:
        await ctx.send("❌ Usage: `$keyinfo <key>`", delete_after=5)
        return
    res = await keyauth_get_info(key)
    if not res.get("success") and "not found" in res.get("message", "").lower():
        await ctx.send(f"❌ Key `{key}` not found.", delete_after=5)
        return
    is_used = res.get("used", False) or res.get("status", "").lower() == "used" or bool(res.get("hwid"))
    used_status_str = "🟢 USED" if is_used else "🔵 UNUSED"
    embed = discord.Embed(title=f"🔍 Key Info — {key}", color=XENIX_COLOR)
    embed.add_field(name="Status", value=used_status_str, inline=True)
    embed.add_field(name="HWID", value=f"`{res.get('hwid') or 'None'}`", inline=False)
    embed.add_field(name="Expiry", value=f"`{res.get('expiry') or 'Lifetime'}`", inline=True)
    await ctx.send(embed=embed)
@bot.command(name="keyban")
async def prefix_keyban(ctx, key: str = None, *, reason: str = "Banned via Bot"):
    if not await staff_check(ctx): return
    if not key:
        await ctx.send("❌ Usage: `$keyban <key> [reason]`", delete_after=5)
        return
    res = await keyauth_ban_key(key, reason)
    if res.get("success"):
        await ctx.send(f"✅ Key `{key}` banned.")
    else:
        await ctx.send(f"❌ Failed: {res.get('message')}")
# ============================================================
#  TASKS & LOOPS
# ============================================================
@tasks.loop(minutes=30)
async def auto_close_task():
    now      = datetime.now(timezone.utc)
    all_t    = await db_all_tickets()
    to_close = []
    for cid, info in all_t.items():
        if info.get("status") != "open": continue
        if not info.get("auto_close", True): continue
        if not info.get("last_activity"): continue
        last = datetime.fromisoformat(info["last_activity"])
        if last.tzinfo is None: last = last.replace(tzinfo=timezone.utc)
        if now - last >= timedelta(hours=AUTO_CLOSE_HOURS): to_close.append(cid)
    for cid in to_close:
        guild = bot.get_guild(GUILD_ID)
        if not guild: continue
        channel = guild.get_channel(int(cid))
        if channel:
            try:
                await channel.send("⏰ Auto-closing due to inactivity...")
                await close_ticket(channel, guild)
            except Exception as e: print(f"Auto-close error: {e}")
@tasks.loop(hours=6)
async def token_refresh_loop():
    now       = datetime.now(timezone.utc)
    all_v     = await db_all_verified()
    for uid, info in all_v.items():
        if not info.get("refresh_token") or info.get("token_expired"): continue
        last_refresh_str = info.get("token_refreshed_at") or info.get("verified_at")
        if not last_refresh_str: continue
        try:
            last_refresh = datetime.fromisoformat(last_refresh_str)
            if last_refresh.tzinfo is None: last_refresh = last_refresh.replace(tzinfo=timezone.utc)
        except Exception: continue
        if now - last_refresh >= timedelta(days=6):
            await refresh_token(uid)
            await asyncio.sleep(0.5)
# ============================================================
#  EVENTS
# ============================================================
@bot.event
async def on_ready():
    global whitelist_cache, silent_perm_cache
    print(f"✅ Xenix Bot online — {bot.user}")
    await bot.change_presence(activity=discord.Game(name="xenix.gg | $commands"))
    whitelist_cache = await db_load_whitelist()
    silent_perm_cache = await db_load_silent_perms()
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    if not auto_close_task.is_running(): auto_close_task.start()
    if not token_refresh_loop.is_running(): token_refresh_loop.start()
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s) globally")
    except Exception as e: print(f"❌ Global sync error: {e}")
    if GUILD_ID:
        try:
            guild_obj = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            guild_synced = await bot.tree.sync(guild=guild_obj)
            print(f"✅ Synced {len(guild_synced)} slash command(s) to guild {GUILD_ID}")
        except Exception as e: print(f"❌ Guild sync error: {e}")
    if not hasattr(bot, 'flask_started'):
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        bot.flask_started = True
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: return
    if message.guild is None:
        await bot.process_commands(message)
        return
    if message.content.startswith(SILENT_PREFIX):
        if message.author.id not in silent_perm_cache: return
        content = message.content[len(SILENT_PREFIX):].strip()
        try: await message.delete()
        except Exception: pass
        if content: await message.channel.send(content)
        return
    staff_member   = is_any_staff(message.author)
    is_whitelisted = message.author.id in whitelist_cache
    if not staff_member and not is_whitelisted:
        matched = check_blacklist(message.content)
        if matched:
            try: await message.delete()
            except Exception: pass
            await log_deleted_message(message, matched)
            return
    if db_pool and has_staff_role(message.author):
        try: await db_add_staff_points(message.author.id, message.guild.id, POINTS_PER_MESSAGE)
        except Exception: pass
    await bot.process_commands(message)
# ============================================================
#  MAIN ENTRY
# ============================================================
async def main():
    if not TOKEN:
        print("❌ DISCORD_TOKEN environment variable not found.")
        return
    await init_db()
    async with bot:
        await bot.start(TOKEN)
if __name__ == "__main__":
    asyncio.run(main())
