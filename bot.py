# ===========================================================
#  VIREX BOT — bot.py
#  Token refresh keeps backup tokens alive forever (no 7-day expiry)
#  Join/Leave welcome channel added
#  /smedia command added
#  poll_applications race condition fixed
#  PostgreSQL backend for verified_data, tickets_data, applications_data
#
#  FIX (this version): every interaction callback that does slow work
#  (creating channels, DB writes, sending DMs, editing messages) now
#  calls interaction.response.defer(...) FIRST, then uses
#  interaction.followup.send(...) for all further replies. This
#  guarantees Discord always gets an ack within its 3-second window,
#  which prevents the "Diese Interaktion ist fehlgeschlagen" error
#  that can happen when Discord's API / your DB is briefly slow.
# ============================================================

import audioop  # noqa: F401 — audioop-lts shim for Python 3.13
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import asyncio
import re
import io
import aiohttp
import asyncpg
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

# ============================================================
#  CONFIG
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

# Staff Applications
APPLICATION_CHANNEL_ID   = int(os.getenv("APPLICATION_CHANNEL_ID", 0))
APPLICATION_LOG_CHANNEL  = int(os.getenv("APPLICATION_LOG_CHANNEL", 0))

# Welcome / Leave channel
WELCOME_CHANNEL_ID       = int(os.getenv("WELCOME_CHANNEL_ID", 0))

# PostgreSQL
DATABASE_URL             = os.getenv("DATABASE_URL", "")

TICKET_CATEGORIES = {
    "purchase": {"label": "Purchase",               "description": "Request help with a purchase.",       "emoji": "🛒", "color": VIREX_COLOR},
    "reseller": {"label": "Apply to be a Reseller", "description": "Apply to Virex's Reseller Program.",  "emoji": "💰", "color": 0xF0A500},
    "claim":    {"label": "Claim Role / Key",        "description": "Claim your role or product key.",     "emoji": "🔑", "color": VIREX_COLOR_SUCCESS},
    "hwid":     {"label": "HWID Reset",              "description": "Request a reset for your key.",       "emoji": "🔒", "color": 0xE07B39},
    "support":  {"label": "Get Support",             "description": "Request support from our staff.",     "emoji": "🎫", "color": VIREX_COLOR},
}

# ============================================================
#  LOGO HELPER
# ============================================================
def set_logo(embed: discord.Embed):
    if VIREX_LOGO and VIREX_LOGO.startswith("https://"):
        embed.set_thumbnail(url=VIREX_LOGO)

# ============================================================
#  DATABASE POOL (global)
# ============================================================
db_pool: asyncpg.Pool = None

async def init_db():
    """Create tables if they don't exist."""
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    async with db_pool.acquire() as conn:
        await conn.execute("""
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
            );

            CREATE TABLE IF NOT EXISTS tickets (
                channel_id      TEXT PRIMARY KEY,
                user_id         BIGINT,
                category        TEXT,
                created_at      TIMESTAMPTZ,
                last_activity   TIMESTAMPTZ,
                auto_close      BOOLEAN DEFAULT TRUE,
                status          TEXT DEFAULT 'open'
            );

            CREATE TABLE IF NOT EXISTS applications (
                app_id          TEXT PRIMARY KEY,
                discord_id      TEXT,
                discord_username TEXT,
                submitted_at    TIMESTAMPTZ,
                status          TEXT DEFAULT 'pending',
                message_id      BIGINT,
                channel_id      BIGINT,
                interview_channel BIGINT,
                reviewed_by     BIGINT,
                reviewed_at     TIMESTAMPTZ,
                deny_reason     TEXT,
                data            JSONB DEFAULT '{}'::jsonb
            );
        """)
    print("✅ PostgreSQL tables ready")

# ============================================================
#  VERIFIED USERS — DB HELPERS
# ============================================================
async def db_get_verified(user_id: str) -> dict | None:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM verified_users WHERE user_id = $1", user_id)
    if not row:
        return None
    d = dict(row)
    extra = d.pop("extra", {}) or {}
    # Merge extra fields back in
    if not isinstance(extra, dict):
        print(f"⚠️  db_get_verified: non-dict extra for user {d.get('user_id')!r}, skipping merge (got {type(extra).__name__!r})")
        extra = {}
    d.update(extra)
    # Convert timestamps to ISO strings for compatibility
    for k in ("verified_at", "token_refreshed_at", "left_at"):
        if d.get(k) and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d

async def db_set_verified(user_id: str, data: dict):
    """Upsert a verified user. Known columns are stored directly; anything else goes into extra JSONB."""
    known = {"username", "access_token", "refresh_token", "verified_at",
             "token_refreshed_at", "token_expired", "last_left_guild", "left_at"}
    base  = {k: v for k, v in data.items() if k in known}
    extra = {k: v for k, v in data.items() if k not in known and k != "user_id"}

    # Normalise timestamps
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
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM verified_users")
    result = {}
    for row in rows:
        d = dict(row)
        uid = d.pop("user_id")
        extra = d.pop("extra", {}) or {}
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
#  APPLICATIONS — DB HELPERS
# ============================================================
async def db_get_application(app_id: str) -> dict | None:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM applications WHERE app_id = $1", app_id)
    if not row:
        return None
    d = dict(row)
    extra = d.pop("data", {}) or {}
    if not isinstance(extra, dict):
        print(f"⚠️  db_get_application: non-dict data for app {d.get('app_id')!r}, skipping merge (got {type(extra).__name__!r})")
        extra = {}
    d.update(extra)
    for k in ("submitted_at", "reviewed_at"):
        if d.get(k) and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d

async def db_set_application(app_id: str, data: dict):
    known = {"discord_id", "discord_username", "submitted_at", "status",
             "message_id", "channel_id", "interview_channel",
             "reviewed_by", "reviewed_at", "deny_reason"}
    base  = {k: v for k, v in data.items() if k in known}
    extra = {k: v for k, v in data.items() if k not in known and k != "app_id"}

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO applications
                (app_id, discord_id, discord_username, submitted_at, status,
                 message_id, channel_id, interview_channel,
                 reviewed_by, reviewed_at, deny_reason, data)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            ON CONFLICT (app_id) DO UPDATE SET
                discord_id        = EXCLUDED.discord_id,
                discord_username  = EXCLUDED.discord_username,
                submitted_at      = COALESCE(EXCLUDED.submitted_at, applications.submitted_at),
                status            = EXCLUDED.status,
                message_id        = EXCLUDED.message_id,
                channel_id        = EXCLUDED.channel_id,
                interview_channel = EXCLUDED.interview_channel,
                reviewed_by       = EXCLUDED.reviewed_by,
                reviewed_at       = EXCLUDED.reviewed_at,
                deny_reason       = EXCLUDED.deny_reason,
                data              = applications.data || EXCLUDED.data
        """,
            app_id,
            str(base.get("discord_id", "")),
            base.get("discord_username"),
            _parse_ts(base.get("submitted_at")),
            base.get("status", "pending"),
            _to_int(base.get("message_id")),
            _to_int(base.get("channel_id")),
            _to_int(base.get("interview_channel")),
            _to_int(base.get("reviewed_by")),
            _parse_ts(base.get("reviewed_at")),
            base.get("deny_reason"),
            json.dumps(extra),
        )

async def db_update_application(app_id: str, **kwargs):
    existing = await db_get_application(app_id) or {"app_id": app_id}
    existing.update(kwargs)
    await db_set_application(app_id, existing)

async def db_all_applications() -> dict:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM applications")
    result = {}
    for row in rows:
        d = dict(row)
        aid = d.pop("app_id")
        extra = d.pop("data", {}) or {}
        if not isinstance(extra, dict):
            print(f"⚠️  db_all_applications: non-dict data for app {aid!r}, skipping merge (got {type(extra).__name__!r})")
            extra = {}
        d.update(extra)
        for k in ("submitted_at", "reviewed_at"):
            if d.get(k) and hasattr(d[k], "isoformat"):
                d[k] = d[k].isoformat()
        result[aid] = d
    return result

# ============================================================
#  UTILITY
# ============================================================
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

# ============================================================
#  LEGACY JSON HELPERS (kept for migrate script / fallback)
# ============================================================
TICKETS_FILE      = "/app/data/tickets.json"
VERIFIED_FILE     = "/app/data/verified.json"
APPLICATIONS_FILE = "/app/data/applications.json"

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

# ============================================================
#  PERMISSION HELPERS
# ============================================================
def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.id in STAFF_ROLE_IDS + ADMIN_ROLE_IDS for r in member.roles)

def is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.id in ADMIN_ROLE_IDS for r in member.roles)

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


@tasks.loop(hours=6)
async def token_refresh_loop():
    now      = datetime.now(timezone.utc)
    all_v    = await db_all_verified()
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
            if success: refreshed += 1
            else:       failed    += 1
            await asyncio.sleep(0.5)
    if refreshed or failed:
        print(f"[TOKEN REFRESH] ✅ Refreshed: {refreshed} | ❌ Failed: {failed}")

@token_refresh_loop.before_loop
async def before_token_refresh():
    await bot.wait_until_ready()


intents = discord.Intents.default()
intents.message_content = True

# ============================================================
#  GUILD JOIN HELPER
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
        try: await channel.delete()
        except: pass
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
    try: await channel.delete()
    except Exception as e: print(f"Channel delete error: {e}")

# ============================================================
#  STAFF APPLICATION — HELPERS
# ============================================================
async def notify_applicant(user_id: int, action: str, reason: str = ""):
    try:
        user = await bot.fetch_user(user_id)
    except Exception:
        return

    if action == "accepted":
        color = VIREX_COLOR_SUCCESS
        title = "✅ Staff Application — Accepted!"
        desc  = (f"**Congratulations!** Your staff application at **Virex** has been **accepted**.\n\n"
                 f"A staff member will contact you shortly with further instructions.\n\n"
                 f"🌐 {VIREX_WEBSITE}")
    elif action == "denied":
        color = VIREX_COLOR_DANGER
        title = "❌ Staff Application — Denied"
        desc  = ("Thank you for applying to **Virex**.\n\n"
                 "Unfortunately your application was **not accepted** at this time.\n\n"
                 + (f"**Reason:** {reason}\n\n" if reason else "")
                 + "You're welcome to re-apply in the future. 💙")
    elif action == "on_hold":
        color = VIREX_COLOR_WARN
        title = "⏸️ Staff Application — On Hold"
        desc  = ("Your application at **Virex** has been placed **on hold**.\n\n"
                 + (f"**Note:** {reason}\n\n" if reason else "")
                 + "We will get back to you as soon as possible.")
    else:
        return

    embed = discord.Embed(title=title, description=desc, color=color,
                          timestamp=datetime.now(timezone.utc))
    embed.set_footer(text="Virex • Staff Applications")
    set_logo(embed)
    try:
        await user.send(embed=embed)
    except discord.Forbidden:
        pass


async def update_application_embed(app_id: str, action: str, reviewer: discord.Member, reason: str = ""):
    app_data = await db_get_application(app_id)
    if not app_data:
        return
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    channel = guild.get_channel(app_data.get("channel_id") or APPLICATION_CHANNEL_ID)
    if not channel:
        return
    try:
        msg = await channel.fetch_message(app_data["message_id"])
    except Exception:
        return
    status_map = {
        "accepted": ("✅ ACCEPTED", VIREX_COLOR_SUCCESS),
        "denied":   ("❌ DENIED",   VIREX_COLOR_DANGER),
        "on_hold":  ("⏸️ ON HOLD",  VIREX_COLOR_WARN),
    }
    status_label, color = status_map.get(action, ("❓ UNKNOWN", 0x888888))
    old   = msg.embeds[0] if msg.embeds else None
    embed = discord.Embed(title=old.title if old else "Staff Application", color=color,
                          timestamp=datetime.now(timezone.utc))
    if old:
        for field in old.fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        value=(f"**Status:** {status_label}\n"
               f"**Reviewed by:** {reviewer.mention}\n"
               f"**Reviewed at:** <t:{int(datetime.now(timezone.utc).timestamp())}:F>"
               + (f"\n**Reason:** {reason}" if reason else "")),
        inline=False
    )
    embed.set_footer(text=f"Application ID: {app_id} • Virex")
    set_logo(embed)
    await msg.edit(embed=embed, view=None)

# ============================================================
#  STAFF APPLICATION — MODALS
# ============================================================
class DenyReasonModal(discord.ui.Modal, title="Deny Application"):
    reason = discord.ui.TextInput(
        label="Reason for denial (optional)",
        placeholder="Enter a reason that will be sent to the applicant...",
        required=False, max_length=500,
        style=discord.TextStyle.paragraph
    )
    def __init__(self, app_id: str):
        super().__init__()
        self.app_id = app_id

    async def on_submit(self, interaction: discord.Interaction):
        # Defer immediately — everything below (DB write, embed edit, DM) can be slow.
        await interaction.response.defer(ephemeral=True, thinking=True)
        app_data = await db_get_application(self.app_id)
        if not app_data:
            await interaction.followup.send("❌ Application not found.", ephemeral=True)
            return
        reason_text = self.reason.value.strip()
        await db_update_application(
            self.app_id,
            status="denied",
            reviewed_by=interaction.user.id,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
            deny_reason=reason_text,
        )
        await update_application_embed(self.app_id, "denied", interaction.user, reason_text)
        await notify_applicant(int(app_data["discord_id"]), "denied", reason_text)
        await interaction.followup.send(
            embed=discord.Embed(
                description=f"❌ Application `{self.app_id}` denied."
                            + (f"\n**Reason:** {reason_text}" if reason_text else ""),
                color=VIREX_COLOR_DANGER), ephemeral=True)


class OnHoldReasonModal(discord.ui.Modal, title="Put Application On Hold"):
    reason = discord.ui.TextInput(
        label="Note for the applicant (optional)",
        placeholder="Enter a note that will be sent to the applicant...",
        required=False, max_length=500,
        style=discord.TextStyle.paragraph
    )
    def __init__(self, app_id: str):
        super().__init__()
        self.app_id = app_id

    async def on_submit(self, interaction: discord.Interaction):
        # Defer immediately — everything below (DB write, embed edit, DM) can be slow.
        await interaction.response.defer(ephemeral=True, thinking=True)
        app_data = await db_get_application(self.app_id)
        if not app_data:
            await interaction.followup.send("❌ Application not found.", ephemeral=True)
            return
        note_text = self.reason.value.strip()
        await db_update_application(
            self.app_id,
            status="on_hold",
            reviewed_by=interaction.user.id,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )
        await update_application_embed(self.app_id, "on_hold", interaction.user, note_text)
        await notify_applicant(int(app_data["discord_id"]), "on_hold", note_text)
        await interaction.followup.send(
            embed=discord.Embed(description=f"⏸️ Application `{self.app_id}` placed on hold.",
                                color=VIREX_COLOR_WARN), ephemeral=True)

# ============================================================
#  STAFF APPLICATION — REVIEW VIEW
# ============================================================
class ApplicationReviewView(discord.ui.View):
    def __init__(self, app_id: str):
        super().__init__(timeout=None)
        self.app_id = app_id

    async def _resolve_app_id(self, message_id: int) -> str:
        all_apps = await db_all_applications()
        for aid, adata in all_apps.items():
            if adata.get("message_id") == message_id:
                return aid
        return self.app_id

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅", custom_id="app_accept")
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Staff only.", ephemeral=True); return
        # Defer immediately — DB lookup, embed edit and DM send can all be slow.
        await interaction.response.defer(ephemeral=True, thinking=True)
        app_id   = await self._resolve_app_id(interaction.message.id)
        app_data = await db_get_application(app_id)
        if not app_data:
            await interaction.followup.send("❌ Application not found.", ephemeral=True); return
        if app_data.get("status") not in ("pending", "on_hold"):
            await interaction.followup.send("❌ Already reviewed.", ephemeral=True); return
        await db_update_application(
            app_id,
            status="accepted",
            reviewed_by=interaction.user.id,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )
        await update_application_embed(app_id, "accepted", interaction.user)
        await notify_applicant(int(app_data["discord_id"]), "accepted")
        await interaction.followup.send(
            embed=discord.Embed(description=f"✅ Application `{app_id}` accepted! Applicant notified.",
                                color=VIREX_COLOR_SUCCESS), ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, emoji="❌", custom_id="app_deny")
    async def deny_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Staff only.", ephemeral=True); return
        app_id   = await self._resolve_app_id(interaction.message.id)
        app_data = await db_get_application(app_id)
        if not app_data:
            await interaction.response.send_message("❌ Application not found.", ephemeral=True); return
        if app_data.get("status") not in ("pending", "on_hold"):
            await interaction.response.send_message("❌ Already reviewed.", ephemeral=True); return
        # NOTE: a modal must be the *first* response to the interaction, so we
        # cannot defer() before this — keep the DB lookup above fast/lightweight.
        await interaction.response.send_modal(DenyReasonModal(app_id=app_id))

    @discord.ui.button(label="On Hold", style=discord.ButtonStyle.secondary, emoji="⏸️", custom_id="app_hold")
    async def hold_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Staff only.", ephemeral=True); return
        app_id   = await self._resolve_app_id(interaction.message.id)
        app_data = await db_get_application(app_id)
        if not app_data:
            await interaction.response.send_message("❌ Application not found.", ephemeral=True); return
        if app_data.get("status") != "pending":
            await interaction.response.send_message("❌ Already reviewed or on hold.", ephemeral=True); return
        await interaction.response.send_modal(OnHoldReasonModal(app_id=app_id))

    @discord.ui.button(label="Open Interview", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="app_interview")
    async def interview_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Staff only.", ephemeral=True); return
        # Defer immediately — resolving the app + creating a channel can be slow.
        await interaction.response.defer(ephemeral=True, thinking=True)
        app_id   = await self._resolve_app_id(interaction.message.id)
        app_data = await db_get_application(app_id)
        if not app_data:
            await interaction.followup.send("❌ Application not found.", ephemeral=True); return
        if app_data.get("interview_channel"):
            await interaction.followup.send("❌ Interview channel already exists.", ephemeral=True); return

        guild        = interaction.guild
        applicant_id = app_data.get("discord_id")
        applicant    = guild.get_member(int(applicant_id)) if applicant_id else None
        overwrites   = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                             manage_channels=True, read_message_history=True),
        }
        if applicant:
            overwrites[applicant] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                                  read_message_history=True)
        for rid in STAFF_ROLE_IDS + ADMIN_ROLE_IDS:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                                 read_message_history=True)
        cat_channel = guild.get_channel(TICKET_CATEGORY_ID)
        uname_slug  = app_data.get("discord_username", "applicant").lower().replace(" ", "-")
        num         = len([c for c in guild.text_channels if c.name.startswith("app-")]) + 1
        try:
            channel = await guild.create_text_channel(
                name=f"app-{uname_slug}-{num:03d}", overwrites=overwrites,
                category=cat_channel, topic=f"Staff Application Interview | app_id:{app_id}"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Could not create channel: {e}", ephemeral=True); return

        embed = discord.Embed(
            title="🎫 Staff Application — Interview Channel",
            description=(f"Interview channel for {applicant.mention if applicant else f'<@{applicant_id}>'}.\n\n"
                         f"**Application ID:** `{app_id}`\n"
                         "Staff can use this channel to interview or discuss the application."),
            color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
        )
        set_logo(embed)
        await channel.send(
            content=" ".join(filter(None, [interaction.user.mention, applicant.mention if applicant else ""])),
            embed=embed
        )
        await db_update_application(app_id, interview_channel=channel.id)
        await interaction.followup.send(
            embed=discord.Embed(description=f"✅ Interview channel created: {channel.mention}", color=VIREX_COLOR),
            ephemeral=True)

# ============================================================
#  BACKGROUND TASK — POLL FOR NEW APPLICATIONS
# ============================================================
_posting_in_progress: set[str] = set()

@tasks.loop(seconds=10)
async def poll_applications():
    fresh = await db_all_applications()
    for app_id, data in fresh.items():
        if data.get("status") != "pending":
            continue
        if data.get("message_id"):
            continue
        if app_id in _posting_in_progress:
            continue
        _posting_in_progress.add(app_id)
        success = await _post_application(app_id)
        if not success:
            _posting_in_progress.discard(app_id)

@poll_applications.before_loop
async def before_poll():
    await bot.wait_until_ready()


async def _post_application(app_id: str) -> bool:
    app_data = await db_get_application(app_id)
    if not app_data:
        return False

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print(f"[APPS] ❌ Guild {GUILD_ID} not found")
        return False

    channel = guild.get_channel(APPLICATION_CHANNEL_ID)
    if not channel:
        print(f"[APPS] ❌ APPLICATION_CHANNEL_ID {APPLICATION_CHANNEL_ID} not found — check your .env!")
        return False

    user_id      = app_data.get("discord_id", 0)
    username     = app_data.get("discord_username", "Unknown")
    submitted_ts = int(datetime.fromisoformat(app_data["submitted_at"]).timestamp())

    embed = discord.Embed(
        title=f"📋 Staff Application — {username}",
        color=VIREX_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Application ID: {app_id} • Virex")
    set_logo(embed)
    embed.add_field(
        name="👤 Applicant",
        value=f"**Username:** {username}\n**Discord ID:** `{user_id}`\n**Submitted:** <t:{submitted_ts}:F>",
        inline=False
    )
    embed.add_field(name="🎂 Age",                 value=app_data.get("age", "—"),            inline=True)
    embed.add_field(name="🌍 Timezone",            value=app_data.get("timezone", "—"),        inline=True)
    embed.add_field(name="🗣️ Languages",           value=app_data.get("languages", "—"),       inline=True)
    embed.add_field(name="⏰ Weekly Availability", value=app_data.get("availability", "—"),    inline=True)
    embed.add_field(name="📅 Discord Account Age", value=app_data.get("discord_since", "—"),  inline=True)
    embed.add_field(name="🛡️ Previous Staff Exp.", value=app_data.get("previous_staff", "—"), inline=False)
    embed.add_field(name="💡 Why Join Virex?",     value=app_data.get("why_valora", "—"),      inline=False)
    embed.add_field(name="🔧 Skills & Strengths",  value=app_data.get("skills", "—"),          inline=False)
    extra = app_data.get("extra", "") or "—"
    embed.add_field(name="📌 Anything Else?",      value=extra,                                inline=False)

    view = ApplicationReviewView(app_id=app_id)
    try:
        msg = await channel.send(embed=embed, view=view)
        await db_update_application(app_id, message_id=msg.id, channel_id=channel.id)
        print(f"[APPS] ✅ Posted application {app_id} → msg {msg.id} in #{channel.name}")
        return True
    except Exception as e:
        print(f"[APPS] ❌ Failed to post {app_id}: {e}")
        return False

# ============================================================
#  VIEWS — TICKETS
# ============================================================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Select a category to open a ticket...",
            min_values=1, max_values=1, custom_id="virex_ticket_select",
            options=[discord.SelectOption(label=v["label"], description=v["description"], emoji=v["emoji"], value=k)
                     for k, v in TICKET_CATEGORIES.items()]
        )

    async def callback(self, interaction: discord.Interaction):
        cat_key = self.values[0]
        cat     = TICKET_CATEGORIES[cat_key]
        guild   = interaction.guild

        # Defer immediately — channel creation + DB write can take >3s and would
        # otherwise trigger Discord's "Interaktion fehlgeschlagen" error.
        await interaction.response.defer(ephemeral=True, thinking=True)

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
        num = len([c for c in guild.text_channels if c.name.startswith("ticket-")]) + 1
        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{num:04d}", overwrites=overwrites, category=cat_channel,
                topic=f"uid-{interaction.user.id} | {cat_key} | open"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Could not create ticket: {e}", ephemeral=True)
            return
        await db_set_ticket(str(channel.id), {
            "user_id": interaction.user.id, "category": cat_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "auto_close": True, "status": "open"
        })
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)
        embed = discord.Embed(
            title=f"{cat['emoji']} {cat['label']} — Ticket #{num:04d}",
            description=(f"Welcome, {interaction.user.mention}! 👋\n\n**Our support team will be with you shortly.**\n\n"
                         f"🌐 **Website:** [{VIREX_WEBSITE}]({VIREX_WEBSITE})\n\n"
                         "Please describe your issue and we'll get back to you as soon as possible."),
            color=cat["color"], timestamp=datetime.now(timezone.utc)
        )
        set_logo(embed)
        embed.set_footer(text="Virex • Premium Products")
        await channel.send(content=interaction.user.mention, embed=embed, view=TicketControlView())


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
            await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True); return
        if not is_staff(interaction.user) and info["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ Only staff or the ticket owner can close this.", ephemeral=True); return
        await interaction.response.send_message("🔒 Closing in 5 seconds...")
        await asyncio.sleep(5)
        await close_ticket(interaction.channel, interaction.guild, closed_by=interaction.user)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.success, emoji="✋", custom_id="virex_claim_ticket")
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Only staff can claim tickets.", ephemeral=True); return
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


class StaffApplyView(discord.ui.View):
    def __init__(self, apply_url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="Apply for Staff", style=discord.ButtonStyle.link, url=apply_url, emoji="📋"))

# ============================================================
#  BOT
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ============================================================
#  BACKGROUND TASKS
# ============================================================
@tasks.loop(minutes=30)
async def auto_close_task():
    now      = datetime.now(timezone.utc)
    all_t    = await db_all_tickets()
    to_close = []
    for cid, info in all_t.items():
        if info.get("status") != "open": continue
        if not info.get("auto_close", True): continue
        last = datetime.fromisoformat(info["last_activity"])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if now - last >= timedelta(hours=AUTO_CLOSE_HOURS):
            to_close.append(cid)
    for cid in to_close:
        guild = bot.get_guild(GUILD_ID)
        if not guild: continue
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

# ============================================================
#  EVENTS
# ============================================================
@bot.event
async def on_ready():
    print(f"✅ Virex Bot online — {bot.user}")
    await init_db()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="Virex 🔵")
    )
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    bot.add_view(StoreView())
    all_apps = await db_all_applications()
    for app_id, data in all_apps.items():
        if data.get("status") in ("pending", "on_hold") and data.get("message_id"):
            bot.add_view(ApplicationReviewView(app_id=app_id))
    if not auto_close_task.is_running():       auto_close_task.start()
    if not poll_applications.is_running():     poll_applications.start()
    if not token_refresh_loop.is_running():
        token_refresh_loop.start()
        print("🔄 Token refresh loop started (runs every 6h)")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Sync error: {e}")
    print("✅ All Virex systems ready!")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # * prefix — send as bot
    if message.content.startswith("*"):
        text = message.content[1:]
        await message.delete()
        await message.channel.send(text)
        return

    # Update ticket last_activity
    cid  = str(message.channel.id)
    info = await db_get_ticket(cid)
    if info and info.get("status") == "open":
        await db_update_ticket(cid, last_activity=datetime.now(timezone.utc).isoformat())

    await bot.process_commands(message)


@bot.event
async def on_member_join(member: discord.Member):
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


# ============================================================
#  on_interaction — handles the smedia ticket button
# ============================================================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    if interaction.data.get("custom_id") != "virex_media_ticket":
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
    num = len([c for c in guild.text_channels if c.name.startswith("ticket-")]) + 1
    try:
        ch = await guild.create_text_channel(
            name=f"ticket-{num:04d}", overwrites=overwrites, category=cat_channel,
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

# ============================================================
#  SLASH — TICKETS
# ============================================================
@bot.tree.command(name="panel", description="Send the Virex ticket panel (Admin only)")
@app_commands.guild_only()
async def cmd_panel(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
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
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.followup.send("✅ Panel sent!", ephemeral=True)


@bot.tree.command(name="store", description="Send the Virex store panel (Admin only)")
@app_commands.guild_only()
async def cmd_store(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
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
        await interaction.response.send_message("❌ Staff only.", ephemeral=True); return
    info = await db_get_ticket(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True); return
    await interaction.response.send_message("🔒 Closing in 5 seconds...")
    await asyncio.sleep(5)
    await close_ticket(interaction.channel, interaction.guild, closed_by=interaction.user)


@bot.tree.command(name="add", description="Add a user to the current ticket (Staff only)")
@app_commands.describe(user="User to add")
@app_commands.guild_only()
async def cmd_add(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True); return
    info = await db_get_ticket(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True); return
    await interaction.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
    await interaction.response.send_message(
        embed=discord.Embed(description=f"✅ {user.mention} added.", color=VIREX_COLOR_SUCCESS))


@bot.tree.command(name="remove", description="Remove a user from the current ticket (Staff only)")
@app_commands.describe(user="User to remove")
@app_commands.guild_only()
async def cmd_remove(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True); return
    info = await db_get_ticket(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True); return
    await interaction.channel.set_permissions(user, overwrite=None)
    await interaction.response.send_message(
        embed=discord.Embed(description=f"✅ {user.mention} removed.", color=VIREX_COLOR_DANGER))


@bot.tree.command(name="autoclose", description="Enable or disable auto-close for this ticket (Staff only)")
@app_commands.describe(enabled="True = on  |  False = off")
@app_commands.guild_only()
async def cmd_autoclose(interaction: discord.Interaction, enabled: bool):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Staff only.", ephemeral=True); return
    info = await db_get_ticket(str(interaction.channel.id))
    if not info:
        await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True); return
    await db_update_ticket(str(interaction.channel.id), auto_close=enabled)
    status = "✅ enabled" if enabled else "❌ disabled"
    await interaction.response.send_message(
        embed=discord.Embed(description=f"Auto-close is now **{status}** for this ticket.", color=VIREX_COLOR))

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
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
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
#  SLASH — STAFF APPLICATIONS
# ============================================================
@bot.tree.command(name="applypanel", description="Send the staff application panel (Admin only)")
@app_commands.guild_only()
async def cmd_applypanel(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    apply_url = f"{WEB_BASE_URL}/apply"
    embed = discord.Embed(
        title="📋 Staff Application — Virex",
        description=("**Want to become part of the Virex team?**\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                     "👥 **What we're looking for:**\n"
                     "├ Active & dedicated members\n"
                     "├ Good communication skills\n"
                     "├ Willingness to help customers\n"
                     "└ Previous experience is a plus\n\n"
                     "📋 **How to apply:**\n"
                     "Click the button below, fill out the application form and submit it.\n"
                     "Our team will review your application as soon as possible.\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n"
                     "*All applications are reviewed manually by our admin team.*"),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    set_logo(embed)
    embed.set_footer(text="Virex • Staff Applications 📋")
    await interaction.channel.send(embed=embed, view=StaffApplyView(apply_url))
    await interaction.followup.send("✅ Application panel sent!", ephemeral=True)


@bot.tree.command(name="app_list", description="List all staff applications (Admin only)")
@app_commands.guild_only()
async def cmd_app_list(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
    all_apps = await db_all_applications()
    if not all_apps:
        await interaction.response.send_message("📭 No applications found.", ephemeral=True); return
    status_icons = {"pending": "⏳", "accepted": "✅", "denied": "❌", "on_hold": "⏸️"}
    lines = []
    for app_id, data in sorted(all_apps.items(),
                                key=lambda x: x[1].get("submitted_at", ""), reverse=True):
        icon  = status_icons.get(data.get("status", "pending"), "❓")
        uname = data.get("discord_username", "Unknown")
        uid   = data.get("discord_id", "?")
        date  = str(data.get("submitted_at", ""))[:10]
        lines.append(f"{icon} `{app_id}` — **{uname}** (`{uid}`) — {date}")
    chunks, chunk, length = [], [], 0
    for line in lines:
        if length + len(line) > 3800:
            chunks.append(chunk); chunk, length = [line], len(line)
        else:
            chunk.append(line); length += len(line)
    if chunk: chunks.append(chunk)
    for i, ch in enumerate(chunks):
        embed = discord.Embed(
            title=f"📋 Staff Applications {'(cont.)' if i > 0 else ''}",
            description="\n".join(ch), color=VIREX_COLOR
        )
        if i == 0:
            embed.set_footer(text=f"Total: {len(all_apps)} applications")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="app_stats", description="Show application statistics (Admin only)")
@app_commands.guild_only()
async def cmd_app_stats(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
    all_apps = await db_all_applications()
    total    = len(all_apps)
    pending  = sum(1 for v in all_apps.values() if v.get("status") == "pending")
    accepted = sum(1 for v in all_apps.values() if v.get("status") == "accepted")
    denied   = sum(1 for v in all_apps.values() if v.get("status") == "denied")
    on_hold  = sum(1 for v in all_apps.values() if v.get("status") == "on_hold")
    embed = discord.Embed(
        title="📊 Application Statistics",
        description=(f"📋 **Total Applications:** `{total}`\n"
                     f"⏳ **Pending:** `{pending}`\n"
                     f"✅ **Accepted:** `{accepted}`\n"
                     f"❌ **Denied:** `{denied}`\n"
                     f"⏸️ **On Hold:** `{on_hold}`"),
        color=VIREX_COLOR, timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Virex • Staff Applications")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================================
#  SLASH — BACKUP / RESTORE
# ============================================================
@bot.tree.command(name="backup_restore", description="Restore a single user back to this server (Admin only)")
@app_commands.describe(user_id="Discord User ID of the person to restore")
@app_commands.guild_only()
async def cmd_backup_restore(interaction: discord.Interaction, user_id: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
    if not user_id.strip().isdigit():
        await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True); return
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
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
    all_v = await db_all_verified()
    if not all_v:
        await interaction.response.send_message("📭 No verified users in backup.", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    added, already, failed, expired = [], [], [], []
    total = len(all_v)
    for uid, info in all_v.items():
        result = await add_member_to_guild(int(uid), interaction.guild.id)
        name   = info.get("username", uid)
        if result["status"] == "added":           added.append(name)
        elif result["status"] == "already":       already.append(name)
        elif result["status"] == "token_expired": expired.append(name)
        else:                                     failed.append(f"{name} — {result['detail']}")
        await asyncio.sleep(0.5)

    def fmt_list(lst, limit=20):
        if not lst: return "—"
        shown = lst[:limit]; extra = len(lst) - limit
        text  = ", ".join(f"`{x}`" for x in shown)
        if extra > 0: text += f" *+{extra} more*"
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
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
    all_v = await db_all_verified()
    if not all_v:
        await interaction.response.send_message("📭 Backup is empty.", ephemeral=True); return
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
            chunks.append(chunk); chunk, length = [line], len(line)
        else:
            chunk.append(line); length += len(line)
    if chunk: chunks.append(chunk)
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
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
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
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    all_v = await db_all_verified()
    total = len(all_v)
    refreshed = failed = skipped = 0
    for uid, info in all_v.items():
        if not info.get("refresh_token"):
            skipped += 1; continue
        success = await refresh_token(uid)
        if success: refreshed += 1
        else:       failed    += 1
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
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)

    v_count = t_count = a_count = 0

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

    # applications.json
    a_data = load_json(APPLICATIONS_FILE)
    for app_id, info in a_data.items():
        await db_set_application(app_id, info)
        a_count += 1

    embed = discord.Embed(
        title="✅ JSON → PostgreSQL Migration Complete",
        description=(f"👥 **Verified users imported:** `{v_count}`\n"
                     f"🎫 **Tickets imported:** `{t_count}`\n"
                     f"📋 **Applications imported:** `{a_count}`"),
        color=VIREX_COLOR_SUCCESS, timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Virex • Database Migration")
    await interaction.followup.send(embed=embed, ephemeral=True)


# ============================================================
#  RUN
# ============================================================
if __name__ == "__main__":
    bot.run(TOKEN)
