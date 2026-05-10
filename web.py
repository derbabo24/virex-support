"""
Virex Web Server — OAuth2 Verify + Staff Application Form
Token refresh stored → backup lives forever
"""

import os
import json
import uuid
import requests
from datetime import datetime, timezone
from flask import Flask, request, render_template_string, redirect
from dotenv import load_dotenv

load_dotenv()

# ── ENV ──────────────────────────────────────────────────────
CLIENT_ID        = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET    = os.getenv("DISCORD_CLIENT_SECRET", "")
WEB_BASE_URL     = os.getenv("WEB_BASE_URL", "https://your-app.up.railway.app")

GUILD_ID         = int(os.getenv("GUILD_ID", 0))
BOT_TOKEN        = os.getenv("DISCORD_TOKEN", "")
VERIFIED_ROLE_ID = int(os.getenv("VERIFIED_ROLE_ID", 0))
VIREX_WEBSITE    = os.getenv("VIREX_WEBSITE", "https://virex.gg/")

REDIRECT_URI      = f"{WEB_BASE_URL}/callback"
APPLY_OAUTH_URI   = f"{WEB_BASE_URL}/apply/callback"

VERIFIED_FILE     = "verified.json"
APPLICATIONS_FILE = "applications.json"

app = Flask(__name__)

# ── STORAGE ──────────────────────────────────────────────────
def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ── DISCORD HELPERS ──────────────────────────────────────────
def give_role(user_id: str):
    if not BOT_TOKEN or VERIFIED_ROLE_ID == 0:
        print("⚠️ Missing BOT_TOKEN or VERIFIED_ROLE_ID")
        return
    # PUT auf den spezifischen Role Endpoint — überschreibt keine anderen Rollen
    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{VERIFIED_ROLE_ID}"
    res = requests.put(url,
        headers={"Authorization": f"Bot {BOT_TOKEN}"}
    )
    if res.status_code == 204:
        print(f"✅ Role given to {user_id}")
    else:
        print(f"❌ Role error {res.status_code}: {res.text}")


def exchange_code(code: str, redirect_uri: str) -> dict | None:
    """Exchange OAuth2 code for token data. Returns full token dict or None."""
    res = requests.post(
        "https://discord.com/api/v10/oauth2/token",
        data={
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  redirect_uri,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if res.status_code != 200:
        print(f"❌ Token exchange failed: {res.status_code} {res.text}")
        return None
    return res.json()  # contains: access_token, refresh_token, expires_in, token_type, scope


def get_discord_user(access_token: str) -> dict | None:
    res = requests.get(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if res.status_code != 200:
        return None
    return res.json()


# ── SHARED CSS ───────────────────────────────────────────────
BASE_STYLE = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<style>
:root {
  --bg:      #050810;
  --card:    #080c18;
  --card2:   #0c1020;
  --border:  #131828;
  --border2: #1a2040;
  --blue:    #00E5FF;
  --blue2:   #0099bb;
  --green:   #00ff99;
  --red:     #ff3c3c;
  --gold:    #FFD700;
  --text:    #d8e2ff;
  --muted:   #556080;
  --input:   #080c18;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Barlow', sans-serif;
  font-size: 15px;
  line-height: 1.6;
  min-height: 100vh;
}
a { color: var(--blue); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── GRID BACKGROUND ── */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(0,229,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,229,255,0.025) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

/* ── GLOW ── */
body::after {
  content: '';
  position: fixed;
  top: -300px; left: 50%;
  transform: translateX(-50%);
  width: 800px; height: 500px;
  background: radial-gradient(ellipse, rgba(0,229,255,0.06) 0%, transparent 65%);
  pointer-events: none;
  z-index: 0;
}

.page-wrap {
  position: relative;
  z-index: 1;
  max-width: 660px;
  margin: 0 auto;
  padding: 48px 20px 80px;
}

/* ── HEADER ── */
.site-header {
  text-align: center;
  margin-bottom: 44px;
}
.logo-wrap {
  display: inline-block;
  position: relative;
  margin-bottom: 16px;
}
.logo-wrap img {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 2px solid rgba(0,229,255,0.4);
  display: block;
}
.logo-glow {
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0,229,255,0.15), transparent 70%);
  pointer-events: none;
}
.logo-emoji {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 80px; height: 80px;
  border-radius: 50%;
  border: 2px solid rgba(0,229,255,0.3);
  background: rgba(0,229,255,0.05);
  font-size: 36px;
  margin-bottom: 16px;
}
.site-header h1 {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 42px;
  color: var(--blue);
  letter-spacing: 6px;
  text-transform: uppercase;
  line-height: 1;
}
.site-header .sub {
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-top: 6px;
}

/* ── CARD ── */
.card {
  background: linear-gradient(160deg, var(--card) 0%, var(--card2) 100%);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 36px 40px;
  box-shadow:
    0 0 0 1px rgba(0,229,255,0.05),
    0 20px 60px rgba(0,0,0,0.5),
    inset 0 1px 0 rgba(255,255,255,0.03);
  animation: fadeUp 0.45s cubic-bezier(0.22,1,0.36,1) both;
}
@keyframes fadeUp {
  from { transform: translateY(20px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}

/* ── SECTION TITLE ── */
.form-section { margin-bottom: 28px; }
.section-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 14px;
  color: var(--blue);
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

/* ── FORM ELEMENTS ── */
.form-row { display: grid; gap: 14px; margin-bottom: 14px; }
.form-row.cols-2 { grid-template-columns: 1fr 1fr; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
label { font-size: 12px; font-weight: 600; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; }
label .req { color: var(--blue); margin-left: 2px; }

input[type="text"],
input[type="number"],
select,
textarea {
  background: rgba(0,0,0,0.3);
  border: 1px solid var(--border2);
  border-radius: 8px;
  padding: 11px 14px;
  color: var(--text);
  font-family: 'Barlow', sans-serif;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  width: 100%;
}
input:focus, select:focus, textarea:focus {
  border-color: rgba(0,229,255,0.5);
  box-shadow: 0 0 0 3px rgba(0,229,255,0.08);
}
select option { background: #080c18; }
textarea { resize: vertical; min-height: 90px; }

/* ── CHAR COUNTER ── */
.char-wrap { position: relative; }
.char-counter {
  position: absolute;
  bottom: 10px; right: 12px;
  font-size: 11px; color: var(--muted);
  pointer-events: none;
}

/* ── SUBMIT BTN ── */
.btn-submit {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, var(--blue) 0%, var(--blue2) 100%);
  color: #000;
  border: none;
  border-radius: 10px;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 20px;
  letter-spacing: 3px;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.2s;
  margin-top: 8px;
  box-shadow: 0 4px 20px rgba(0,229,255,0.2);
}
.btn-submit:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 6px 28px rgba(0,229,255,0.3);
}
.btn-submit:active { transform: translateY(0); }
.btn-submit:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

/* ── DIVIDER ── */
.divider { border: none; border-top: 1px solid var(--border); margin: 28px 0; }

/* ── DISCORD TAG ── */
.discord-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(88,101,242,0.1);
  border: 1px solid rgba(88,101,242,0.2);
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 14px;
  font-weight: 600;
  color: #8fa8ff;
  margin-bottom: 20px;
}
.discord-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
  flex-shrink: 0;
}

/* ── STATUS ── */
.status-card { text-align: center; padding: 16px 0 10px; }
.status-icon { font-size: 54px; display: block; margin-bottom: 14px; }
.status-card h2 {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 32px;
  letter-spacing: 3px;
}
.status-card h2.success { color: var(--green); }
.status-card h2.error   { color: var(--red); }
.status-card h2.warning { color: var(--gold); }
.status-card p { color: var(--muted); margin-top: 10px; font-size: 14px; }

.highlight-box {
  background: rgba(0,229,255,0.05);
  border: 1px solid rgba(0,229,255,0.15);
  border-radius: 8px;
  padding: 12px 18px;
  margin: 18px 0 0;
  font-size: 14px;
  color: var(--blue);
  text-align: center;
}

/* ── FOOTER ── */
.footer {
  text-align: center;
  margin-top: 30px;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 1px;
}

/* ── RESPONSIVE ── */
@media (max-width: 520px) {
  .card { padding: 24px 20px; }
  .form-row.cols-2 { grid-template-columns: 1fr; }
  .site-header h1 { font-size: 32px; }
}
</style>
"""

LOGO_HTML = f'<div class="logo-wrap"><div class="logo-glow"></div><img src="/static/logo.png" alt="Virex" onerror="this.parentElement.innerHTML=\'<span style=&quot;font-size:44px&quot;>🐻</span>\'"></div>'

# ── VERIFY SUCCESS ────────────────────────────────────────────
SUCCESS_HTML = BASE_STYLE + """
<div class="page-wrap">
  <header class="site-header">
    """ + LOGO_HTML + """
    <h1>VIREX</h1>
    <div class="sub">Secure Verification</div>
  </header>
  <div class="card">
    <div class="status-card">
      <span class="status-icon">✅</span>
      <h2 class="success">VERIFIED</h2>
      <div class="discord-tag" style="display:inline-flex;margin-top:18px">
        <span class="discord-dot"></span>
        {{ username }}
      </div>
      <p>Your account is verified.<br>You can close this tab and return to Discord.</p>
    </div>
    <div class="highlight-box">🎉 Full server access unlocked</div>
  </div>
  <div class="footer"><a href="{{ website }}">{{ website }}</a></div>
</div>
"""

# ── ERROR ─────────────────────────────────────────────────────
ERROR_HTML = BASE_STYLE + """
<div class="page-wrap">
  <header class="site-header">
    <div class="logo-emoji">🐻</div>
    <h1>VIREX</h1>
  </header>
  <div class="card">
    <div class="status-card">
      <span class="status-icon">❌</span>
      <h2 class="error">ERROR</h2>
      <p>{{ error }}</p>
    </div>
  </div>
  <div class="footer"><a href="{{ website }}">{{ website }}</a></div>
</div>
"""

# ── APPLY OAUTH STEP ──────────────────────────────────────────
APPLY_OAUTH_HTML = BASE_STYLE + """
<div class="page-wrap">
  <header class="site-header">
    """ + LOGO_HTML + """
    <h1>VIREX</h1>
    <div class="sub">Staff Application</div>
  </header>
  <div class="card">
    <div class="status-card">
      <span class="status-icon" style="font-size:42px">🔐</span>
      <h2 style="color:var(--blue);font-size:26px;letter-spacing:3px">IDENTIFY</h2>
      <p style="margin-top:12px">We need to verify your Discord account<br>before you can submit an application.</p>
    </div>
    <div style="margin-top:28px;text-align:center">
      <a href="{{ oauth_url }}" style="
        display:inline-block;padding:14px 36px;
        background:#5865F2;color:white;border-radius:10px;
        font-family:'Bebas Neue',sans-serif;font-size:18px;
        letter-spacing:2px;text-decoration:none;
        box-shadow:0 4px 20px rgba(88,101,242,0.3);
        transition:opacity 0.2s
      " onmouseover="this.style.opacity=0.85" onmouseout="this.style.opacity=1">
        🔐 &nbsp; CONTINUE WITH DISCORD
      </a>
    </div>
    <p style="text-align:center;color:var(--muted);font-size:12px;margin-top:18px">
      We only read your username and ID — never your password.
    </p>
  </div>
  <div class="footer"><a href="{{ website }}">{{ website }}</a></div>
</div>
"""

# ── APPLY FORM ────────────────────────────────────────────────
APPLY_FORM_HTML = BASE_STYLE + """
<div class="page-wrap">
  <header class="site-header">
    """ + LOGO_HTML + """
    <h1>VIREX</h1>
    <div class="sub">Staff Application</div>
  </header>
  <div class="card">
    <div class="discord-tag">
      <span class="discord-dot"></span>
      Applying as: <strong>{{ username }}</strong>
    </div>

    <form method="POST" action="/apply/submit" id="appForm">
      <input type="hidden" name="discord_id"      value="{{ discord_id }}">
      <input type="hidden" name="discord_username" value="{{ username }}">

      <div class="form-section">
        <div class="section-title">Personal Info</div>
        <div class="form-row cols-2">
          <div class="form-group">
            <label>Age <span class="req">*</span></label>
            <input type="number" name="age" min="13" max="99" required placeholder="e.g. 18">
          </div>
          <div class="form-group">
            <label>Timezone <span class="req">*</span></label>
            <input type="text" name="timezone" required placeholder="e.g. CET, EST, PST">
          </div>
        </div>
        <div class="form-row cols-2">
          <div class="form-group">
            <label>Languages <span class="req">*</span></label>
            <input type="text" name="languages" required placeholder="e.g. English, German">
          </div>
          <div class="form-group">
            <label>Weekly availability <span class="req">*</span></label>
            <select name="availability" required>
              <option value="" disabled selected>Select hours/week</option>
              <option value="1–5h">1–5 hours</option>
              <option value="5–10h">5–10 hours</option>
              <option value="10–20h">10–20 hours</option>
              <option value="20h+">20+ hours</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>How long have you had Discord? <span class="req">*</span></label>
            <input type="text" name="discord_since" required placeholder="e.g. 3 years, since 2020">
          </div>
        </div>
      </div>

      <hr class="divider">

      <div class="form-section">
        <div class="section-title">Experience</div>
        <div class="form-row">
          <div class="form-group">
            <label>Previous staff / moderation experience <span class="req">*</span></label>
            <div class="char-wrap">
              <textarea name="previous_staff" id="prev_staff" required placeholder="Describe any previous staff roles. If none, write 'No experience'." maxlength="600" rows="4"></textarea>
              <span class="char-counter" id="cnt_prev">0 / 600</span>
            </div>
          </div>
        </div>
      </div>

      <hr class="divider">

      <div class="form-section">
        <div class="section-title">Motivation</div>
        <div class="form-row">
          <div class="form-group">
            <label>Why do you want to join the Virex staff team? <span class="req">*</span></label>
            <div class="char-wrap">
              <textarea name="why_valora" id="why_valora" required placeholder="Tell us why you want to be part of Virex and what you can contribute." maxlength="800" rows="5"></textarea>
              <span class="char-counter" id="cnt_why">0 / 800</span>
            </div>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Your skills & strengths <span class="req">*</span></label>
            <div class="char-wrap">
              <textarea name="skills" id="skills" required placeholder="e.g. problem solving, fast response, coding, multilingual, customer support..." maxlength="600" rows="4"></textarea>
              <span class="char-counter" id="cnt_skills">0 / 600</span>
            </div>
          </div>
        </div>
      </div>

      <hr class="divider">

      <div class="form-section">
        <div class="section-title">Anything else?</div>
        <div class="form-row">
          <div class="form-group">
            <label>Additional information (optional)</label>
            <div class="char-wrap">
              <textarea name="extra" id="extra" placeholder="Anything else you'd like us to know?" maxlength="400" rows="3"></textarea>
              <span class="char-counter" id="cnt_extra">0 / 400</span>
            </div>
          </div>
        </div>
      </div>

      <button type="submit" class="btn-submit" id="submitBtn">
        SUBMIT APPLICATION
      </button>
    </form>
  </div>
  <div class="footer">
    <a href="{{ website }}">{{ website }}</a>
    &nbsp;•&nbsp; All applications are reviewed manually
  </div>
</div>

<script>
function bindCounter(id, cntId) {
  const ta = document.getElementById(id);
  const cnt = document.getElementById(cntId);
  if (!ta || !cnt) return;
  const max = ta.getAttribute('maxlength');
  const update = () => {
    cnt.textContent = ta.value.length + ' / ' + max;
    cnt.style.color = ta.value.length > max * 0.9 ? '#ff8844' : '';
  };
  ta.addEventListener('input', update);
  update();
}
bindCounter('prev_staff', 'cnt_prev');
bindCounter('why_valora', 'cnt_why');
bindCounter('skills',     'cnt_skills');
bindCounter('extra',      'cnt_extra');

document.getElementById('appForm').addEventListener('submit', function() {
  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'SUBMITTING…';
});
</script>
"""

APPLY_SUCCESS_HTML = BASE_STYLE + """
<div class="page-wrap">
  <header class="site-header">
    """ + LOGO_HTML + """
    <h1>VIREX</h1>
    <div class="sub">Staff Application</div>
  </header>
  <div class="card">
    <div class="status-card">
      <span class="status-icon">🎉</span>
      <h2 class="success">SUBMITTED</h2>
      <p style="margin-top:14px">
        Thank you, <strong>{{ username }}</strong>!<br>
        Your application has been received and will be reviewed by our team.
      </p>
    </div>
    <div class="highlight-box" style="margin-top:20px">
      📬 You'll receive a DM on Discord once a decision has been made.
    </div>
    <p style="text-align:center;color:var(--muted);font-size:13px;margin-top:20px">
      Application ID: <code style="color:var(--blue)">{{ app_id }}</code>
    </p>
  </div>
  <div class="footer"><a href="{{ website }}">{{ website }}</a></div>
</div>
"""

APPLY_ALREADY_HTML = BASE_STYLE + """
<div class="page-wrap">
  <header class="site-header">
    """ + LOGO_HTML + """
    <h1>VIREX</h1>
  </header>
  <div class="card">
    <div class="status-card">
      <span class="status-icon">⏳</span>
      <h2 class="warning">PENDING</h2>
      <p style="margin-top:12px">
        Hey <strong>{{ username }}</strong>, you already have a pending application.<br>
        Please wait for our team to review it before submitting a new one.
      </p>
    </div>
  </div>
  <div class="footer"><a href="{{ website }}">{{ website }}</a></div>
</div>
"""


# ── ROUTES ───────────────────────────────────────────────────

@app.route("/")
def home():
    return """<div style="text-align:center;color:#00E5FF;font-family:'Bebas Neue',sans-serif;
    letter-spacing:4px;font-size:32px;margin-top:100px">VIREX ✅<br>
    <span style="font-size:14px;color:#556080;font-family:sans-serif;letter-spacing:1px">OAuth Server Running</span></div>"""


# ── VERIFY FLOW ──────────────────────────────────────────────

@app.route("/callback")
def callback():
    code  = request.args.get("code")
    error = request.args.get("error")

    if error or not code:
        return render_template_string(ERROR_HTML, error="Authorization was cancelled or failed.", website=VIREX_WEBSITE), 400

    token_data = exchange_code(code, REDIRECT_URI)
    if not token_data:
        return render_template_string(ERROR_HTML, error="Token exchange failed. Please try again.", website=VIREX_WEBSITE), 500

    access_token  = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")  # ← KEY: save this for infinite refresh

    user = get_discord_user(access_token)
    if not user:
        return render_template_string(ERROR_HTML, error="Could not fetch Discord user.", website=VIREX_WEBSITE), 500

    uid      = user["id"]
    username = user["username"]

    verified = load_json(VERIFIED_FILE)
    verified[uid] = {
        "username":           username,
        "access_token":       access_token,
        "refresh_token":      refresh_token,  # ← stored forever, refreshed every 6 days by bot
        "verified_at":        datetime.now(timezone.utc).isoformat(),
        "token_refreshed_at": None,
        "token_expired":      False,
    }
    save_json(VERIFIED_FILE, verified)

    give_role(uid)
    print(f"✅ VERIFIED: {username} ({uid}) — refresh_token stored: {'yes' if refresh_token else 'NO'}")

    return render_template_string(SUCCESS_HTML, username=username, website=VIREX_WEBSITE)


# ── APPLY FLOW ───────────────────────────────────────────────

@app.route("/apply")
def apply_start():
    import urllib.parse
    encoded_redirect = urllib.parse.quote(APPLY_OAUTH_URI, safe="")
    oauth_url = (
        "https://discord.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={encoded_redirect}"
        "&response_type=code"
        "&scope=identify"
    )
    return render_template_string(APPLY_OAUTH_HTML, oauth_url=oauth_url, website=VIREX_WEBSITE)


@app.route("/apply/callback")
def apply_callback():
    code  = request.args.get("code")
    error = request.args.get("error")

    if error or not code:
        return render_template_string(ERROR_HTML, error="Discord login cancelled.", website=VIREX_WEBSITE), 400

    token_data = exchange_code(code, APPLY_OAUTH_URI)
    if not token_data:
        return render_template_string(ERROR_HTML, error="Could not authenticate with Discord.", website=VIREX_WEBSITE), 500

    user = get_discord_user(token_data["access_token"])
    if not user:
        return render_template_string(ERROR_HTML, error="Could not fetch Discord user.", website=VIREX_WEBSITE), 500

    uid      = user["id"]
    username = user["username"]

    apps = load_json(APPLICATIONS_FILE)
    for app_data in apps.values():
        if str(app_data.get("discord_id")) == str(uid) and app_data.get("status") == "pending":
            return render_template_string(APPLY_ALREADY_HTML, username=username, website=VIREX_WEBSITE)

    return render_template_string(APPLY_FORM_HTML, discord_id=uid, username=username, website=VIREX_WEBSITE)


@app.route("/apply/submit", methods=["POST"])
def apply_submit():
    discord_id       = request.form.get("discord_id", "").strip()
    discord_username = request.form.get("discord_username", "Unknown").strip()

    if not discord_id:
        return render_template_string(ERROR_HTML,
            error="Missing Discord ID. Please restart the application.", website=VIREX_WEBSITE), 400

    required = ["age", "timezone", "languages", "availability",
                "discord_since", "previous_staff", "why_valora", "skills"]
    for field in required:
        if not request.form.get(field, "").strip():
            return render_template_string(ERROR_HTML,
                error=f"Field '{field}' is required. Please go back and fill in all fields.",
                website=VIREX_WEBSITE), 400

    app_id = str(uuid.uuid4())[:8].upper()

    apps = load_json(APPLICATIONS_FILE)
    apps[app_id] = {
        "discord_id":       int(discord_id),
        "discord_username": discord_username,
        "submitted_at":     datetime.now(timezone.utc).isoformat(),
        "status":           "pending",
        "message_id":       None,
        "channel_id":       None,
        "age":              request.form.get("age", "").strip(),
        "timezone":         request.form.get("timezone", "").strip(),
        "languages":        request.form.get("languages", "").strip(),
        "availability":     request.form.get("availability", "").strip(),
        "discord_since":    request.form.get("discord_since", "").strip(),
        "previous_staff":   request.form.get("previous_staff", "").strip()[:600],
        "why_valora":       request.form.get("why_valora", "").strip()[:800],
        "skills":           request.form.get("skills", "").strip()[:600],
        "extra":            request.form.get("extra", "").strip()[:400],
    }
    save_json(APPLICATIONS_FILE, apps)
    print(f"📋 New application: {app_id} from {discord_username} ({discord_id})")

    return render_template_string(APPLY_SUCCESS_HTML,
        username=discord_username, app_id=app_id, website=VIREX_WEBSITE)


# ── RUN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"🌐 Virex web server running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
