import asyncio
import os
import sys
import discord
from discord.ext import commands
import config
from database import Database

# Ensure UTF-8 stdout across Windows & Linux
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Create custom Help Command
class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        ctx = self.context
        prefix = await ctx.bot.db.get_prefix(ctx.guild.id if ctx.guild else None)

        embed = discord.Embed(
            title="🛡️ Bot Command Central & Help",
            description=f"Server Prefix: `{prefix}` | Type `{prefix}help <command>` for detailed parameters.",
            color=config.COLOR_PRIMARY
        )

        for cog, cog_commands in mapping.items():
            filtered = await self.filter_commands(cog_commands, sort=True)
            if not filtered:
                continue

            name = cog.qualified_name if cog else "General"
            cmd_list = [f"`{c.name}`" for c in filtered]
            embed.add_field(name=f"📁 {name} ({len(cmd_list)})", value=" ".join(cmd_list), inline=False)

        embed.set_footer(text="Anti-Mention • Moderation • Tickets • AutoMod • DMs • Utility • Fun")
        await ctx.send(embed=embed)

    async def send_command_help(self, command):
        ctx = self.context
        prefix = await ctx.bot.db.get_prefix(ctx.guild.id if ctx.guild else None)

        embed = discord.Embed(
            title=f"Command: {command.name}",
            description=command.help or "No description provided.",
            color=config.COLOR_PRIMARY
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
            color=config.COLOR_PRIMARY
        )
        subcommands = [f"`{prefix}{group.name} {c.name}` - {c.short_doc or 'No description'}" for c in group.commands]
        embed.add_field(name="Subcommands", value="\n".join(subcommands), inline=False)
        await ctx.send(embed=embed)

async def get_prefix(bot, message):
    if not message.guild:
        return config.DEFAULT_PREFIX
    return await bot.db.get_prefix(message.guild.id)

class AdvancedDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=CustomHelp(),
            case_insensitive=True
        )
        self.db = Database(config.DATABASE_PATH)

    async def setup_hook(self):
        # 1. Initialize SQLite Database
        print("🔧 Initializing Database schemas...")
        await self.db.init_db()

        # 2. Load Cogs
        print("📦 Loading Extension Cogs...")
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                extension = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(extension)
                    print(f"  └── Loaded: {extension}")
                except Exception as e:
                    print(f"  └── ❌ Failed to load {extension}: {e}")

    async def on_ready(self):
        print(f"\n=======================================================")
        print(f"  Logged in as: {self.user.name}#{self.user.discriminator} (ID: {self.user.id})")
        print(f"  Connected to {len(self.guilds)} guilds with {sum(g.member_count for g in self.guilds)} members.")
        print(f"  Ready for 24/7 Hosting on Railway!")
        print(f"=======================================================\n")

        activity = discord.Activity(type=discord.ActivityType.watching, name=f"{config.DEFAULT_PREFIX}help | Guarding Servers")
        await self.change_presence(status=discord.Status.online, activity=activity)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global error handler for commands."""
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            return await ctx.send(f"{config.EMOJI_ERROR} You lack the required permission(s): `{perms}`")

        if isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            return await ctx.send(f"{config.EMOJI_ERROR} I lack the required permission(s) to execute this: `{perms}`")

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"{config.EMOJI_ERROR} Missing argument: `{error.param.name}`. Type `{ctx.prefix}help {ctx.command}` for usage.")

        if isinstance(error, commands.MemberNotFound):
            return await ctx.send(f"{config.EMOJI_ERROR} Member `{error.argument}` was not found in this server.")

        if isinstance(error, commands.BadArgument):
            return await ctx.send(f"{config.EMOJI_ERROR} Invalid argument provided: {error}")

        # Unexpected error
        print(f"Unhandled error in command {ctx.command}: {error}", file=sys.stderr)
        await ctx.send(f"{config.EMOJI_ERROR} An error occurred while running the command: `{error}`")

bot = AdvancedDiscordBot()

# --- ADMIN SYNC COMMAND ---

@bot.command(name="sync")
@commands.is_owner()
async def sync_slash_commands(ctx: commands.Context):
    """Sync application slash commands globally."""
    msg = await ctx.send("⏳ Syncing slash commands...")
    synced = await bot.tree.sync()
    await msg.edit(content=f"{config.EMOJI_SUCCESS} Synced **{len(synced)}** application command(s) globally.")

# --- RUN BOT ---

async def main():
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "your_bot_token_here":
        print("❌ ERROR: DISCORD_TOKEN is not set in environment or .env file!")
        print("Please create a bot on https://discord.com/developers/applications and set DISCORD_TOKEN.")
        sys.exit(1)

    async with bot:
        await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot shut down cleanly.")
