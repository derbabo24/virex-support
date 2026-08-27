# 🛡️ SentinelBot - Ultimate Discord Moderation & Multi-Feature Bot

A high-performance, production-ready Discord Bot built with **Python (`discord.py` 2.x)** and `aiosqlite`. Engineered specifically for **24/7 Hosting on Railway** (or Docker / VPS / Local).

Everything in the bot is in **English** with clean embeds, emojis, permission checks, and automatic SQLite database management.

---

## 🌟 Key Features Overview (100+ Functions & Commands)

- 🛡️ **Anti-@ / Anti-Mention Guard**: Select specific users (e.g. Server Owner, Admins) or roles to protect against unauthorized pings. If an unauthorized user mentions them, their message is immediately deleted, the offender is punished (Delete / Warn / Timeout / Kick), and a log is dispatched. Includes a complete Whitelist system!
- 🔨 **Complete Moderation Suite**: `.ban`, `.unban`, `.softban`, `.tempban`, `.massban`, `.kick`, `.mute` (timeout), `.unmute`, `.warn`, `.warns`, `.delwarn`, `.clearwarns`, `.purge`, `.purgeuser`, `.purgebot`, `.purgelinks`, `.lock`, `.unlock`, `.hide`, `.unhide`, `.slowmode`, `.setnick`, `.role add/remove`.
- ✉️ **Direct Messaging & ModMail**: `.dm @user <message>`, `.reply <userId> <text>`, `.massdm <message>`, automated moderation action DMs (notifies punished users), and a ModMail relay where user DMs are sent straight to a staff channel.
- 🤖 **AutoMod Shield**: Anti-Spam (flooding detection), Anti-Discord-Invites, Anti-External-Links, Anti-Caps filter, Mass-Mentions guard, and custom blacklisted bad words (`.badwords add/remove/list`).
- 🎫 **Interactive Ticket System**: Full Discord UI Buttons panel (`.ticket panel`), auto ticket channel creation, permission isolation, chat transcripts (`.ticket transcript`), and close/reopen buttons.
- ⚙️ **Server Management**: Custom welcome/leave channels & messages with variables (`{user}`, `{server}`, `{members}`), AutoRole on join, Mod-Log channel, and customizable server prefix (`.setprefix <prefix>`).
- 🧰 **20+ Utility Tools**: `.userinfo`, `.serverinfo`, `.avatar`, `.banner`, `.roleinfo`, `.channelinfo`, `.id`, `.calc` (safe math parser), `.qrcode` generator, `.reminder` timer loop, `.poll`, `.embed` builder.
- 🎮 **20+ Fun & Community**: `.8ball`, `.meme`, `.joke`, `.roast`, `.rps`, `.ship` love calculator, `.coinflip`, `.dice`, `.roll`, `.fact`, `.say`, `.reverse`, `.slap`, `.hug`, `.pat`, `.rate`.
- 💰 **Economy & Leveling**: Chat XP system with level-up notifications, `.rank`, `.xptop`, `.balance`, `.daily` coins, `.deposit`, `.withdraw`, `.pay`, and `.ecotop`.

---

## 🚀 How to Host on Railway (Step-by-Step)

Railway makes it effortless to run this bot 24/7 with zero downtime.

### Step 1: Discord Developer Portal Setup
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, give your bot a name, and click Create.
3. In the left menu, click **Bot**:
   - Click **Reset Token** and copy your **Bot Token** (keep this secret!).
   - Scroll down to **Privileged Gateway Intents** and enable ALL THREE:
     - ✅ **Presence Intent**
     - ✅ **Server Members Intent**
     - ✅ **Message Content Intent**
   - Click **Save Changes**.
4. In the left menu, click **OAuth2** -> **URL Generator**:
   - Under **Scopes**, check `bot` and `applications.commands`.
   - Under **Bot Permissions**, check `Administrator` (or all moderation/channel permissions).
   - Copy the generated URL and paste it in your browser to invite the bot to your Discord server.

---

### Step 2: Deploy to Railway
1. Push this project folder to your **GitHub** account (or connect directly via Railway CLI):
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Discord bot"
   git branch -M main
   git remote add origin https://github.com/your-username/your-repo-name.git
   git push -u origin main
   ```
2. Open [Railway.app](https://railway.app/) and click **New Project** -> **Deploy from GitHub repo**.
3. Select your repository.
4. In your Railway project dashboard, click on your service and go to the **Variables** tab:
   - Add variable: `DISCORD_TOKEN` = `(paste your bot token from Step 1)`
   - Add variable: `DEFAULT_PREFIX` = `.` (optional, defaults to `.`)
   - Add variable: `OWNER_ID` = `your_discord_user_id` (optional)
5. Go to the **Settings** tab:
   - Under **Volumes** (Optional for persistent storage across redeploys): Add a Volume mounted at `/app` if you want database files to persist forever across code rebuilds.
6. Railway will automatically build using `Procfile` and `railway.json` and start `python main.py`!
7. Check the **Deployments** / **Logs** tab in Railway to see:
   ```
   =======================================================
     Logged in as: YourBot#0000 (ID: 1234567890)
     Ready for 24/7 Hosting on Railway!
   =======================================================
   ```

---

## 💻 Local Setup / Running on PC

If you want to test or run locally:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy .env.example to .env and configure your token
cp .env.example .env

# 3. Start the bot
python main.py
```

---

## 📖 Command Documentation

### 1. 🛡️ Anti-Mention / Anti-@ System (`.antiping`)
| Command | Description |
|---|---|
| `.antiping adduser @user [delete/warn/mute/kick] [mute_mins]` | Protect a user against unauthorized mentions |
| `.antiping addrole @role [delete/warn/mute/kick] [mute_mins]` | Protect a whole role against unauthorized mentions |
| `.antiping remove @user/@role` | Remove protection |
| `.antiping whitelist @target @allowed_user_or_role` | Grant permission to someone to ping the target |
| `.antiping unwhitelist @target @allowed_user_or_role` | Revoke mention permission |
| `.antiping list` | View all active protected users & roles |

---

### 2. 🔨 Moderation Commands
| Command | Description | Example |
|---|---|---|
| `.ban @user [reason]` | Bans a member from the server and sends a DM | `.ban @Troll Spammed invite links` |
| `.unban <userId>` | Unbans a user by their user ID | `.unban 1234567890 Appeal accepted` |
| `.softban @user [reason]` | Bans and unbans instantly to purge 7 days of messages | `.softban @Raider Raiding channel` |
| `.tempban @user <duration> [reason]` | Bans user temporarily (auto-unbans after duration) | `.tempban @User 2d Toxic behavior` |
| `.massban <id1> <id2> ...` | Bans multiple user IDs in one command | `.massban 111 222 333 Bot raid` |
| `.kick @user [reason]` | Kicks member from the server | `.kick @User Rule violation` |
| `.mute @user <duration> [reason]` | Times out / mutes a user (e.g. 5m, 1h, 1d) | `.mute @User 30m Arguing in chat` |
| `.unmute @user` | Removes timeout / unmutes a user | `.unmute @User` |
| `.warn @user [reason]` | Issues a formal warning and increments case counter | `.warn @User Inappropriate language` |
| `.warns @user` | Lists all past warnings for a user | `.warns @User` |
| `.delwarn <case_id>` | Deletes a warning by its Case ID | `.delwarn 4` |
| `.clearwarns @user` | Clears all warnings for a user | `.clearwarns @User` |
| `.purge <count>` | Bulk deletes messages in channel (1-100) | `.purge 25` |
| `.purgeuser @user <count>` | Deletes messages sent only by specific user | `.purgeuser @User 50` |
| `.purgebot <count>` | Deletes messages sent by bots | `.purgebot 20` |
| `.purgelinks <count>` | Deletes messages containing URLs | `.purgelinks 20` |
| `.lock [#channel]` | Locks channel for @everyone | `.lock #general` |
| `.unlock [#channel]` | Unlocks channel for @everyone | `.unlock #general` |
| `.hide [#channel]` | Hides channel from @everyone | `.hide #staff-chat` |
| `.unhide [#channel]` | Unhides channel for @everyone | `.unhide #announcements` |
| `.slowmode <seconds>` | Sets slowmode delay (0 to disable) | `.slowmode 5` |
| `.setnick @user <nickname>` | Changes member nickname | `.setnick @User Alex` |
| `.role add @user @role` | Assigns a role to a member | `.role add @User @VIP` |
| `.role remove @user @role` | Removes a role from a member | `.role remove @User @VIP` |

---

### 3. ✉️ Direct Messages (DM) & ModMail
| Command | Description |
|---|---|
| `.dm @user <message>` | Sends a direct message embed to a user as the bot |
| `.reply <userId> <message>` | Replies to a user's DM / ModMail message |
| `.massdm <message>` | Sends an announcement DM to all server members (Admin only, with rate-limiting) |
| `.toggledm` | Toggles whether users receive automated DMs when warned/kicked/banned/muted |

---

### 4. 🤖 AutoMod Protection (`.automod`)
| Command | Description |
|---|---|
| `.automod` | Displays current status of AutoMod protections |
| `.automod antispam on/off` | Toggles rapid message flood detection |
| `.automod antiinvites on/off` | Blocks & deletes Discord invite links (`discord.gg/...`) |
| `.automod antilinks on/off` | Blocks & deletes all external links |
| `.automod anticaps on/off` | Blocks & deletes excessive CAPITAL letters (>70%) |
| `.automod maxmentions <limit>` | Sets maximum allowed mentions per message |
| `.badwords add <word>` | Blacklists a word |
| `.badwords remove <word>` | Removes a word from blacklist |
| `.badwords list` | Lists all blacklisted words |

---

### 5. 🎫 Ticket System (`.ticket`)
| Command | Description |
|---|---|
| `.ticket panel [#channel]` | Sends the interactive button embed panel ("Open a Ticket") |
| `.ticket category <category_id>` | Sets the parent category where ticket channels will open |
| `.ticket close` | Closes and deletes the current ticket channel |
| `.ticket add @user` | Adds a user to the ticket |
| `.ticket remove @user` | Removes a user from the ticket |
| `.ticket transcript` | Generates and uploads a `.txt` transcript of the ticket chat |

---

### 6. ⚙️ Server Management & Settings
| Command | Description |
|---|---|
| `.settings` | Shows the server configuration overview |
| `.setprefix <new_prefix>` | Sets custom prefix for this server (e.g. `!`, `?`, `$`) |
| `.setmodlog #channel` | Sets the channel where moderation action logs are posted |
| `.setmodmail #channel` | Sets the channel where incoming user DMs are forwarded |
| `.setwelcome #channel` | Sets the welcome greeting channel |
| `.welcomemsg <text>` | Sets custom welcome message (Variables: `{user}`, `{server}`, `{members}`) |
| `.setleave #channel` | Sets the member leave / goodbye channel |
| `.leavemsg <text>` | Sets custom leave message |
| `.setautorole @role` | Automatically grants this role to new members |
| `.disableautorole` | Disables AutoRole |

---

### 7. 🧰 Utility & Info Tools
| Command | Description |
|---|---|
| `.help [command]` | Interactive categorization help menu |
| `.ping` | Check bot latency and response time |
| `.uptime` | Displays total bot uptime |
| `.botinfo` | Shows bot statistics, server count, and architecture |
| `.userinfo [@user]` | Displays full user profile details, join date, account age & roles |
| `.serverinfo` | Displays server creation date, member stats, boost level, and counts |
| `.avatar [@user]` | Displays full-resolution avatar image with direct link |
| `.banner [@user]` | Displays user profile banner image |
| `.roleinfo @role` | Displays role color, permissions, position, and member count |
| `.channelinfo [#channel]` | Displays channel topic, slowmode, and category |
| `.id [@target]` | Grabs user/role/channel Discord Snowflake ID |
| `.calc <expression>` | Safe mathematical evaluation (`.calc 25 * 4 + (100 / 2)`) |
| `.qrcode <url/text>` | Generates a scannable QR Code image |
| `.reminder <time> <text>` | Sets a scheduled reminder timer (`.reminder 15m Take pizza out`) |
| `.poll <question>` | Creates a thumbs up / thumbs down poll embed |
| `.embed Title | Description | Hex` | Custom embed message creator |

---

### 8. 🎮 Fun, Games & Entertainment
| Command | Description |
|---|---|
| `.8ball <question>` | Ask the Magic 8-Ball |
| `.meme` | Fetches a top trending meme from Reddit |
| `.joke` | Fetches a funny joke with spoiler punchline |
| `.roast [@user]` | Friendly roast |
| `.rps <rock/paper/scissors>` | Play Rock Paper Scissors against the bot |
| `.ship @user1 [@user2]` | Love compatibility calculator with visual meter |
| `.coinflip` | Flip a coin (Heads/Tails) |
| `.dice [sides]` | Roll custom-sided die (e.g. `.dice 20`) |
| `.roll <min> <max>` | Generate random number |
| `.fact` | Interesting random real-world fact |
| `.choose opt1, opt2, opt3` | Randomly picks an option |
| `.say <text>` | Bot repeats your message and deletes original |
| `.reverse <text>` | Reverses text backwards |
| `.slap @user` | Slap interaction |
| `.hug @user` | Hug interaction |
| `.pat @user` | Headpat interaction |
| `.rate <thing>` | Rates anything from 0 to 10 |

---

### 9. 💰 Economy & Activity Leveling
| Command | Description |
|---|---|
| `.balance [@user]` | Check wallet and bank coin balance |
| `.daily` | Claim daily reward coins (once every 24 hours) |
| `.deposit <amount/all>` | Moves coins from wallet to bank |
| `.withdraw <amount/all>` | Moves coins from bank to wallet |
| `.pay @user <amount>` | Transfers coins to another member |
| `.ecotop` | Server leaderboard of richest members |
| `.rank [@user]` | Check current Level and XP status |
| `.xptop` | Server leaderboard of highest level members |
