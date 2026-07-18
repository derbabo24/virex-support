import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import re
import random
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread
import asyncpg
import json
# ─── CONFIG ───────────────────────────────────────────────────────────────────
PREFIX = "$"
SILENT_PREFIX = "*"
BAN_REQUEST_CHANNEL_ID = int(os.environ.get("BAN_REQUEST_CHANNEL_ID", 0))
ADMIN_ROLE_NAME = os.environ.get("ADMIN_ROLE_NAME", "Blacklist")  # Rolle, die Ban-Requests approven/denyen darf
STAFF_ROLE_NAME = "Trial Staff (not trusted)"
BLACKLIST_ADMIN_ROLE = "Blacklist"
APPROVE_CHANNEL_ID = 1504531328731709540
POST_CHANNEL_ID = 1502194708993146921
CHANGELOG_CHANNEL_ID = 1524959757499371620
CUSTOMER_ROLE_NAME = "customer"
MESSAGE_LOG_CHANNEL_ID = 1524959786871820309
VOUCH_CHANNEL_ID = 1502194368059146290
WEBSITE_URL = "https://vireex.cc"
R6_GUIDE_URL = "https://vireex.cc/guide"
# ─── DATABASE CONFIG ──────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL")
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
# ─── VOUCH COUNTER ────────────────────────────────────────────────────────────
vouch_counter: int = 1
# ─── BOT SETUP ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)
active_giveaways: dict = {}
db_pool: asyncpg.Pool = None
# ─── IN-MEMORY WHITELIST CACHE ────────────────────────────────────────────────
# Loaded from DB on startup — avoids a DB query on every single message
whitelist_cache: set[int] = set()
# ─── HTTP SERVER ──────────────────────────────────────────────────────────────
app = Flask(__name__)
@app.route('/guide')
def serve_guide():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()
def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False)
# ─── DATABASE HELPERS ─────────────────────────────────────────────────────────
async def init_db():
    global db_pool
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not set!")
        return False
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60,
            ssl='require'
        )
        async with db_pool.acquire() as conn:
            # Blacklist table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    user_id BIGINT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    blacklisted_by BIGINT NOT NULL,
                    blacklisted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    guild_id BIGINT NOT NULL
                )
            ''')
            # ── Whitelist table ──────────────────────────────────────────────
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS whitelist (
                    user_id BIGINT PRIMARY KEY,
                    whitelisted_by BIGINT NOT NULL,
                    whitelisted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    guild_id BIGINT NOT NULL
                )
            ''')
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
# ── Blacklist DB helpers ───────────────────────────────────────────────────────
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
# ── Whitelist DB helpers ───────────────────────────────────────────────────────
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
# ─── HELPERS ──────────────────────────────────────────────────────────────────
def utcnow() -> datetime:
    return datetime.now(timezone.utc)
def has_staff_role(user: discord.Member) -> bool:
    return STAFF_ROLE_NAME.lower() in [r.name.lower() for r in user.roles]
def has_blacklist_admin_role(user: discord.Member) -> bool:
    return BLACKLIST_ADMIN_ROLE.lower() in [r.name.lower() for r in user.roles]
def has_admin_role(user: discord.Member) -> bool:
    """Rolle, die Ban-Requests approven/denyen darf (aus Railway-Variable)."""
    return ADMIN_ROLE_NAME.lower() in [r.name.lower() for r in user.roles]
def has_customer_role(user: discord.Member) -> bool:
    return CUSTOMER_ROLE_NAME.lower() in [r.name.lower() for r in user.roles]
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
        for name, status in chunk:
            dot = STATUS_DOTS.get(status, "⚫")
            field_value += f"{dot} **{name}**\n`{status}`\n\n"
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
    if not has_staff_role(ctx.author):
        embed = discord.Embed(title="❌ No Permission", description=f"You need at least the **{STAFF_ROLE_NAME}** role to use this command.", color=0xFF4444)
        await ctx.send(embed=embed, delete_after=5)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        return False
    return True
async def blacklist_admin_check(ctx) -> bool:
    if not has_blacklist_admin_role(ctx.author):
        embed = discord.Embed(title="❌ No Permission", description=f"You need the **{BLACKLIST_ADMIN_ROLE}** role to use this command.", color=0xFF4444)
        await ctx.send(embed=embed, delete_after=5)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
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
# ─── BAN REQUEST VIEW (persistent — survives bot restarts) ────────────────────
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
# ─── EVENTS ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    global vouch_counter, whitelist_cache
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="vireex.cc | $manual"))
    # Load whitelist from database into memory
    whitelist_cache = await db_load_whitelist()
    print(f"✅ Whitelist cache loaded: {len(whitelist_cache)} user(s)")
    # Persistent view for ban request buttons (works after restarts)
    bot.add_view(BanRequestView())
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    if not hasattr(bot, 'flask_started'):
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        bot.flask_started = True
        print("✅ Flask HTTP server started on port 8080")
@bot.event
async def on_member_join(member: discord.Member):
    if await is_blacklisted(member.id):
        try:
            blacklist_entry = await get_blacklist_entry(member.id)
            await member.ban(reason=f"Blacklisted: {blacklist_entry['reason']}")
            log_channel = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(title="🔨 Auto-Ban — Blacklist", color=0xFF0000, timestamp=utcnow())
                embed.add_field(name="👤 User", value=f"{member} (`{member.id}`)", inline=False)
                embed.add_field(name="📝 Reason", value=blacklist_entry['reason'], inline=False)
                embed.set_footer(text="Auto-banned on join")
                await log_channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Error auto-banning {member.id}: {e}")
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.content.startswith(SILENT_PREFIX):
        if not has_staff_role(message.author):
            return
        content = message.content[len(SILENT_PREFIX):].strip()
        try:
            await message.delete()
        except discord.Forbidden:
            pass
        if content:
            await message.channel.send(content)
        return
    is_staff      = has_staff_role(message.author)
    # ── Whitelist check: whitelisted users bypass the word filter completely ──
    is_whitelisted = message.author.id in whitelist_cache
    if not is_staff and not is_whitelisted:
        matched = check_blacklist(message.content)
        if matched:
            try:
                await message.delete()
            except discord.Forbidden:
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
    await bot.process_commands(message)
# ─── PREFIX COMMANDS ──────────────────────────────────────────────────────────
@bot.command(name="commands")
async def commands_list(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except discord.Forbidden:
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
        name="⚡ Slash Commands (`/`)",
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
            "`/r6guide` — Vega R6 setup guide"
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
    except discord.Forbidden:
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
    except discord.Forbidden:
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
    except discord.Forbidden:
        pass
    records = await get_blacklist(ctx.guild.id)
    if not records:
        await ctx.send(embed=discord.Embed(title="📋 Blacklist", description="No users are currently blacklisted.", color=0x57F287))
        return
    embeds = []
    items_per_page = 5
    for i in range(0, len(records), items_per_page):
        chunk = records[i:i+items_per_page]
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
# ─── OTHER PREFIX COMMANDS ────────────────────────────────────────────────────
@bot.command(name="manual")
async def manual(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except discord.Forbidden:
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
    except discord.Forbidden:
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
    except discord.Forbidden:
        pass
    embed = discord.Embed(title="🪟 Windows Activation Guide", description="Follow the steps below to activate Windows.", color=0x00B4D8)
    embed.add_field(name="1️⃣ Open PowerShell as Administrator", value="Press Windows → type `PowerShell` → Run as Administrator", inline=False)
    embed.add_field(name="2️⃣ Run this command", value="```irm https://get.activated.win/ | iex```", inline=False)
    embed.add_field(name="3️⃣ Press `4`", value="", inline=True)
    embed.add_field(name="4️⃣ Activate Windows → `1`", value="", inline=True)
    embed.add_field(name="5️⃣ Auto-Renewal → `5`", value="", inline=True)
    embed.set_footer(text="Virex Team")
    await ctx.send(embed=embed)
@bot.command(name="tempvsperm")
async def tempvsperm(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except discord.Forbidden:
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
    except discord.Forbidden:
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
    except discord.Forbidden:
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
        await ctx.send(embed=discord.Embed(title="✅ Ban Request Sent", description=f"Request sent to {ban_channel.mention} — admins can now approve or deny it.", color=0x00FF00), delete_after=5)
    else:
        await ctx.send("❌ Ban request channel not found. Set `BAN_REQUEST_CHANNEL_ID` in Railway variables.", delete_after=5)
@bot.command(name="scam")
async def scam(ctx):
    if not await staff_check(ctx):
        return
    try:
        await ctx.message.delete()
    except discord.Forbidden:
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
    except discord.Forbidden:
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
# ─── APPROVE VIEW ─────────────────────────────────────────────────────────────
class ApproveView(discord.ui.View):
    def __init__(self, link: str, author: discord.Member):
        super().__init__(timeout=300)
        self.link   = link
        self.author = author
    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_staff_role(interaction.user):
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
        if not has_staff_role(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to deny posts.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("🚫 Post denied.", ephemeral=True)
# ─── SLASH COMMANDS ───────────────────────────────────────────────────────────
@bot.tree.command(name="post", description="Submit a video for approval")
@app_commands.describe(link="Video link to submit")
async def post(interaction: discord.Interaction, link: str):
    if not has_staff_role(interaction.user):
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
    if not has_staff_role(interaction.user):
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
@bot.tree.command(name="r6guide", description="Shows the Vega R6 setup guide")
async def r6guide(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Vega R6 — Setup Guide",
        description=f"**[🔗 Click here to open the full guide]({R6_GUIDE_URL})**",
        color=0x0A84FF
    )
    embed.set_footer(text="Virex Team • vireex.cc")
    await interaction.response.send_message(embed=embed)
# ─── STATUS COMMANDS ──────────────────────────────────────────────────────────
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
    if not has_staff_role(interaction.user):
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
    if not has_staff_role(interaction.user):
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
    if not has_staff_role(interaction.user):
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
        embed.add_field(name="👤 User",      value=f"{member} (`{member.id}`)", inline=True)
        embed.add_field(name="🛡️ Removed By", value=f"{interaction.user}",      inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Virex — Whitelist")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Database error. Failed to remove user from whitelist.", ephemeral=True)
@bot.tree.command(name="whitelistview", description="Show all whitelisted users (Staff only)")
async def cmd_whitelistview(interaction: discord.Interaction):
    if not has_staff_role(interaction.user):
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
            user_display = f"Unknown"
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
    embed.add_field(name="Stars",   value=star_display, inline=False)
    embed.add_field(name="Vouch:",  value=message,      inline=False)
    embed.add_field(name="Vouch N°:", value=str(vouch_num), inline=True)
    embed.add_field(name="Vouched at:", value=now.strftime("%A, %B %d, %Y %I:%M %p"), inline=True)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text=f"Vouched by {interaction.user} • Virex Team")
    await vouch_channel.send(content=f"Vouched by: {interaction.user.mention}", embed=embed)
    await interaction.response.send_message("✅ Your vouch has been submitted, thank you!", ephemeral=True)
# ─── GIVEAWAY VIEW ────────────────────────────────────────────────────────────
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
            embed = build_giveaway_embed(data["prize"], data["winners"], data["host_id"], data["ends_at"], len(data["entries"]), data.get("requirements"))
            await interaction.message.edit(embed=embed)
        except Exception:
            pass
# ─── GIVEAWAY SLASH COMMANDS ──────────────────────────────────────────────────
@bot.tree.command(name="giveaway", description="Start a giveaway")
@app_commands.describe(duration="Duration e.g. 10m, 2h, 1d", winners="Number of winners", prize="What is being given away?", requirements="Optional requirements to enter")
async def giveaway_start(interaction: discord.Interaction, duration: str, winners: int, prize: str, requirements: str = None):
    if not has_staff_role(interaction.user):
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
    if not has_staff_role(interaction.user):
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
    if not has_staff_role(interaction.user):
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
# ─── ERROR HANDLING ───────────────────────────────────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing arguments.", delete_after=5)
        return
    print(f"[ERROR] {error}")
# ─── START ────────────────────────────────────────────────────────────────────
async def main():
    TOKEN = os.environ.get("DISCORD_TOKEN")
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
