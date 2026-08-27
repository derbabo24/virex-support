import asyncio
import os
import sys
import re
import io
import time
import datetime
import random
import ast
import operator
import urllib.parse
from collections import defaultdict
from typing import List, Optional, Tuple, Dict, Any

import aiohttp
import aiosqlite
import discord
from discord.ext import commands, tasks
from discord import ui
from dotenv import load_dotenv

# Ensure UTF-8 stdout across Windows & Linux / Railway
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", ".")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")

COLOR_PRIMARY = 0x5865F2    # Blurple
COLOR_SUCCESS = 0x57F287    # Green
COLOR_WARNING = 0xFEE75C    # Yellow
COLOR_ERROR = 0xED4245      # Red
COLOR_INFO = 0x5865F2       # Blue
COLOR_MOD = 0xE67E22        # Orange
COLOR_PROTECT = 0x9B59B6    # Purple

EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"
EMOJI_WARNING = "⚠️"
EMOJI_SHIELD = "🛡️"
EMOJI_HAMMER = "🔨"
EMOJI_MUTE = "🔇"
EMOJI_WARN = "⚠️"
EMOJI_LOCK = "🔒"
EMOJI_UNLOCK = "🔓"

INVITE_REGEX = re.compile(r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/[a-zA-Z0-9_-]+")
LINK_REGEX = re.compile(r"https?://\S+|www\.\S+")

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

EIGHT_BALL_RESPONSES = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful."
]

ROASTS = [
    "You're the reason the gene pool needs a lifeguard.",
    "If I had a face like yours, I'd sue my parents.",
    "You bring everyone so much joy... when you leave the room.",
    "I'd agree with you, but then we'd both be wrong.",
    "Your secrets are always safe with me. I never even listen when you tell me them.",
    "I'm not insulting you, I'm describing you.",
    "You have an entire life to be an idiot. Why not take today off?"
]

FACTS = [
    "Honey never spoils. Archaeologists have found 3000-year-old honey in Egyptian tombs that is still perfectly edible.",
    "Octopuses have three hearts and blue blood.",
    "Bananas are curved because they grow towards the sun.",
    "A day on Venus is longer than a year on Venus.",
    "Water makes different pouring sounds depending on its temperature."
]

def safe_eval(expr: str):
    """Safely evaluates basic arithmetic expressions via AST."""
    def eval_node(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = eval_node(node.left)
            right = eval_node(node.right)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            operand = eval_node(node.operand)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type}")
        else:
            raise ValueError("Invalid expression element")

    tree = ast.parse(expr, mode='eval')
    return eval_node(tree.body)

def parse_time_duration(time_str: str) -> int:
    """Parses a time string like '10m', '2h', '1d', '30s' into seconds."""
    time_regex = re.compile(r"^(\d+)([smhd])$")
    match = time_regex.match(time_str.lower())
    if not match:
        if time_str.isdigit():
            return int(time_str) * 60
        return 0

    val, unit = int(match.group(1)), match.group(2)
    if unit == 's':
        return val
    elif unit == 'm':
        return val * 60
    elif unit == 'h':
        return val * 3600
    elif unit == 'd':
        return val * 86400
    return 0

# ==========================================
# ASYNC SQLITE DATABASE LAYER
# ==========================================

class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Creates all necessary SQLite tables on startup."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    prefix TEXT DEFAULT '.',
                    mod_log_channel_id INTEGER DEFAULT 0,
                    welcome_channel_id INTEGER DEFAULT 0,
                    welcome_message TEXT DEFAULT 'Welcome to {server}, {user}!',
                    leave_channel_id INTEGER DEFAULT 0,
                    leave_message TEXT DEFAULT '{user} has left the server.',
                    autorole_id INTEGER DEFAULT 0,
                    ticket_category_id INTEGER DEFAULT 0,
                    modmail_channel_id INTEGER DEFAULT 0,
                    dm_on_mod INTEGER DEFAULT 1
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS protected_mentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    target_type TEXT NOT NULL,
                    punishment TEXT DEFAULT 'delete',
                    mute_duration_seconds INTEGER DEFAULT 300,
                    alert_channel_id INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    UNIQUE(guild_id, target_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS protected_mention_whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    allowed_id INTEGER NOT NULL,
                    allowed_type TEXT NOT NULL,
                    UNIQUE(guild_id, target_id, allowed_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS automod_settings (
                    guild_id INTEGER PRIMARY KEY,
                    anti_spam INTEGER DEFAULT 0,
                    anti_links INTEGER DEFAULT 0,
                    anti_invites INTEGER DEFAULT 0,
                    anti_caps INTEGER DEFAULT 0,
                    max_mentions INTEGER DEFAULT 5
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS bad_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    UNIQUE(guild_id, word)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'open',
                    created_at REAL NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS economy (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    balance INTEGER DEFAULT 100,
                    bank INTEGER DEFAULT 0,
                    last_daily REAL DEFAULT 0,
                    PRIMARY KEY(guild_id, user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS levels (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    last_xp_time REAL DEFAULT 0,
                    PRIMARY KEY(guild_id, user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    reminder_text TEXT NOT NULL,
                    remind_at REAL NOT NULL
                )
            """)

            await db.commit()

    async def get_prefix(self, guild_id: Optional[int]) -> str:
        if not guild_id:
            return DEFAULT_PREFIX
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT prefix FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] else DEFAULT_PREFIX

    async def set_prefix(self, guild_id: int, prefix: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, prefix)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET prefix = excluded.prefix
            """, (guild_id, prefix))
            await db.commit()

    async def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return {
                    "guild_id": guild_id,
                    "prefix": DEFAULT_PREFIX,
                    "mod_log_channel_id": 0,
                    "welcome_channel_id": 0,
                    "welcome_message": "Welcome to {server}, {user}!",
                    "leave_channel_id": 0,
                    "leave_message": "{user} has left the server.",
                    "autorole_id": 0,
                    "ticket_category_id": 0,
                    "modmail_channel_id": 0,
                    "dm_on_mod": 1
                }

    async def update_guild_setting(self, guild_id: int, column: str, value: Any):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))
            await db.execute(f"UPDATE guild_settings SET {column} = ? WHERE guild_id = ?", (value, guild_id))
            await db.commit()

    # --- Anti-Mention DB ---
    async def add_protected_mention(self, guild_id: int, target_id: int, target_type: str, punishment: str = "delete", mute_duration: int = 300, alert_channel_id: int = 0):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO protected_mentions (guild_id, target_id, target_type, punishment, mute_duration_seconds, alert_channel_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, target_id) DO UPDATE SET
                    punishment = excluded.punishment,
                    mute_duration_seconds = excluded.mute_duration_seconds,
                    alert_channel_id = excluded.alert_channel_id
            """, (guild_id, target_id, target_type, punishment, mute_duration, alert_channel_id, time.time()))
            await db.commit()

    async def remove_protected_mention(self, guild_id: int, target_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("DELETE FROM protected_mentions WHERE guild_id = ? AND target_id = ?", (guild_id, target_id))
            await db.execute("DELETE FROM protected_mention_whitelist WHERE guild_id = ? AND target_id = ?", (guild_id, target_id))
            await db.commit()
            return cur.rowcount > 0

    async def get_protected_mentions(self, guild_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM protected_mentions WHERE guild_id = ?", (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_protected_target(self, guild_id: int, target_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM protected_mentions WHERE guild_id = ? AND target_id = ?", (guild_id, target_id)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def add_mention_whitelist(self, guild_id: int, target_id: int, allowed_id: int, allowed_type: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO protected_mention_whitelist (guild_id, target_id, allowed_id, allowed_type)
                VALUES (?, ?, ?, ?)
            """, (guild_id, target_id, allowed_id, allowed_type))
            await db.commit()

    async def remove_mention_whitelist(self, guild_id: int, target_id: int, allowed_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("""
                DELETE FROM protected_mention_whitelist 
                WHERE guild_id = ? AND target_id = ? AND allowed_id = ?
            """, (guild_id, target_id, allowed_id))
            await db.commit()
            return cur.rowcount > 0

    async def get_mention_whitelists(self, guild_id: int, target_id: int) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT allowed_id FROM protected_mention_whitelist WHERE guild_id = ? AND target_id = ?", (guild_id, target_id)) as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    # --- Warnings DB ---
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("""
                INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (guild_id, user_id, moderator_id, reason, time.time()))
            await db.commit()
            return cur.lastrowid

    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC", (guild_id, user_id)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def delete_warning(self, guild_id: int, warn_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("DELETE FROM warnings WHERE guild_id = ? AND id = ?", (guild_id, warn_id))
            await db.commit()
            return cur.rowcount > 0

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await db.commit()
            return cur.rowcount

    # --- AutoMod DB ---
    async def get_automod(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM automod_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return {"guild_id": guild_id, "anti_spam": 0, "anti_links": 0, "anti_invites": 0, "anti_caps": 0, "max_mentions": 5}

    async def update_automod(self, guild_id: int, setting: str, value: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO automod_settings (guild_id) VALUES (?)", (guild_id,))
            await db.execute(f"UPDATE automod_settings SET {setting} = ? WHERE guild_id = ?", (value, guild_id))
            await db.commit()

    async def add_bad_word(self, guild_id: int, word: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO bad_words (guild_id, word) VALUES (?, ?)", (guild_id, word.lower()))
            await db.commit()

    async def remove_bad_word(self, guild_id: int, word: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("DELETE FROM bad_words WHERE guild_id = ? AND word = ?", (guild_id, word.lower()))
            await db.commit()
            return cur.rowcount > 0

    async def get_bad_words(self, guild_id: int) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT word FROM bad_words WHERE guild_id = ?", (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    # --- Tickets DB ---
    async def create_ticket(self, guild_id: int, channel_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("""
                INSERT INTO tickets (guild_id, channel_id, user_id, status, created_at)
                VALUES (?, ?, ?, 'open', ?)
            """, (guild_id, channel_id, user_id, time.time()))
            await db.commit()
            return cur.lastrowid

    async def get_ticket(self, channel_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def close_ticket(self, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (channel_id,))
            await db.commit()

    # --- Economy DB ---
    async def get_economy(self, guild_id: int, user_id: int) -> Dict[str, int]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return {"guild_id": guild_id, "user_id": user_id, "balance": 100, "bank": 0, "last_daily": 0}

    async def update_balance(self, guild_id: int, user_id: int, amount: int, in_bank: bool = False):
        field = "bank" if in_bank else "balance"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO economy (guild_id, user_id, balance, bank)
                VALUES (?, ?, 100, 0)
                ON CONFLICT(guild_id, user_id) DO NOTHING
            """, (guild_id, user_id))
            await db.execute(f"UPDATE economy SET {field} = {field} + ? WHERE guild_id = ? AND user_id = ?", (amount, guild_id, user_id))
            await db.commit()

    async def claim_daily(self, guild_id: int, user_id: int, reward: int = 250) -> Tuple[bool, int]:
        async with aiosqlite.connect(self.db_path) as db:
            eco = await self.get_economy(guild_id, user_id)
            now = time.time()
            cooldown = 86400
            time_left = int(cooldown - (now - eco["last_daily"]))
            if time_left > 0:
                return False, time_left

            await db.execute("""
                INSERT INTO economy (guild_id, user_id, balance, bank, last_daily)
                VALUES (?, ?, ?, 0, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    balance = balance + excluded.balance,
                    last_daily = excluded.last_daily
            """, (guild_id, user_id, reward, now))
            await db.commit()
            return True, reward

    async def get_economy_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT user_id, (balance + bank) AS total
                FROM economy
                WHERE guild_id = ?
                ORDER BY total DESC
                LIMIT ?
            """, (guild_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # --- Levels & XP DB ---
    async def add_xp(self, guild_id: int, user_id: int, xp_amount: int) -> Tuple[int, int, bool]:
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                row = await cursor.fetchone()

            if not row:
                current_xp = xp_amount
                current_level = 1
                await db.execute("""
                    INSERT INTO levels (guild_id, user_id, xp, level, last_xp_time)
                    VALUES (?, ?, ?, ?, ?)
                """, (guild_id, user_id, current_xp, current_level, now))
                await db.commit()
                return current_xp, current_level, False

            if now - row["last_xp_time"] < 60:
                return row["xp"], row["level"], False

            new_xp = row["xp"] + xp_amount
            new_level = int((new_xp / 100) ** 0.5) + 1
            did_level_up = new_level > row["level"]

            await db.execute("""
                UPDATE levels SET xp = ?, level = ?, last_xp_time = ?
                WHERE guild_id = ? AND user_id = ?
            """, (new_xp, new_level, now, guild_id, user_id))
            await db.commit()
            return new_xp, new_level, did_level_up

    async def get_level_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT user_id, xp, level
                FROM levels
                WHERE guild_id = ?
                ORDER BY xp DESC
                LIMIT ?
            """, (guild_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_user_level(self, guild_id: int, user_id: int) -> Dict[str, int]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT xp, level FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return {"xp": 0, "level": 1}

    # --- Reminders DB ---
    async def add_reminder(self, user_id: int, channel_id: int, text: str, remind_at: float) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("""
                INSERT INTO reminders (user_id, channel_id, reminder_text, remind_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, channel_id, text, remind_at))
            await db.commit()
            return cur.lastrowid

    async def get_due_reminders(self) -> List[Dict[str, Any]]:
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM reminders WHERE remind_at <= ?", (now,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def delete_reminder(self, reminder_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            await db.commit()

# ==========================================
# INTERACTIVE BUTTON TICKET VIEWS
# ==========================================

class TicketControlsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_btn")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        ticket_data = await self.bot.db.get_ticket(interaction.channel.id)
        if not ticket_data:
            return await interaction.followup.send("❌ This channel is not an active ticket.", ephemeral=True)

        await self.bot.db.close_ticket(interaction.channel.id)
        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description=f"Ticket closed by {interaction.user.mention}. This channel will be deleted in 5 seconds.",
            color=COLOR_WARNING
        )
        await interaction.followup.send(embed=embed)
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception:
            pass

    @ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📄", custom_id="ticket_transcript_btn")
    async def transcript_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        messages = []
        async for m in interaction.channel.history(limit=500, oldest_first=True):
            messages.append(f"[{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {m.author}: {m.content}")

        transcript_text = "\n".join(messages)
        file_data = io.BytesIO(transcript_text.encode("utf-8"))
        discord_file = discord.File(file_data, filename=f"transcript-{interaction.channel.name}.txt")

        await interaction.followup.send(
            content=f"📄 Transcript for **{interaction.channel.name}**:",
            file=discord_file,
            ephemeral=True
        )

class TicketPanelView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Open a Ticket", style=discord.ButtonStyle.primary, emoji="📩", custom_id="ticket_open_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        user = interaction.user

        settings = await self.bot.db.get_guild_settings(guild.id)
        category_id = settings.get("ticket_category_id")
        category = guild.get_channel(category_id) if category_id else None

        chan_name = f"ticket-{user.name.lower()[:15]}"
        existing = discord.utils.get(guild.text_channels, name=chan_name)
        if existing:
            return await interaction.response.send_message(
                f"❌ You already have an open ticket: {existing.mention}", ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        channel = await guild.create_text_channel(
            name=chan_name,
            category=category,
            overwrites=overwrites,
            topic=f"Support Ticket for {user} ({user.id})"
        )

        await self.bot.db.create_ticket(guild.id, channel.id, user.id)

        embed = discord.Embed(
            title=f"🎫 Support Ticket - #{channel.name}",
            description=f"Welcome {user.mention}!\nPlease describe your issue in detail. Our staff will assist you shortly.",
            color=COLOR_PRIMARY
        )
        embed.set_footer(text="Click 'Close Ticket' when your issue is resolved.")

        await channel.send(content=f"{user.mention} | Staff Team", embed=embed, view=TicketControlsView(self.bot))
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# ==========================================
# CUSTOM HELP COMMAND
# ==========================================

class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context
        prefix = await ctx.bot.db.get_prefix(ctx.guild.id if ctx.guild else None)

        embed = discord.Embed(
            title="🛡️ SentinelBot Command Help",
            description=f"Current Prefix: `{prefix}` | Type `{prefix}help <command>` for usage details.",
            color=COLOR_PRIMARY
        )

        # Categorize all commands
        categories = {
            "🛡️ Anti-Mention": ["antiping"],
            "🔨 Moderation": ["ban", "unban", "softban", "tempban", "massban", "kick", "mute", "unmute", "warn", "warns", "delwarn", "clearwarns", "purge", "purgeuser", "purgebot", "purgelinks", "lock", "unlock", "hide", "unhide", "slowmode", "setnick", "role"],
            "✉️ Direct Messages": ["dm", "reply", "massdm", "toggledm"],
            "🤖 AutoMod": ["automod", "badwords"],
            "🎫 Ticket System": ["ticket"],
            "⚙️ Server Setup": ["settings", "setprefix", "setmodlog", "setmodmail", "setwelcome", "welcomemsg", "setleave", "leavemsg", "setautorole", "disableautorole"],
            "🧰 Utility & Info": ["ping", "uptime", "botinfo", "userinfo", "serverinfo", "avatar", "banner", "roleinfo", "channelinfo", "id", "calc", "qrcode", "reminder", "poll", "embed"],
            "🎮 Fun & Games": ["8ball", "coinflip", "dice", "roll", "meme", "joke", "roast", "rps", "ship", "fact", "choose", "say", "slap", "hug", "pat", "rate", "reverse"],
            "💰 Economy & XP": ["balance", "daily", "deposit", "withdraw", "pay", "ecotop", "rank", "xptop"]
        }

        for cat_name, cmd_names in categories.items():
            formatted = " ".join([f"`{c}`" for c in cmd_names])
            embed.add_field(name=f"{cat_name} ({len(cmd_names)})", value=formatted, inline=False)

        embed.set_footer(text="Over 100 Features & Protections Active")
        await ctx.send(embed=embed)

    async def send_command_help(self, command):
        ctx = self.context
        prefix = await ctx.bot.db.get_prefix(ctx.guild.id if ctx.guild else None)

        embed = discord.Embed(
            title=f"Command: {command.name}",
            description=command.help or "No description provided.",
            color=COLOR_PRIMARY
        )
        embed.add_field(name="Usage", value=f"`{prefix}{command.name} {command.signature}`", inline=False)
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join([f"`{a}`" for a in command.aliases]), inline=False)
        await ctx.send(embed=embed)

    async def send_group_help(self, group):
        ctx = self.context
        prefix = await ctx.bot.db.get_prefix(ctx.guild.id if ctx.guild else None)

        embed = discord.Embed(
            title=f"Group: {group.name}",
            description=group.help or "No description provided.",
            color=COLOR_PRIMARY
        )
        subcommands = [f"`{prefix}{group.name} {c.name}` - {c.short_doc or 'No description'}" for c in group.commands]
        embed.add_field(name="Subcommands", value="\n".join(subcommands), inline=False)
        await ctx.send(embed=embed)

# ==========================================
# BOT CLIENT CLASS
# ==========================================

async def dynamic_prefix(bot, message):
    if not message.guild:
        return DEFAULT_PREFIX
    return await bot.db.get_prefix(message.guild.id)

class SentinelBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=dynamic_prefix,
            intents=intents,
            help_command=CustomHelp(),
            case_insensitive=True
        )
        self.db = Database(DATABASE_PATH)
        self.start_time = time.time()
        self.user_message_times = defaultdict(list)

    async def setup_hook(self):
        print("🔧 Initializing Database tables...")
        await self.db.init_db()

        # Register persistent ticket views
        self.add_view(TicketPanelView(self))
        self.add_view(TicketControlsView(self))

        # Start reminder background task loop
        self.reminder_loop.start()

    @tasks.loop(seconds=15.0)
    async def reminder_loop(self):
        due_list = await self.db.get_due_reminders()
        for r in due_list:
            user = self.get_user(r["user_id"])
            channel = self.get_channel(r["channel_id"])
            embed = discord.Embed(
                title="⏰ Reminder Alert",
                description=r["reminder_text"],
                color=COLOR_WARNING,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="Your scheduled reminder is here!")

            target_mention = user.mention if user else f"<@{r['user_id']}>"
            if channel:
                try:
                    await channel.send(content=target_mention, embed=embed)
                except Exception:
                    if user:
                        try:
                            await user.send(embed=embed)
                        except Exception:
                            pass
            elif user:
                try:
                    await user.send(embed=embed)
                except Exception:
                    pass

            await self.db.delete_reminder(r["id"])

    @reminder_loop.before_loop
    async def before_reminder_loop(self):
        await self.wait_until_ready()

bot = SentinelBot()

# ==========================================
# EVENTS & LISTENERS
# ==========================================

@bot.event
async def on_ready():
    print(f"\n=======================================================")
    print(f"  Logged in as: {bot.user.name}#{bot.user.discriminator} (ID: {bot.user.id})")
    print(f"  Connected to {len(bot.guilds)} guilds.")
    print(f"  Ready for 24/7 Hosting on Railway!")
    print(f"=======================================================\n")

    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{DEFAULT_PREFIX}help | Guarding Servers")
    await bot.change_presence(status=discord.Status.online, activity=activity)

@bot.event
async def on_message(message: discord.Message):
    # 1. Handle DMs / ModMail
    if not message.guild:
        if not message.author.bot:
            for guild in bot.guilds:
                member = guild.get_member(message.author.id)
                if member:
                    settings = await bot.db.get_guild_settings(guild.id)
                    modmail_id = settings.get("modmail_channel_id")
                    if modmail_id:
                        modmail_chan = guild.get_channel(modmail_id)
                        if modmail_chan:
                            embed = discord.Embed(
                                title="📩 ModMail Received",
                                description=message.content or "*(No text content)*",
                                color=COLOR_PRIMARY,
                                timestamp=discord.utils.utcnow()
                            )
                            embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar.url)
                            embed.set_footer(text=f"Reply using: .reply {message.author.id} <your response>")
                            if message.attachments:
                                att_links = "\n".join([f"[{a.filename}]({a.url})" for a in message.attachments])
                                embed.add_field(name="Attachments", value=att_links, inline=False)
                            await modmail_chan.send(embed=embed)
                            try:
                                await message.add_reaction("✅")
                            except Exception:
                                pass
        return

    if message.author.bot:
        return

    guild_id = message.guild.id

    # 2. Anti-Mention / Anti-@ System
    if (message.mentions or message.role_mentions) and not message.author.guild_permissions.administrator:
        protected_list = await bot.db.get_protected_mentions(guild_id)
        if protected_list:
            protected_map = {item["target_id"]: item for item in protected_list}
            triggered = None
            target_obj = None

            for u in message.mentions:
                if u.id in protected_map:
                    wl = await bot.db.get_mention_whitelists(guild_id, u.id)
                    author_roles = [r.id for r in message.author.roles]
                    if message.author.id not in wl and not any(rid in wl for rid in author_roles):
                        triggered = protected_map[u.id]
                        target_obj = u
                        break

            if not triggered:
                for r in message.role_mentions:
                    if r.id in protected_map:
                        wl = await bot.db.get_mention_whitelists(guild_id, r.id)
                        author_roles = [role.id for role in message.author.roles]
                        if message.author.id not in wl and not any(rid in wl for rid in author_roles):
                            triggered = protected_map[r.id]
                            target_obj = r
                            break

            if triggered and target_obj:
                try:
                    await message.delete()
                except Exception:
                    pass

                punishment = triggered["punishment"]
                mute_sec = triggered["mute_duration_seconds"] or 300
                punishment_text = "Message deleted"

                if punishment == "warn":
                    warn_id = await bot.db.add_warning(guild_id, message.author.id, bot.user.id, f"Mentioned protected target: {target_obj.name}")
                    punishment_text = f"Warned (Case #{warn_id}) and message deleted"
                elif punishment == "mute":
                    try:
                        await message.author.timeout(datetime.timedelta(seconds=mute_sec), reason=f"Mentioned protected target: {target_obj.name}")
                        punishment_text = f"Timed out for {mute_sec // 60}m and message deleted"
                    except Exception:
                        pass
                elif punishment == "kick":
                    try:
                        await message.author.kick(reason=f"Mentioned protected target: {target_obj.name}")
                        punishment_text = "Kicked from server and message deleted"
                    except Exception:
                        pass

                # Chat alert
                warn_embed = discord.Embed(
                    title=f"{EMOJI_SHIELD} Anti-Mention Protection",
                    description=f"{message.author.mention}, you cannot mention **{target_obj.name}**!\n**Action:** {punishment_text}.",
                    color=COLOR_ERROR
                )
                try:
                    t_msg = await message.channel.send(embed=warn_embed)
                    await t_msg.delete(delay=6)
                except Exception:
                    pass

                # Author DM
                try:
                    dm_emb = discord.Embed(
                        title=f"{EMOJI_SHIELD} Mention Blocked in {message.guild.name}",
                        description=f"Your message was removed because **{target_obj.name}** is protected against pings.\n**Result:** {punishment_text}",
                        color=COLOR_WARNING
                    )
                    await message.author.send(embed=dm_emb)
                except Exception:
                    pass

                # Mod Log
                settings = await bot.db.get_guild_settings(guild_id)
                log_chan_id = triggered["alert_channel_id"] or settings.get("mod_log_channel_id")
                if log_chan_id:
                    log_chan = message.guild.get_channel(log_chan_id)
                    if log_chan:
                        l_emb = discord.Embed(title="🛡️ Anti-Mention Incident", color=COLOR_ERROR, timestamp=discord.utils.utcnow())
                        l_emb.add_field(name="Offender", value=f"{message.author} (`{message.author.id}`)", inline=True)
                        l_emb.add_field(name="Protected Target", value=f"{target_obj.name} (`{target_obj.id}`)", inline=True)
                        l_emb.add_field(name="Action Taken", value=punishment_text, inline=True)
                        await log_chan.send(embed=l_emb)
                return

    # 3. AutoMod
    if not message.author.guild_permissions.manage_messages:
        automod = await bot.db.get_automod(guild_id)
        content = message.content

        # Bad words
        bad_words = await bot.db.get_bad_words(guild_id)
        if bad_words:
            lowered = content.lower()
            if any(w in lowered for w in bad_words):
                try:
                    await message.delete()
                    w_msg = await message.channel.send(f"{EMOJI_WARNING} {message.author.mention}, prohibited words are not allowed.")
                    await w_msg.delete(delay=4)
                except Exception:
                    pass
                return

        # Anti-invites
        if automod.get("anti_invites", 0) and INVITE_REGEX.search(content):
            try:
                await message.delete()
                w_msg = await message.channel.send(f"{EMOJI_SHIELD} {message.author.mention}, Discord server invites are blocked!")
                await w_msg.delete(delay=4)
            except Exception:
                pass
            return

        # Anti-links
        if automod.get("anti_links", 0) and LINK_REGEX.search(content):
            try:
                await message.delete()
                w_msg = await message.channel.send(f"{EMOJI_SHIELD} {message.author.mention}, posting external links is disabled!")
                await w_msg.delete(delay=4)
            except Exception:
                pass
            return

        # Anti-caps
        if automod.get("anti_caps", 0) and len(content) > 8:
            caps = sum(1 for c in content if c.isupper())
            if (caps / len(content)) > 0.70:
                try:
                    await message.delete()
                    w_msg = await message.channel.send(f"{EMOJI_WARNING} {message.author.mention}, avoid excessive CAPITAL letters.")
                    await w_msg.delete(delay=4)
                except Exception:
                    pass
                return

        # Mass mentions
        max_m = automod.get("max_mentions", 5)
        if max_m > 0 and len(message.mentions) > max_m:
            try:
                await message.delete()
                w_msg = await message.channel.send(f"{EMOJI_WARNING} {message.author.mention}, you cannot mention more than {max_m} users at once.")
                await w_msg.delete(delay=4)
            except Exception:
                pass
            return

        # Anti-Spam
        if automod.get("anti_spam", 0):
            now = time.time()
            u_key = (guild_id, message.author.id)
            bot.user_message_times[u_key] = [t for t in bot.user_message_times[u_key] if now - t < 4.0]
            bot.user_message_times[u_key].append(now)
            if len(bot.user_message_times[u_key]) > 5:
                try:
                    await message.delete()
                    w_msg = await message.channel.send(f"{EMOJI_WARNING} {message.author.mention}, stop spamming messages so fast!")
                    await w_msg.delete(delay=4)
                except Exception:
                    pass
                return

    # 4. XP & Leveling
    xp_gain = random.randint(15, 25)
    new_xp, new_lvl, did_lvl_up = await bot.db.add_xp(guild_id, message.author.id, xp_gain)
    if did_lvl_up:
        try:
            await message.channel.send(f"🎉 Congratulations {message.author.mention}, you reached **Level {new_lvl}**!")
        except Exception:
            pass

    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    settings = await bot.db.get_guild_settings(guild.id)

    # AutoRole
    autorole_id = settings.get("autorole_id")
    if autorole_id:
        role = guild.get_role(autorole_id)
        if role:
            try:
                await member.add_roles(role, reason="AutoRole on join")
            except Exception:
                pass

    # Welcome message
    welcome_chan_id = settings.get("welcome_channel_id")
    if welcome_chan_id:
        channel = guild.get_channel(welcome_chan_id)
        if channel:
            raw_msg = settings.get("welcome_message", "Welcome to {server}, {user}!")
            formatted = raw_msg.replace("{user}", member.mention).replace("{server}", guild.name).replace("{members}", str(guild.member_count))
            embed = discord.Embed(title=f"👋 Welcome to {guild.name}!", description=formatted, color=COLOR_SUCCESS, timestamp=discord.utils.utcnow())
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{guild.member_count}")
            try:
                await channel.send(embed=embed)
            except Exception:
                pass

@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild
    settings = await bot.db.get_guild_settings(guild.id)

    leave_chan_id = settings.get("leave_channel_id")
    if leave_chan_id:
        channel = guild.get_channel(leave_chan_id)
        if channel:
            raw_msg = settings.get("leave_message", "{user} has left the server.")
            formatted = raw_msg.replace("{user}", str(member)).replace("{server}", guild.name).replace("{members}", str(guild.member_count))
            embed = discord.Embed(title="👋 Member Left", description=formatted, color=COLOR_WARNING, timestamp=discord.utils.utcnow())
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Remaining: {guild.member_count}")
            try:
                await channel.send(embed=embed)
            except Exception:
                pass

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        perms = ", ".join(error.missing_permissions)
        return await ctx.send(f"{EMOJI_ERROR} You lack permission: `{perms}`")
    if isinstance(error, commands.BotMissingPermissions):
        perms = ", ".join(error.missing_permissions)
        return await ctx.send(f"{EMOJI_ERROR} I lack permission: `{perms}`")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(f"{EMOJI_ERROR} Missing argument: `{error.param.name}`. Type `{ctx.prefix}help {ctx.command}` for usage.")
    if isinstance(error, commands.MemberNotFound):
        return await ctx.send(f"{EMOJI_ERROR} Member `{error.argument}` was not found.")
    if isinstance(error, commands.BadArgument):
        return await ctx.send(f"{EMOJI_ERROR} Invalid argument: {error}")
    print(f"Unhandled error in {ctx.command}: {error}", file=sys.stderr)
    await ctx.send(f"{EMOJI_ERROR} Error executing command: `{error}`")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

async def log_mod_action(guild: discord.Guild, embed: discord.Embed):
    settings = await bot.db.get_guild_settings(guild.id)
    log_id = settings.get("mod_log_channel_id")
    if log_id:
        channel = guild.get_channel(log_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception:
                pass

async def send_mod_notification_dm(user: discord.User, guild: discord.Guild, action: str, reason: str):
    settings = await bot.db.get_guild_settings(guild.id)
    if not settings.get("dm_on_mod", 1):
        return
    embed = discord.Embed(
        title=f"Notification: {action}",
        description=f"You received a moderation action in **{guild.name}**.",
        color=COLOR_MOD,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Action", value=action, inline=True)
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
    embed.set_footer(text=f"Server: {guild.name}")
    try:
        await user.send(embed=embed)
    except Exception:
        pass

# ==========================================
# COMMANDS: 1. ANTI-MENTION SYSTEM
# ==========================================

@bot.group(name="antiping", aliases=["protectping", "guardmention", "antimention"], invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antiping_group(ctx: commands.Context):
    """Manage anti-mention protections for users and roles."""
    prefix = await bot.db.get_prefix(ctx.guild.id)
    embed = discord.Embed(
        title="🛡️ Anti-Mention Protection System",
        description="Prevent unauthorized users from pinging specific users or roles.",
        color=COLOR_PROTECT
    )
    embed.add_field(
        name="Commands",
        value=(
            f"`{prefix}antiping adduser @user [delete/warn/mute/kick] [mute_mins]`\n"
            f"`{prefix}antiping addrole @role [delete/warn/mute/kick] [mute_mins]`\n"
            f"`{prefix}antiping remove @user/@role`\n"
            f"`{prefix}antiping whitelist @protected @allowed`\n"
            f"`{prefix}antiping unwhitelist @protected @allowed`\n"
            f"`{prefix}antiping list`"
        ),
        inline=False
    )
    await ctx.send(embed=embed)

@antiping_group.command(name="adduser")
@commands.has_permissions(administrator=True)
async def antiping_adduser(ctx: commands.Context, user: discord.Member, punishment: str = "delete", mute_minutes: int = 5):
    """Protect a user from unauthorized mentions."""
    punishment = punishment.lower()
    if punishment not in ["delete", "warn", "mute", "kick"]:
        return await ctx.send(f"{EMOJI_ERROR} Choose punishment: `delete`, `warn`, `mute`, `kick`.")
    mute_sec = max(60, mute_minutes * 60)
    await bot.db.add_protected_mention(ctx.guild.id, user.id, "user", punishment, mute_sec)
    await ctx.send(f"{EMOJI_SUCCESS} Anti-Mention protection enabled for {user.mention} (**{punishment.capitalize()}**).")

@antiping_group.command(name="addrole")
@commands.has_permissions(administrator=True)
async def antiping_addrole(ctx: commands.Context, role: discord.Role, punishment: str = "delete", mute_minutes: int = 5):
    """Protect a role from unauthorized mentions."""
    punishment = punishment.lower()
    if punishment not in ["delete", "warn", "mute", "kick"]:
        return await ctx.send(f"{EMOJI_ERROR} Choose punishment: `delete`, `warn`, `mute`, `kick`.")
    mute_sec = max(60, mute_minutes * 60)
    await bot.db.add_protected_mention(ctx.guild.id, role.id, "role", punishment, mute_sec)
    await ctx.send(f"{EMOJI_SUCCESS} Anti-Mention protection enabled for role {role.mention} (**{punishment.capitalize()}**).")

@antiping_group.command(name="remove", aliases=["del"])
@commands.has_permissions(administrator=True)
async def antiping_remove(ctx: commands.Context, target: str):
    """Remove protection from a user or role."""
    clean_id = int(target.replace("<@", "").replace("<@&", "").replace(">", "").replace("!", ""))
    removed = await bot.db.remove_protected_mention(ctx.guild.id, clean_id)
    if removed:
        await ctx.send(f"{EMOJI_SUCCESS} Removed protection for ID `{clean_id}`.")
    else:
        await ctx.send(f"{EMOJI_ERROR} Target `{clean_id}` was not protected.")

@antiping_group.command(name="whitelist")
@commands.has_permissions(administrator=True)
async def antiping_whitelist(ctx: commands.Context, protected_target: str, allowed_target: str):
    """Whitelist a user or role to allow mentioning the protected target."""
    prot_id = int(protected_target.replace("<@", "").replace("<@&", "").replace(">", "").replace("!", ""))
    allow_id = int(allowed_target.replace("<@", "").replace("<@&", "").replace(">", "").replace("!", ""))
    await bot.db.add_mention_whitelist(ctx.guild.id, prot_id, allow_id, "user")
    await ctx.send(f"{EMOJI_SUCCESS} Whitelisted `{allow_id}` to ping protected `{prot_id}`.")

@antiping_group.command(name="unwhitelist")
@commands.has_permissions(administrator=True)
async def antiping_unwhitelist(ctx: commands.Context, protected_target: str, allowed_target: str):
    """Remove whitelist permission."""
    prot_id = int(protected_target.replace("<@", "").replace("<@&", "").replace(">", "").replace("!", ""))
    allow_id = int(allowed_target.replace("<@", "").replace("<@&", "").replace(">", "").replace("!", ""))
    removed = await bot.db.remove_mention_whitelist(ctx.guild.id, prot_id, allow_id)
    await ctx.send(f"{EMOJI_SUCCESS} Removed from whitelist." if removed else f"{EMOJI_ERROR} Not found.")

@antiping_group.command(name="list")
@commands.has_permissions(administrator=True)
async def antiping_list(ctx: commands.Context):
    """List all protected users and roles."""
    protected = await bot.db.get_protected_mentions(ctx.guild.id)
    if not protected:
        return await ctx.send(f"{EMOJI_INFO} No protected users or roles configured.")
    embed = discord.Embed(title="🛡️ Active Protected Mentions", color=COLOR_PROTECT)
    for p in protected:
        tid = p["target_id"]
        name = f"👤 User: <@{tid}>" if p["target_type"] == "user" else f"🎭 Role: <@&{tid}>"
        whitelists = await bot.db.get_mention_whitelists(ctx.guild.id, tid)
        wl_str = ", ".join([f"<@{w}>" for w in whitelists]) if whitelists else "None"
        embed.add_field(name=name, value=f"Punishment: **{p['punishment'].capitalize()}** | Whitelisted: {wl_str}", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# COMMANDS: 2. MODERATION SUITE
# ==========================================

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member from the server."""
    if member.id == ctx.author.id or member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send(f"{EMOJI_ERROR} You cannot ban this user.")
    await send_mod_notification_dm(member, ctx.guild, "Banned", reason)
    await member.ban(reason=f"By {ctx.author} | {reason}", delete_message_days=0)
    embed = discord.Embed(title=f"{EMOJI_HAMMER} Member Banned", description=f"**{member}** has been banned.", color=COLOR_ERROR)
    embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    await ctx.send(embed=embed)
    await log_mod_action(ctx.guild, embed)

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def unban(ctx: commands.Context, user_id: str, *, reason: str = "No reason provided"):
    """Unban a user by ID."""
    clean_id = user_id.replace("<@", "").replace(">", "").replace("!", "")
    banned_user = None
    async for entry in ctx.guild.bans():
        if str(entry.user.id) == clean_id or str(entry.user) == user_id:
            banned_user = entry.user
            break
    if not banned_user:
        return await ctx.send(f"{EMOJI_ERROR} User `{user_id}` not found in ban list.")
    await ctx.guild.unban(banned_user, reason=f"By {ctx.author} | {reason}")
    embed = discord.Embed(title=f"{EMOJI_SUCCESS} Member Unbanned", description=f"**{banned_user}** unbanned.", color=COLOR_SUCCESS)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    await ctx.send(embed=embed)
    await log_mod_action(ctx.guild, embed)

@bot.command(name="softban")
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def softban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Bans and unbans to purge 7 days of messages."""
    await send_mod_notification_dm(member, ctx.guild, "Softbanned (Purged & Kicked)", reason)
    await member.ban(reason=f"Softban by {ctx.author} | {reason}", delete_message_days=7)
    await ctx.guild.unban(member, reason=f"Softban auto-unban by {ctx.author}")
    await ctx.send(f"{EMOJI_SUCCESS} Softbanned **{member}**.")

@bot.command(name="tempban")
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def tempban(ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
    """Temporarily ban a user for a duration (e.g. 10m, 2h, 1d)."""
    seconds = parse_time_duration(duration)
    if seconds <= 0:
        return await ctx.send(f"{EMOJI_ERROR} Invalid duration format (e.g. `30m`, `2h`, `1d`).")
    await send_mod_notification_dm(member, ctx.guild, f"Tempbanned for {duration}", reason)
    await member.ban(reason=f"Tempban ({duration}) by {ctx.author} | {reason}", delete_message_days=0)
    await ctx.send(f"{EMOJI_HAMMER} Tempbanned **{member}** for **{duration}**.")
    async def auto_unban():
        await asyncio.sleep(seconds)
        try:
            await ctx.guild.unban(member, reason=f"Tempban expired ({duration})")
        except Exception:
            pass
    asyncio.create_task(auto_unban())

@bot.command(name="massban")
@commands.has_permissions(administrator=True)
@commands.bot_has_permissions(ban_members=True)
async def massban(ctx: commands.Context, user_ids: commands.Greedy[int], *, reason: str = "Massban"):
    """Ban multiple user IDs at once."""
    if not user_ids:
        return await ctx.send(f"{EMOJI_ERROR} Provide user IDs separated by space.")
    banned = 0
    for uid in user_ids:
        try:
            await ctx.guild.ban(discord.Object(id=uid), reason=f"Massban by {ctx.author} | {reason}", delete_message_days=0)
            banned += 1
        except Exception:
            pass
    await ctx.send(f"{EMOJI_SUCCESS} Massban completed: **{banned}/{len(user_ids)}** users banned.")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member from the server."""
    await send_mod_notification_dm(member, ctx.guild, "Kicked", reason)
    await member.kick(reason=f"By {ctx.author} | {reason}")
    await ctx.send(f"{EMOJI_SUCCESS} Kicked **{member}**.")

@bot.command(name="mute", aliases=["timeout"])
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def mute(ctx: commands.Context, member: discord.Member, duration: str = "10m", *, reason: str = "No reason provided"):
    """Timeout / Mute a member for a given duration (e.g. 5m, 1h, 1d)."""
    sec = parse_time_duration(duration)
    if sec <= 0 or sec > 28 * 86400:
        return await ctx.send(f"{EMOJI_ERROR} Invalid duration! (Max 28 days).")
    await send_mod_notification_dm(member, ctx.guild, f"Muted for {duration}", reason)
    await member.timeout(datetime.timedelta(seconds=sec), reason=f"By {ctx.author} | {reason}")
    await ctx.send(f"{EMOJI_MUTE} Muted **{member}** for **{duration}**.")

@bot.command(name="unmute", aliases=["untimeout"])
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def unmute(ctx: commands.Context, member: discord.Member):
    """Unmute / remove timeout from a member."""
    await member.timeout(None, reason=f"Unmuted by {ctx.author}")
    await ctx.send(f"{EMOJI_SUCCESS} Unmuted **{member}**.")

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Issue a warning to a member."""
    wid = await bot.db.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
    await send_mod_notification_dm(member, ctx.guild, f"Warned (Case #{wid})", reason)
    warns_count = len(await bot.db.get_warnings(ctx.guild.id, member.id))
    await ctx.send(f"{EMOJI_WARN} Warned **{member}** (Case `#{wid}`). Total warnings: **{warns_count}**.")

@bot.command(name="warns", aliases=["warnings"])
@commands.has_permissions(manage_messages=True)
async def warns(ctx: commands.Context, member: discord.Member):
    """List warnings for a member."""
    wlist = await bot.db.get_warnings(ctx.guild.id, member.id)
    if not wlist:
        return await ctx.send(f"{EMOJI_INFO} **{member}** has no warnings.")
    embed = discord.Embed(title=f"⚠️ Warnings for {member}", description=f"Total: **{len(wlist)}**", color=COLOR_WARNING)
    for w in wlist[:10]:
        embed.add_field(name=f"Case #{w['id']}", value=f"**Mod:** <@{w['moderator_id']}>\n**Reason:** {w['reason']}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="delwarn")
@commands.has_permissions(manage_messages=True)
async def delwarn(ctx: commands.Context, warn_id: int):
    """Delete a warning by Case ID."""
    success = await bot.db.delete_warning(ctx.guild.id, warn_id)
    await ctx.send(f"{EMOJI_SUCCESS} Deleted Case `#{warn_id}`." if success else f"{EMOJI_ERROR} Case not found.")

@bot.command(name="clearwarns")
@commands.has_permissions(administrator=True)
async def clearwarns(ctx: commands.Context, member: discord.Member):
    """Clear all warnings for a member."""
    count = await bot.db.clear_warnings(ctx.guild.id, member.id)
    await ctx.send(f"{EMOJI_SUCCESS} Cleared all **{count}** warnings for {member.mention}.")

@bot.command(name="purge", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def purge(ctx: commands.Context, amount: int = 10):
    """Bulk delete messages (1-100)."""
    amount = min(max(1, amount), 100)
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount)
    msg = await ctx.send(f"{EMOJI_SUCCESS} Deleted **{len(deleted)}** messages.")
    await msg.delete(delay=4)

@bot.command(name="purgeuser")
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def purgeuser(ctx: commands.Context, member: discord.Member, amount: int = 20):
    """Bulk delete messages by a specific user."""
    amount = min(max(1, amount), 100)
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount, check=lambda m: m.author.id == member.id)
    msg = await ctx.send(f"{EMOJI_SUCCESS} Deleted **{len(deleted)}** messages from {member.mention}.")
    await msg.delete(delay=4)

@bot.command(name="purgebot")
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def purgebot(ctx: commands.Context, amount: int = 20):
    """Bulk delete bot messages."""
    amount = min(max(1, amount), 100)
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount, check=lambda m: m.author.bot)
    msg = await ctx.send(f"{EMOJI_SUCCESS} Deleted **{len(deleted)}** bot messages.")
    await msg.delete(delay=4)

@bot.command(name="purgelinks")
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def purgelinks(ctx: commands.Context, amount: int = 20):
    """Bulk delete messages containing links."""
    amount = min(max(1, amount), 100)
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount, check=lambda m: bool(LINK_REGEX.search(m.content)))
    msg = await ctx.send(f"{EMOJI_SUCCESS} Deleted **{len(deleted)}** link messages.")
    await msg.delete(delay=4)

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def lock(ctx: commands.Context, channel: discord.TextChannel = None):
    """Lock a channel for @everyone."""
    channel = channel or ctx.channel
    ow = channel.overwrites_for(ctx.guild.default_role)
    ow.send_messages = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
    await channel.send(f"{EMOJI_LOCK} Channel locked.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def unlock(ctx: commands.Context, channel: discord.TextChannel = None):
    """Unlock a channel for @everyone."""
    channel = channel or ctx.channel
    ow = channel.overwrites_for(ctx.guild.default_role)
    ow.send_messages = None
    await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
    await channel.send(f"{EMOJI_UNLOCK} Channel unlocked.")

@bot.command(name="hide")
@commands.has_permissions(manage_channels=True)
async def hide(ctx: commands.Context, channel: discord.TextChannel = None):
    """Hide a channel from @everyone."""
    channel = channel or ctx.channel
    ow = channel.overwrites_for(ctx.guild.default_role)
    ow.view_channel = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
    await ctx.send(f"{EMOJI_SUCCESS} Channel {channel.mention} is now hidden.")

@bot.command(name="unhide")
@commands.has_permissions(manage_channels=True)
async def unhide(ctx: commands.Context, channel: discord.TextChannel = None):
    """Unhide a channel for @everyone."""
    channel = channel or ctx.channel
    ow = channel.overwrites_for(ctx.guild.default_role)
    ow.view_channel = None
    await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
    await ctx.send(f"{EMOJI_SUCCESS} Channel {channel.mention} is now visible.")

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx: commands.Context, seconds: int = 0, channel: discord.TextChannel = None):
    """Set slowmode delay for a channel (0 to disable)."""
    channel = channel or ctx.channel
    await channel.edit(slowmode_delay=seconds)
    await ctx.send(f"{EMOJI_SUCCESS} Slowmode set to **{seconds}s** in {channel.mention}.")

@bot.command(name="setnick", aliases=["nick"])
@commands.has_permissions(manage_nicknames=True)
async def setnick(ctx: commands.Context, member: discord.Member, *, nickname: str = None):
    """Set or reset nickname for a member."""
    await member.edit(nick=nickname)
    await ctx.send(f"{EMOJI_SUCCESS} Updated nickname for {member.mention}.")

@bot.group(name="role", invoke_without_command=True)
@commands.has_permissions(manage_roles=True)
async def role_group(ctx: commands.Context):
    """Manage roles (.role add @user @role, .role remove @user @role)."""
    await ctx.send("Usage: `.role add @user @role` or `.role remove @user @role`")

@role_group.command(name="add")
@commands.has_permissions(manage_roles=True)
async def role_add(ctx: commands.Context, member: discord.Member, role: discord.Role):
    """Add a role to a member."""
    await member.add_roles(role)
    await ctx.send(f"{EMOJI_SUCCESS} Added role {role.mention} to {member.mention}.")

@role_group.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def role_remove(ctx: commands.Context, member: discord.Member, role: discord.Role):
    """Remove a role from a member."""
    await member.remove_roles(role)
    await ctx.send(f"{EMOJI_SUCCESS} Removed role {role.mention} from {member.mention}.")

# ==========================================
# COMMANDS: 3. DIRECT MESSAGING (DMs)
# ==========================================

@bot.command(name="dm", aliases=["senddm", "pm"])
@commands.has_permissions(manage_messages=True)
async def dm_user(ctx: commands.Context, user: discord.User, *, message: str):
    """Send a direct message embed to a user as the bot."""
    embed = discord.Embed(title=f"Message from {ctx.guild.name}", description=message, color=COLOR_PRIMARY, timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"Sent by Staff: {ctx.author}")
    try:
        await user.send(embed=embed)
        await ctx.send(f"{EMOJI_SUCCESS} DM delivered to **{user}**.")
    except Exception as e:
        await ctx.send(f"{EMOJI_ERROR} Could not send DM (user DMs closed or blocked): `{e}`")

@bot.command(name="reply")
@commands.has_permissions(manage_messages=True)
async def reply_dm(ctx: commands.Context, user_id: int, *, response: str):
    """Reply to a user's ModMail / DM."""
    user = bot.get_user(user_id) or await bot.fetch_user(user_id)
    embed = discord.Embed(title=f"Staff Response - {ctx.guild.name}", description=response, color=COLOR_SUCCESS, timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"Responded by: {ctx.author}")
    try:
        await user.send(embed=embed)
        await ctx.send(f"{EMOJI_SUCCESS} Reply sent to **{user}**.")
    except Exception as e:
        await ctx.send(f"{EMOJI_ERROR} Failed to DM user: `{e}`")

@bot.command(name="massdm")
@commands.has_permissions(administrator=True)
async def massdm(ctx: commands.Context, *, message_content: str):
    """Broadcast an official announcement DM to server members."""
    members = [m for m in ctx.guild.members if not m.bot]
    msg = await ctx.send(f"⏳ Sending DM to **{len(members)}** members...")
    sent = 0
    embed = discord.Embed(title=f"📢 Announcement from {ctx.guild.name}", description=message_content, color=COLOR_PRIMARY)
    for m in members:
        try:
            await m.send(embed=embed)
            sent += 1
            await asyncio.sleep(1.2)
        except Exception:
            pass
    await msg.edit(content=f"{EMOJI_SUCCESS} Broadcast finished! Delivered to **{sent}/{len(members)}** members.")

@bot.command(name="toggledm")
@commands.has_permissions(administrator=True)
async def toggledm(ctx: commands.Context):
    """Toggle automated DMs to users upon moderation actions."""
    settings = await bot.db.get_guild_settings(ctx.guild.id)
    new_val = 0 if settings.get("dm_on_mod", 1) else 1
    await bot.db.update_guild_setting(ctx.guild.id, "dm_on_mod", new_val)
    status = "Enabled" if new_val else "Disabled"
    await ctx.send(f"{EMOJI_SUCCESS} Moderation action DMs are now **{status}**.")

# ==========================================
# COMMANDS: 4. AUTOMOD & BADWORDS
# ==========================================

@bot.group(name="automod", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def automod_group(ctx: commands.Context):
    """View AutoMod settings."""
    settings = await bot.db.get_automod(ctx.guild.id)
    embed = discord.Embed(title="🛡️ AutoMod Configuration", color=COLOR_PRIMARY)
    embed.add_field(name="Anti-Spam", value="🟢 On" if settings["anti_spam"] else "🔴 Off", inline=True)
    embed.add_field(name="Anti-Invites", value="🟢 On" if settings["anti_invites"] else "🔴 Off", inline=True)
    embed.add_field(name="Anti-Links", value="🟢 On" if settings["anti_links"] else "🔴 Off", inline=True)
    embed.add_field(name="Anti-Caps", value="🟢 On" if settings["anti_caps"] else "🔴 Off", inline=True)
    embed.add_field(name="Max Mentions", value=str(settings["max_mentions"]), inline=True)
    await ctx.send(embed=embed)

@automod_group.command(name="antispam")
@commands.has_permissions(administrator=True)
async def toggle_antispam(ctx: commands.Context, state: str):
    val = 1 if state.lower() in ["on", "enable", "1"] else 0
    await bot.db.update_automod(ctx.guild.id, "anti_spam", val)
    await ctx.send(f"{EMOJI_SUCCESS} Anti-Spam: **{'Enabled' if val else 'Disabled'}**.")

@automod_group.command(name="antiinvites")
@commands.has_permissions(administrator=True)
async def toggle_antiinvites(ctx: commands.Context, state: str):
    val = 1 if state.lower() in ["on", "enable", "1"] else 0
    await bot.db.update_automod(ctx.guild.id, "anti_invites", val)
    await ctx.send(f"{EMOJI_SUCCESS} Anti-Invites: **{'Enabled' if val else 'Disabled'}**.")

@automod_group.command(name="antilinks")
@commands.has_permissions(administrator=True)
async def toggle_antilinks(ctx: commands.Context, state: str):
    val = 1 if state.lower() in ["on", "enable", "1"] else 0
    await bot.db.update_automod(ctx.guild.id, "anti_links", val)
    await ctx.send(f"{EMOJI_SUCCESS} Anti-Links: **{'Enabled' if val else 'Disabled'}**.")

@automod_group.command(name="anticaps")
@commands.has_permissions(administrator=True)
async def toggle_anticaps(ctx: commands.Context, state: str):
    val = 1 if state.lower() in ["on", "enable", "1"] else 0
    await bot.db.update_automod(ctx.guild.id, "anti_caps", val)
    await ctx.send(f"{EMOJI_SUCCESS} Anti-Caps: **{'Enabled' if val else 'Disabled'}**.")

@automod_group.command(name="maxmentions")
@commands.has_permissions(administrator=True)
async def set_maxmentions(ctx: commands.Context, limit: int):
    await bot.db.update_automod(ctx.guild.id, "max_mentions", max(0, limit))
    await ctx.send(f"{EMOJI_SUCCESS} Max Mentions limit set to **{limit}**.")

@bot.group(name="badwords", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def badwords_group(ctx: commands.Context):
    """Manage blacklisted bad words (.badwords add/remove/list)."""
    await ctx.send("Usage: `.badwords add <word>`, `.badwords remove <word>`, `.badwords list`")

@badwords_group.command(name="add")
@commands.has_permissions(administrator=True)
async def badwords_add(ctx: commands.Context, *, word: str):
    await bot.db.add_bad_word(ctx.guild.id, word)
    await ctx.send(f"{EMOJI_SUCCESS} Added `{word}` to badwords list.")

@badwords_group.command(name="remove", aliases=["del"])
@commands.has_permissions(administrator=True)
async def badwords_remove(ctx: commands.Context, *, word: str):
    removed = await bot.db.remove_bad_word(ctx.guild.id, word)
    await ctx.send(f"{EMOJI_SUCCESS} Removed `{word}`." if removed else f"{EMOJI_ERROR} Not in list.")

@badwords_group.command(name="list")
@commands.has_permissions(administrator=True)
async def badwords_list(ctx: commands.Context):
    words = await bot.db.get_bad_words(ctx.guild.id)
    if not words:
        return await ctx.send(f"{EMOJI_INFO} No bad words blacklisted.")
    await ctx.send(f"🚫 **Blacklisted Words:** {', '.join([f'`{w}`' for w in words])}")

# ==========================================
# COMMANDS: 5. TICKETS
# ==========================================

@bot.group(name="ticket", invoke_without_command=True)
async def ticket_group(ctx: commands.Context):
    """Ticket system management (.ticket panel, .ticket close, .ticket transcript)."""
    prefix = await bot.db.get_prefix(ctx.guild.id)
    await ctx.send(f"Usage: `{prefix}ticket panel`, `{prefix}ticket category <cat_id>`, `{prefix}ticket close`, `{prefix}ticket transcript`")

@ticket_group.command(name="panel")
@commands.has_permissions(administrator=True)
async def ticket_panel(ctx: commands.Context, channel: discord.TextChannel = None):
    """Deploy the interactive Ticket Button panel."""
    channel = channel or ctx.channel
    embed = discord.Embed(title="📩 Need Support?", description="Click the button below to open a private ticket with our staff.", color=COLOR_PRIMARY)
    await channel.send(embed=embed, view=TicketPanelView(bot))
    await ctx.send(f"{EMOJI_SUCCESS} Ticket panel sent to {channel.mention}.")

@ticket_group.command(name="category")
@commands.has_permissions(administrator=True)
async def ticket_category(ctx: commands.Context, category: discord.CategoryChannel):
    """Set parent category for ticket channels."""
    await bot.db.update_guild_setting(ctx.guild.id, "ticket_category_id", category.id)
    await ctx.send(f"{EMOJI_SUCCESS} Ticket category set to **{category.name}**.")

@ticket_group.command(name="close")
async def ticket_close(ctx: commands.Context):
    """Close and delete the current ticket."""
    t_data = await bot.db.get_ticket(ctx.channel.id)
    if not t_data and not ctx.channel.name.startswith("ticket-"):
        return await ctx.send(f"{EMOJI_ERROR} This is not an active ticket channel.")
    await bot.db.close_ticket(ctx.channel.id)
    await ctx.send("🔒 Closing ticket in 5 seconds...")
    await asyncio.sleep(5)
    await ctx.channel.delete()

@ticket_group.command(name="transcript")
async def ticket_transcript(ctx: commands.Context):
    """Export a text transcript file of the ticket channel."""
    messages = []
    async for m in ctx.channel.history(limit=500, oldest_first=True):
        messages.append(f"[{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {m.author}: {m.content}")
    file_data = io.BytesIO("\n".join(messages).encode("utf-8"))
    await ctx.send(file=discord.File(file_data, filename=f"transcript-{ctx.channel.name}.txt"))

# ==========================================
# COMMANDS: 6. SERVER MANAGEMENT & SETTINGS
# ==========================================

@bot.command(name="setprefix")
@commands.has_permissions(administrator=True)
async def setprefix(ctx: commands.Context, new_prefix: str):
    """Set custom prefix for this server."""
    await bot.db.set_prefix(ctx.guild.id, new_prefix[:5])
    await ctx.send(f"{EMOJI_SUCCESS} Server prefix updated to: `{new_prefix}`")

@bot.command(name="setmodlog")
@commands.has_permissions(administrator=True)
async def setmodlog(ctx: commands.Context, channel: discord.TextChannel):
    """Set the moderation log channel."""
    await bot.db.update_guild_setting(ctx.guild.id, "mod_log_channel_id", channel.id)
    await ctx.send(f"{EMOJI_SUCCESS} Mod logs will be sent to {channel.mention}.")

@bot.command(name="setmodmail")
@commands.has_permissions(administrator=True)
async def setmodmail(ctx: commands.Context, channel: discord.TextChannel):
    """Set the channel where incoming DM ModMail messages arrive."""
    await bot.db.update_guild_setting(ctx.guild.id, "modmail_channel_id", channel.id)
    await ctx.send(f"{EMOJI_SUCCESS} ModMail routed to {channel.mention}.")

@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome(ctx: commands.Context, channel: discord.TextChannel):
    """Set welcome greetings channel."""
    await bot.db.update_guild_setting(ctx.guild.id, "welcome_channel_id", channel.id)
    await ctx.send(f"{EMOJI_SUCCESS} Welcome messages set to {channel.mention}.")

@bot.command(name="welcomemsg")
@commands.has_permissions(administrator=True)
async def welcomemsg(ctx: commands.Context, *, message: str):
    """Set custom welcome message (Variables: {user}, {server}, {members})."""
    await bot.db.update_guild_setting(ctx.guild.id, "welcome_message", message)
    await ctx.send(f"{EMOJI_SUCCESS} Welcome message updated.")

@bot.command(name="setleave")
@commands.has_permissions(administrator=True)
async def setleave(ctx: commands.Context, channel: discord.TextChannel):
    """Set leave goodbye channel."""
    await bot.db.update_guild_setting(ctx.guild.id, "leave_channel_id", channel.id)
    await ctx.send(f"{EMOJI_SUCCESS} Leave messages set to {channel.mention}.")

@bot.command(name="leavemsg")
@commands.has_permissions(administrator=True)
async def leavemsg(ctx: commands.Context, *, message: str):
    """Set custom leave message."""
    await bot.db.update_guild_setting(ctx.guild.id, "leave_message", message)
    await ctx.send(f"{EMOJI_SUCCESS} Leave message updated.")

@bot.command(name="setautorole")
@commands.has_permissions(administrator=True)
async def setautorole(ctx: commands.Context, role: discord.Role):
    """Set role given to new members automatically."""
    await bot.db.update_guild_setting(ctx.guild.id, "autorole_id", role.id)
    await ctx.send(f"{EMOJI_SUCCESS} AutoRole set to {role.mention}.")

@bot.command(name="disableautorole")
@commands.has_permissions(administrator=True)
async def disableautorole(ctx: commands.Context):
    """Disable AutoRole."""
    await bot.db.update_guild_setting(ctx.guild.id, "autorole_id", 0)
    await ctx.send(f"{EMOJI_SUCCESS} AutoRole disabled.")

@bot.command(name="settings")
@commands.has_permissions(administrator=True)
async def settings(ctx: commands.Context):
    """Display server configuration overview."""
    s = await bot.db.get_guild_settings(ctx.guild.id)
    embed = discord.Embed(title=f"⚙️ Settings - {ctx.guild.name}", color=COLOR_PRIMARY)
    embed.add_field(name="Prefix", value=f"`{s['prefix']}`", inline=True)
    embed.add_field(name="Mod Logs", value=f"<#{s['mod_log_channel_id']}>" if s['mod_log_channel_id'] else "Not set", inline=True)
    embed.add_field(name="ModMail", value=f"<#{s['modmail_channel_id']}>" if s['modmail_channel_id'] else "Not set", inline=True)
    embed.add_field(name="Welcome Channel", value=f"<#{s['welcome_channel_id']}>" if s['welcome_channel_id'] else "Not set", inline=True)
    embed.add_field(name="Leave Channel", value=f"<#{s['leave_channel_id']}>" if s['leave_channel_id'] else "Not set", inline=True)
    embed.add_field(name="AutoRole", value=f"<@&{s['autorole_id']}>" if s['autorole_id'] else "Disabled", inline=True)
    await ctx.send(embed=embed)

# ==========================================
# COMMANDS: 7. UTILITY & LOOKUPS
# ==========================================

@bot.command(name="ping")
async def ping(ctx: commands.Context):
    """Check bot latency."""
    await ctx.send(f"🏓 Pong! Latency: **{round(bot.latency * 1000)}ms**")

@bot.command(name="uptime")
async def uptime(ctx: commands.Context):
    """Check how long the bot has been running."""
    up_str = str(datetime.timedelta(seconds=int(time.time() - bot.start_time)))
    await ctx.send(f"⏱️ Uptime: **{up_str}**")

@bot.command(name="botinfo")
async def botinfo(ctx: commands.Context):
    """Show overall bot info and statistics."""
    total_users = sum(g.member_count for g in bot.guilds)
    embed = discord.Embed(title="🤖 Bot Information", color=COLOR_PRIMARY)
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="Users", value=f"{total_users:,}", inline=True)
    embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.set_footer(text="Hosted 24/7 on Railway")
    await ctx.send(embed=embed)

@bot.command(name="userinfo", aliases=["user", "whois"])
async def userinfo(ctx: commands.Context, member: discord.Member = None):
    """Lookup details about a user."""
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 User Info: {member}", color=COLOR_PRIMARY)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo", aliases=["server"])
async def serverinfo(ctx: commands.Context):
    """Lookup server statistics."""
    guild = ctx.guild
    embed = discord.Embed(title=f"🏰 Server Info: {guild.name}", color=COLOR_PRIMARY)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="Members", value=f"👥 {guild.member_count}", inline=True)
    embed.add_field(name="Channels", value=f"💬 {len(guild.text_channels)} text | 🔊 {len(guild.voice_channels)} voice", inline=True)
    embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="avatar", aliases=["av", "pfp"])
async def avatar(ctx: commands.Context, member: discord.Member = None):
    """View a member's avatar."""
    member = member or ctx.author
    embed = discord.Embed(title=f"🖼️ Avatar of {member}", color=COLOR_PRIMARY)
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="banner")
async def banner(ctx: commands.Context, user: discord.User = None):
    """View a user's banner."""
    user = user or ctx.author
    fetched = await bot.fetch_user(user.id)
    if not fetched.banner:
        return await ctx.send(f"{EMOJI_INFO} **{user}** does not have a banner.")
    embed = discord.Embed(title=f"🎨 Banner of {user}", color=COLOR_PRIMARY)
    embed.set_image(url=fetched.banner.url)
    await ctx.send(embed=embed)

@bot.command(name="roleinfo")
async def roleinfo(ctx: commands.Context, role: discord.Role):
    """View details about a role."""
    embed = discord.Embed(title=f"🎭 Role Info: {role.name}", color=role.color)
    embed.add_field(name="ID", value=f"`{role.id}`", inline=True)
    embed.add_field(name="Members", value=str(len(role.members)), inline=True)
    embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="channelinfo")
async def channelinfo(ctx: commands.Context, channel: discord.TextChannel = None):
    """View details about a channel."""
    channel = channel or ctx.channel
    embed = discord.Embed(title=f"💬 Channel Info: #{channel.name}", color=COLOR_PRIMARY)
    embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
    embed.add_field(name="Slowmode", value=f"{channel.slowmode_delay}s", inline=True)
    embed.add_field(name="NSFW", value="Yes" if channel.is_nsfw() else "No", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="id")
async def get_id(ctx: commands.Context, target: str = None):
    """Get Snowflake ID of yourself, user, channel, or role."""
    if not target:
        return await ctx.send(f"Your ID: `{ctx.author.id}`")
    clean = target.replace("<@", "").replace("<#", "").replace("<@&", "").replace(">", "").replace("!", "")
    await ctx.send(f"ID for {target}: `{clean}`")

@bot.command(name="calc")
async def calc(ctx: commands.Context, *, expression: str):
    """Safely calculate basic math (e.g. .calc 25 * 4 + 10)."""
    try:
        res = safe_eval(expression)
        await ctx.send(f"🧮 Result: **{res}**")
    except Exception as e:
        await ctx.send(f"{EMOJI_ERROR} Calculation error: `{e}`")

@bot.command(name="qrcode", aliases=["qr"])
async def qrcode(ctx: commands.Context, *, text_or_url: str):
    """Generate a QR Code image."""
    enc = urllib.parse.quote(text_or_url)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={enc}"
    embed = discord.Embed(title="📱 QR Code", color=COLOR_PRIMARY)
    embed.set_image(url=qr_url)
    await ctx.send(embed=embed)

@bot.command(name="reminder", aliases=["remindme", "timer"])
async def reminder(ctx: commands.Context, duration: str, *, reminder_text: str):
    """Set a reminder (e.g. .reminder 10m Check food)."""
    sec = parse_time_duration(duration)
    if sec <= 0:
        return await ctx.send(f"{EMOJI_ERROR} Invalid duration (e.g. `10m`, `1h`, `1d`).")
    remind_at = time.time() + sec
    await bot.db.add_reminder(ctx.author.id, ctx.channel.id, reminder_text, remind_at)
    await ctx.send(f"{EMOJI_SUCCESS} I will remind you about **{reminder_text}** in **{duration}**!")

@bot.command(name="poll")
async def poll(ctx: commands.Context, *, question: str):
    """Create a community poll."""
    embed = discord.Embed(title="📊 Poll", description=question, color=COLOR_PRIMARY)
    embed.set_footer(text=f"By {ctx.author}")
    m = await ctx.send(embed=embed)
    await m.add_reaction("👍")
    await m.add_reaction("👎")

@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def custom_embed(ctx: commands.Context, *, args: str):
    """Create a custom embed. Format: .embed Title | Description | Optional Hex"""
    parts = [p.strip() for p in args.split("|")]
    title = parts[0]
    desc = parts[1] if len(parts) > 1 else ""
    color = COLOR_PRIMARY
    if len(parts) > 2:
        try:
            color = int(parts[2].replace("#", ""), 16)
        except ValueError:
            pass
    embed = discord.Embed(title=title, description=desc, color=color)
    await ctx.send(embed=embed)

# ==========================================
# COMMANDS: 8. FUN & GAMES
# ==========================================

@bot.command(name="8ball")
async def eight_ball(ctx: commands.Context, *, question: str):
    """Ask Magic 8-Ball."""
    await ctx.send(f"🎱 **{random.choice(EIGHT_BALL_RESPONSES)}**")

@bot.command(name="coinflip", aliases=["flip"])
async def coinflip(ctx: commands.Context):
    """Flip a coin."""
    await ctx.send(f"🪙 Landed on: **{random.choice(['Heads', 'Tails'])}**!")

@bot.command(name="dice")
async def dice(ctx: commands.Context, sides: int = 6):
    """Roll a die."""
    await ctx.send(f"🎲 Rolled a D{sides}: **{random.randint(1, max(2, sides))}**")

@bot.command(name="roll")
async def roll(ctx: commands.Context, min_val: int = 1, max_val: int = 100):
    """Roll a random number."""
    if min_val >= max_val:
        min_val, max_val = 1, max(100, min_val)
    await ctx.send(f"🎲 Random number: **{random.randint(min_val, max_val)}**")

@bot.command(name="meme")
async def meme(ctx: commands.Context):
    """Get a fresh meme from Reddit."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://meme-api.com/gimme") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title=data.get("title", "Meme"), color=COLOR_PRIMARY)
                    embed.set_image(url=data.get("url"))
                    return await ctx.send(embed=embed)
        except Exception:
            pass
    await ctx.send("❌ Could not fetch meme right now.")

@bot.command(name="joke")
async def joke(ctx: commands.Context):
    """Get a funny joke."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://official-joke-api.appspot.com/random_joke") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return await ctx.send(f"😂 **{data.get('setup')}**\n||{data.get('punchline')}||")
        except Exception:
            pass
    await ctx.send("Why do we tell actors to 'break a leg'? Because every play has a cast!")

@bot.command(name="roast")
async def roast(ctx: commands.Context, member: discord.Member = None):
    """Roast someone."""
    member = member or ctx.author
    await ctx.send(f"{member.mention}, {random.choice(ROASTS)}")

@bot.command(name="rps")
async def rps(ctx: commands.Context, choice: str):
    """Play Rock Paper Scissors."""
    valid = ["rock", "paper", "scissors"]
    uc = choice.lower()
    if uc not in valid:
        return await ctx.send("Choose: `rock`, `paper`, or `scissors`.")
    bc = random.choice(valid)
    if uc == bc:
        res = "It's a tie!"
    elif (uc == "rock" and bc == "scissors") or (uc == "paper" and bc == "rock") or (uc == "scissors" and bc == "paper"):
        res = "You won! 🎉"
    else:
        res = "I won! 🤖"
    await ctx.send(f"You chose **{uc}**, I chose **{bc}**. **{res}**")

@bot.command(name="ship")
async def ship(ctx: commands.Context, user1: discord.Member, user2: discord.Member = None):
    """Calculate love compatibility."""
    user2 = user2 or ctx.author
    pct = (user1.id + user2.id) % 101
    await ctx.send(f"💘 Love compatibility between **{user1.name}** and **{user2.name}**: **{pct}%**!")

@bot.command(name="fact")
async def fact(ctx: commands.Context):
    """Random interesting fact."""
    await ctx.send(f"💡 **Fact:** {random.choice(FACTS)}")

@bot.command(name="choose")
async def choose(ctx: commands.Context, *, options: str):
    """Pick randomly from comma separated choices."""
    opts = [o.strip() for o in options.split(",") if o.strip()]
    if len(opts) < 2:
        return await ctx.send("Give at least 2 choices separated by commas.")
    await ctx.send(f"🤔 I choose: **{random.choice(opts)}**!")

@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx: commands.Context, *, text: str):
    """Repeat text and delete author message."""
    await ctx.message.delete()
    await ctx.send(text)

@bot.command(name="slap")
async def slap(ctx: commands.Context, member: discord.Member):
    await ctx.send(f"✋ {ctx.author.mention} slapped {member.mention}!")

@bot.command(name="hug")
async def hug(ctx: commands.Context, member: discord.Member):
    await ctx.send(f"🤗 {ctx.author.mention} gave {member.mention} a warm hug!")

@bot.command(name="pat")
async def pat(ctx: commands.Context, member: discord.Member):
    await ctx.send(f"👋 {ctx.author.mention} patted {member.mention} on the head.")

@bot.command(name="rate")
async def rate(ctx: commands.Context, *, thing: str):
    await ctx.send(f"⭐ I rate **{thing}** a **{random.randint(0, 10)}/10**!")

@bot.command(name="reverse")
async def reverse(ctx: commands.Context, *, text: str):
    await ctx.send(text[::-1])

# ==========================================
# COMMANDS: 9. ECONOMY & LEVELING
# ==========================================

@bot.command(name="balance", aliases=["bal", "money"])
async def balance(ctx: commands.Context, member: discord.Member = None):
    """Check coin balance."""
    member = member or ctx.author
    eco = await bot.db.get_economy(ctx.guild.id, member.id)
    embed = discord.Embed(title=f"💰 Balance - {member.name}", color=COLOR_SUCCESS)
    embed.add_field(name="Wallet", value=f"🪙 {eco['balance']:,}", inline=True)
    embed.add_field(name="Bank", value=f"🪙 {eco['bank']:,}", inline=True)
    embed.add_field(name="Total", value=f"🪙 {eco['balance'] + eco['bank']:,}", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="daily")
async def daily(ctx: commands.Context):
    """Claim daily 250 coins."""
    success, res = await bot.db.claim_daily(ctx.guild.id, ctx.author.id, reward=250)
    if success:
        await ctx.send(f"🎁 You claimed your daily reward of **🪙 {res:,} coins**!")
    else:
        h, m = res // 3600, (res % 3600) // 60
        await ctx.send(f"⏳ Daily reward already claimed! Wait **{h}h {m}m**.")

@bot.command(name="deposit", aliases=["dep"])
async def deposit(ctx: commands.Context, amount: str):
    """Deposit coins to bank."""
    eco = await bot.db.get_economy(ctx.guild.id, ctx.author.id)
    amt = eco["balance"] if amount.lower() == "all" else int(amount)
    if amt <= 0 or amt > eco["balance"]:
        return await ctx.send(f"{EMOJI_ERROR} Invalid deposit amount.")
    await bot.db.update_balance(ctx.guild.id, ctx.author.id, -amt, in_bank=False)
    await bot.db.update_balance(ctx.guild.id, ctx.author.id, amt, in_bank=True)
    await ctx.send(f"{EMOJI_SUCCESS} Deposited **🪙 {amt:,} coins** to bank.")

@bot.command(name="withdraw", aliases=["with"])
async def withdraw(ctx: commands.Context, amount: str):
    """Withdraw coins from bank."""
    eco = await bot.db.get_economy(ctx.guild.id, ctx.author.id)
    amt = eco["bank"] if amount.lower() == "all" else int(amount)
    if amt <= 0 or amt > eco["bank"]:
        return await ctx.send(f"{EMOJI_ERROR} Invalid withdraw amount.")
    await bot.db.update_balance(ctx.guild.id, ctx.author.id, -amt, in_bank=True)
    await bot.db.update_balance(ctx.guild.id, ctx.author.id, amt, in_bank=False)
    await ctx.send(f"{EMOJI_SUCCESS} Withdrew **🪙 {amt:,} coins** to wallet.")

@bot.command(name="pay", aliases=["give"])
async def pay(ctx: commands.Context, recipient: discord.Member, amount: int):
    """Transfer coins to another member."""
    if recipient.bot or recipient.id == ctx.author.id or amount <= 0:
        return await ctx.send(f"{EMOJI_ERROR} Invalid transaction.")
    eco = await bot.db.get_economy(ctx.guild.id, ctx.author.id)
    if eco["balance"] < amount:
        return await ctx.send(f"{EMOJI_ERROR} Not enough coins in wallet.")
    await bot.db.update_balance(ctx.guild.id, ctx.author.id, -amount, in_bank=False)
    await bot.db.update_balance(ctx.guild.id, recipient.id, amount, in_bank=False)
    await ctx.send(f"{EMOJI_SUCCESS} Sent **🪙 {amount:,} coins** to {recipient.mention}.")

@bot.command(name="ecotop")
async def ecotop(ctx: commands.Context):
    """Richest members leaderboard."""
    top = await bot.db.get_economy_leaderboard(ctx.guild.id, limit=10)
    embed = discord.Embed(title="🏆 Richest Members", color=COLOR_WARNING)
    for i, r in enumerate(top, 1):
        embed.add_field(name=f"#{i} | <@{r['user_id']}>", value=f"🪙 **{r['total']:,} coins**", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="rank", aliases=["level", "lvl"])
async def rank(ctx: commands.Context, member: discord.Member = None):
    """Check chat level and XP."""
    member = member or ctx.author
    lvl_data = await bot.db.get_user_level(ctx.guild.id, member.id)
    embed = discord.Embed(title=f"⭐ Rank: {member.name}", color=COLOR_PRIMARY)
    embed.add_field(name="Level", value=f"**Level {lvl_data['level']}**", inline=True)
    embed.add_field(name="XP", value=f"**{lvl_data['xp']:,} XP**", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="xptop")
async def xptop(ctx: commands.Context):
    """Highest level members leaderboard."""
    top = await bot.db.get_level_leaderboard(ctx.guild.id, limit=10)
    embed = discord.Embed(title="🏆 XP & Level Leaderboard", color=COLOR_PRIMARY)
    for i, r in enumerate(top, 1):
        embed.add_field(name=f"#{i} | <@{r['user_id']}>", value=f"Level **{r['level']}** ({r['xp']:,} XP)", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# ADMIN & RUN
# ==========================================

@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx: commands.Context):
    """Sync global slash application commands."""
    synced = await bot.tree.sync()
    await ctx.send(f"{EMOJI_SUCCESS} Synced **{len(synced)}** commands globally.")

async def main():
    if not DISCORD_TOKEN or DISCORD_TOKEN == "your_bot_token_here":
        print("❌ ERROR: DISCORD_TOKEN is missing! Set it in Railway variables or .env file.")
        sys.exit(1)
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped.")
