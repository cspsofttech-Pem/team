"""
Team Task Tracker — shared online board for the whole office, built with Streamlit.
Columns: To Do → In Progress → Completed

- Employees register with their own name + PIN, then sign in.
- Admin signs in with the admin password and gets a dashboard with filters.
- Online: data lives in Supabase. Local testing: data lives in tasks.db.

Run locally:  streamlit run app.py
"""

import hashlib
import hmac
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from storage import SQLiteStore, SupabaseStore

st.set_page_config(page_title="Team Tasks", page_icon="🗂️", layout="wide",
                   initial_sidebar_state="collapsed")


# ---------- Settings (Streamlit Cloud → Settings → Secrets) ----------
def secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:  # no secrets file at all
        return default


TEAM_PASSWORD = secret("app_password")            # needed to register as a new employee
ADMIN_PASSWORD = secret("admin_password")         # admin sign-in
ONLY_OWN = bool(secret("employees_see_only_own", False))  # True: employees see only their tasks
TZ = ZoneInfo(secret("timezone", "Asia/Kolkata"))

STATUSES = ["To Do", "In Progress", "Completed"]
STATUS_ICON = {"To Do": "📝", "In Progress": "⚙️", "Completed": "✅"}
PRIORITIES = ["High", "Medium", "Low"]
PRIORITY_COLOR = {"High": "#b91c1c", "Medium": "#f59e0b", "Low": "#22c55e"}

NEAR_DAYS = 1       # overdue, today or tomorrow -> red edge
MODERATE_DAYS = 4   # 2-4 days left              -> blue edge
                    # 5+ days left               -> green edge


def today() -> date:
    return datetime.now(TZ).date()


def now_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


# ---------- Database ----------
@st.cache_resource
def get_store():
    url, key = secret("supabase_url"), secret("supabase_key")
    if url and key:
        return SupabaseStore(url, key)
    return SQLiteStore(Path(__file__).parent / "tasks.db")


store = get_store()


# ---------- Look & feel: light, colourful, phone-friendly ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
html, body, .stApp, .stMarkdown, button, input, textarea, select { font-family: 'Poppins', system-ui, sans-serif !important; }
.stApp { background: linear-gradient(160deg, #f4f6ff 0%, #fff8f1 55%, #effbf6 100%) !important; color: #1e293b; }
.block-container { padding-top: 1.2rem; padding-left: 1rem; padding-right: 1rem; max-width: 1100px; }
header[data-testid="stHeader"] { background: transparent; }

/* Greeting banner */
.hero { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
        background: linear-gradient(120deg, #6366f1 0%, #8b5cf6 45%, #ec4899 100%);
        color: #fff; border-radius: 22px; padding: 18px 20px; margin-bottom: 12px;
        box-shadow: 0 12px 30px rgba(99,102,241,.28); }
.hero h1 { color: #fff !important; font-size: 1.45rem; font-weight: 700; margin: 2px 0 2px; padding: 0; }
.hero-date { font-size: .8rem; opacity: .85; text-transform: uppercase; letter-spacing: .06em; }
.hero-sub { font-size: .85rem; opacity: .92; }
.hero-bar { height: 8px; width: min(320px, 70vw); background: rgba(255,255,255,.3); border-radius: 99px;
            margin: 10px 0 4px; overflow: hidden; }
.hero-bar span { display: block; height: 100%; background: #fff; border-radius: 99px; }
.brand { text-align: center; padding: 26px 10px 10px; }
.brand .logo { font-size: 3rem; }
.brand h1 { font-weight: 700; margin: 0; background: linear-gradient(120deg,#6366f1,#ec4899);
            -webkit-background-clip: text; background-clip: text; color: transparent !important; }
.brand p { color: #64748b; }

/* Stat cards */
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 6px 0 12px; }
@media (max-width: 640px) { .stats { grid-template-columns: repeat(2, 1fr); } }
.stat { background: #fff; border-radius: 16px; padding: 12px 14px; box-shadow: 0 4px 14px rgba(15,23,42,.06);
        border-top: 4px solid var(--c); }
.stat .num { font-size: 1.6rem; font-weight: 700; color: #0f172a; line-height: 1.1; }
.stat .lbl { font-size: .8rem; color: #64748b; }
[data-testid="stMetric"] { background: #fff; border-radius: 14px; padding: 10px 12px;
                           box-shadow: 0 4px 14px rgba(15,23,42,.06); }

/* Tabs as pills */
[data-baseweb="tab-list"] { gap: 6px; background: #fff; padding: 6px; border-radius: 14px;
                            box-shadow: 0 4px 14px rgba(15,23,42,.06); overflow-x: auto; }
button[data-baseweb="tab"] { border-radius: 10px !important; padding: 8px 14px !important; font-size: .95rem; }
button[data-baseweb="tab"][aria-selected="true"] { background: #eef2ff; color: #4338ca; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }

/* Expanders, forms, popovers */
[data-testid="stExpander"] { background: #fff; border-radius: 14px; border: 1px solid #eef0f6;
                             box-shadow: 0 4px 14px rgba(15,23,42,.05); }
[data-testid="stForm"] { background: #fff; border-radius: 16px; border: 1px solid #eef0f6; }
.stButton button, [data-testid="stPopover"] button { border-radius: 12px; }

/* Ticket cards */
[class*="st-key-card_"] { background: #fff !important; border-radius: 16px !important;
                          border: 1px solid #eef0f6 !important; box-shadow: 0 4px 16px rgba(15,23,42,.07); }
.ticket-title { font-weight: 600; font-size: 1.02rem; margin-bottom: 4px; color: #0f172a; }
.ticket-id { color: #94a3b8; font-size: .72rem; font-family: monospace; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: .72rem;
         font-weight: 600; color: white; margin-right: 4px; border: 1px solid rgba(255,255,255,.6); }
.meta { color: #64748b; font-size: .8rem; margin-top: 6px; line-height: 1.55; }
.overdue { color: #e11d48; font-weight: 600; }
.done-title { text-decoration: line-through; opacity: .6; }

/* Card edge colour by due date */
[class*="st-key-card_near_"]     { border-left: 6px solid #f43f5e !important; background: #fff5f6 !important; }
[class*="st-key-card_moderate_"] { border-left: 6px solid #3b82f6 !important; background: #f3f8ff !important; }
[class*="st-key-card_far_"]      { border-left: 6px solid #10b981 !important; background: #f0fdf7 !important; }

/* HIGH priority: whole card solid red */
[class*="st-key-card_high_"] { background: linear-gradient(135deg, #ef4444, #dc2626) !important;
                               border: 0 !important; box-shadow: 0 8px 22px rgba(220,38,38,.35) !important; }
[class*="st-key-card_high_"] p, [class*="st-key-card_high_"] div, [class*="st-key-card_high_"] span,
[class*="st-key-card_high_"] .meta, [class*="st-key-card_high_"] .overdue, [class*="st-key-card_high_"] .ticket-title,
[class*="st-key-card_high_"] .ticket-id, [class*="st-key-card_high_"] [data-testid="stCaptionContainer"] { color: #fff !important; }
[class*="st-key-card_high_"] button { background: rgba(255,255,255,.2) !important; border-color: rgba(255,255,255,.55) !important; }
[class*="st-key-card_high_"] button p { color: #fff !important; }

.urg-label { font-size: .72rem; font-weight: 600; padding: 2px 10px; border-radius: 99px; color: white;
             border: 1px solid rgba(255,255,255,.6); }
.urg-near-bg { background: #f43f5e; } .urg-moderate-bg { background: #3b82f6; } .urg-far-bg { background: #10b981; }

/* Keep a card's buttons in one row on phones */
[class*="st-key-card_"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .4rem; }
[class*="st-key-card_"] [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }

/* Ringing bell + red count badge */
@keyframes ring { 0%,100% {transform: rotate(0)} 10%,30% {transform: rotate(14deg)} 20%,40% {transform: rotate(-14deg)} 50% {transform: rotate(0)} }
.bell { display: inline-block; animation: ring 1.6s ease-in-out infinite; transform-origin: top center; }
.bellbox { position: relative; display: inline-block; font-size: 2rem; line-height: 1;
           background: rgba(255,255,255,.22); border-radius: 16px; padding: 10px 12px; }
.bellbox .count { position: absolute; top: -6px; right: -6px; background: #f43f5e; color: #fff;
                  font-size: .78rem; font-weight: 800; min-width: 22px; height: 22px; padding: 0 6px;
                  border-radius: 999px; display: flex; align-items: center; justify-content: center;
                  border: 2px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,.2); }
.legend { margin: 4px 0 8px; }
.legend span { display: inline-block; margin: 0 6px 6px 0; font-size: .78rem; white-space: nowrap;
               background: #fff; padding: 3px 10px; border-radius: 99px; border: 1px solid #eef0f6; }
</style>
""", unsafe_allow_html=True)


# ---------- PIN hashing (PINs are never stored as plain text) ----------
def hash_pin(pin: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def check_pin(pin: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt_hex), 120_000)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def name_key(name: str) -> str:
    return " ".join(name.split()).lower()


# ---------- Login / Register / Admin ----------
def login_screen():
    st.markdown("<div class='brand'><div class='logo'>🗂️</div><h1>Team Tasks</h1>"
                "<p>Plan it. Track it. Get it done — together.</p></div>", unsafe_allow_html=True)
    tab_in, tab_reg, tab_admin = st.tabs(["🔑 Sign in", "📝 Register", "🛡️ Admin"])

    with tab_in:
        with st.form("signin"):
            name = st.text_input("Your name")
            pin = st.text_input("PIN", type="password", max_chars=12)
            if st.form_submit_button("Sign in", type="primary", use_container_width=True):
                user = store.get_user(name_key(name)) if name.strip() else None
                if user and check_pin(pin, user["pin_hash"]):
                    st.session_state.user = user["name"]
                    st.session_state.is_admin = False
                    st.rerun()
                else:
                    st.error("Name or PIN is wrong. New here? Use the Register tab.")

    with tab_reg:
        st.caption("First time? Create your account with your own name and a PIN.")
        with st.form("register", clear_on_submit=False):
            name = st.text_input("Your full name")
            p1 = st.text_input("Choose a PIN (4–12 digits or letters)", type="password", max_chars=12)
            p2 = st.text_input("Repeat PIN", type="password", max_chars=12)
            team = st.text_input("Team password (ask your admin)", type="password") if TEAM_PASSWORD else ""
            if st.form_submit_button("Create account", type="primary", use_container_width=True):
                clean = " ".join(name.split())
                if len(clean) < 2:
                    st.error("Please enter your name.")
                elif clean.lower() == "admin":
                    st.error("Please use your real name.")
                elif len(p1) < 4:
                    st.error("PIN must be at least 4 characters.")
                elif p1 != p2:
                    st.error("The two PINs don't match.")
                elif TEAM_PASSWORD and team != TEAM_PASSWORD:
                    st.error("Team password is wrong.")
                elif store.get_user(name_key(clean)):
                    st.error("That name is already registered. Sign in instead, or add your initial (e.g. 'Arun K').")
                else:
                    store.add_user({"name_key": name_key(clean), "name": clean, "pin_hash": hash_pin(p1),
                                    "created_at": now_str(), "last_seen": now_str()})
                    st.session_state.user = clean
                    st.session_state.is_admin = False
                    st.rerun()

    with tab_admin:
        if not ADMIN_PASSWORD:
            st.info("Admin sign-in is off. Add `admin_password` in the app's Secrets to turn it on.")
        else:
            with st.form("admin"):
                pwd = st.text_input("Admin password", type="password")
                if st.form_submit_button("Sign in as admin", type="primary", use_container_width=True):
                    if hmac.compare_digest(pwd, ADMIN_PASSWORD):
                        st.session_state.user = "Admin"
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        st.error("Wrong admin password.")


if "user" not in st.session_state:
    login_screen()
    st.stop()

USER = st.session_state.user
IS_ADMIN = st.session_state.get("is_admin", False)
st.session_state.setdefault("editing", None)
st.session_state.setdefault("confirm_delete", None)


# ---------- Load shared data (fresh every time, so everyone sees the latest) ----------
try:
    all_tasks = store.list()
    users = store.list_users()
except Exception as e:
    st.error(f"Couldn't reach the database: {e}")
    st.stop()

USER_NAMES = sorted(u["name"] for u in users)
me = None if IS_ADMIN else next((u for u in users if u["name_key"] == name_key(USER)), None)
if not IS_ADMIN and me is None:  # account was removed by the admin
    st.session_state.clear()
    st.rerun()


def mine(t):
    return name_key(t.get("assignee") or "") == name_key(USER) or name_key(t.get("created_by") or "") == name_key(USER)


tasks = all_tasks if (IS_ADMIN or not ONLY_OWN) else [t for t in all_tasks if mine(t)]


# ---------- Task helpers ----------
def due_urgency(t):
    if t["status"] == "Completed" or not t.get("due"):
        return None
    days_left = (date.fromisoformat(t["due"]) - today()).days
    if days_left <= NEAR_DAYS:
        return "near"
    return "moderate" if days_left <= MODERATE_DAYS else "far"


def is_due_today(t):
    return t["status"] != "Completed" and t.get("due") == today().isoformat()


def is_overdue(t):
    return t["status"] != "Completed" and bool(t.get("due")) and date.fromisoformat(t["due"]) < today()


def can_delete(t):
    return IS_ADMIN or name_key(t.get("created_by") or "") == name_key(USER)


def add_task(title, description, priority, due, assignee):
    store.add({
        "id": uuid.uuid4().hex[:8], "title": title.strip(), "description": description.strip(),
        "priority": priority, "due": due.isoformat() if due else None, "assignee": assignee or "",
        "status": "To Do", "created_at": now_str(), "created_by": USER,
        "updated_at": now_str(), "updated_by": USER, "completed_at": None,
    })


def move_task(t, step):
    idx = STATUSES.index(t["status"]) + step
    if 0 <= idx < len(STATUSES):
        new_status = STATUSES[idx]
        store.update(t["id"], {"status": new_status,
                               "completed_at": now_str() if new_status == "Completed" else None,
                               "updated_at": now_str(), "updated_by": USER})


# ---------- 🔔 Notifications ----------
def notifications():
    """Returns list of (task, reason)."""
    out = []
    if IS_ADMIN:
        for t in all_tasks:
            if is_overdue(t):
                out.append((t, "⏰ Overdue"))
            elif is_due_today(t):
                out.append((t, "🔔 Due today"))
        return out
    # Employee: only tasks assigned to them or added by them, and still open.
    last_seen = (me or {}).get("last_seen") or ""
    for t in all_tasks:
        if t["status"] == "Completed":
            continue
        assigned_to_me = name_key(t.get("assignee") or "") == name_key(USER)
        added_by_me = name_key(t.get("created_by") or "") == name_key(USER)
        if not (assigned_to_me or added_by_me):
            continue
        if is_overdue(t):
            out.append((t, "⏰ Overdue"))
        elif is_due_today(t):
            out.append((t, "🔔 Due today"))
        elif (assigned_to_me and (t.get("updated_at") or "") > last_seen
              and name_key(t.get("updated_by") or "") != name_key(USER)):
            out.append((t, f"🆕 Assigned / updated by {t.get('updated_by')}"))
    return out


notes = notifications()


# ---------- Header: greeting banner with bell, progress ----------
hour = datetime.now(TZ).hour
greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
n = len(notes)
total_all = len(tasks)
done_all = sum(t["status"] == "Completed" for t in tasks)
pct = round(100 * done_all / total_all) if total_all else 0

st.markdown(f"""
<div class="hero">
  <div>
    <div class="hero-date">{datetime.now(TZ):%A, %d %B %Y}</div>
    <h1>{greeting}, {USER.split()[0]} 👋</h1>
    <div class="hero-sub">{'🛡️ Admin view · all work' if IS_ADMIN else 'Here is what the team is working on'}</div>
    <div class="hero-bar"><span style="width:{pct}%"></span></div>
    <div class="hero-sub">{pct}% of tasks completed</div>
  </div>
  <div class="bellbox"><span class="{'bell' if n else ''}">🔔</span>{f"<span class='count'>{n if n < 100 else '99+'}</span>" if n else ""}</div>
</div>
""", unsafe_allow_html=True)

a1, a2, a3 = st.columns([3, 1, 1], vertical_alignment="center")
with a1.popover(f"🔔 Notifications ({n})", use_container_width=True):
    if not notes:
        st.write("You're all caught up 🎉")
    for t, reason in notes[:30]:
        st.markdown(f"**{reason}** · {t['title']}  \n"
                    f"<small>{STATUS_ICON[t['status']]} {t['status']} · 👤 {t.get('assignee') or '—'}"
                    f"{' · 📅 ' + t['due'] if t.get('due') else ''}</small>", unsafe_allow_html=True)
    if not IS_ADMIN and any(r.startswith("🆕") for _, r in notes):
        if st.button("Mark new ones as read", key="mark_read", use_container_width=True):
            store.update_user(name_key(USER), {"last_seen": now_str()})
            st.rerun()
if a2.button("🔄", key="refresh", help="Refresh", use_container_width=True):
    st.rerun()
if a3.button("🚪", key="signout", help="Sign out", use_container_width=True):
    st.session_state.clear()
    st.rerun()


# ---------- 🔊 Deadline alert: chime + vibration for tasks due today ----------
def deadline_alert(due_list):
    """Plays a chime (and vibrates on Android) once per day per phone.
    Phones block sound until the page is tapped, so a big button is shown when needed."""
    titles = ", ".join(t["title"] for t in due_list[:3]) + (" …" if len(due_list) > 3 else "")
    titles = titles.replace("\\", "").replace("`", "'").replace("<", "‹").replace(">", "›")
    safe_user = "".join(ch for ch in name_key(USER) if ch.isalnum()) or "user"
    play_key = f"tt_chime_{safe_user}_{today().isoformat()}"
    components.html(f"""
<style>
  body {{ margin:0; font-family: 'Poppins', system-ui, sans-serif; }}
  .box {{ display:flex; align-items:center; gap:12px; padding:12px 14px; border-radius:16px;
          background: linear-gradient(120deg,#fff1f2,#ffe4e6); border:1px solid #fecdd3; }}
  .ico {{ font-size:28px; animation: ring 1.4s ease-in-out infinite; transform-origin: top center; }}
  @keyframes ring {{ 0%,100%{{transform:rotate(0)}} 10%,30%{{transform:rotate(16deg)}} 20%,40%{{transform:rotate(-16deg)}} 50%{{transform:rotate(0)}} }}
  .txt {{ flex:1; color:#9f1239; font-size:14px; line-height:1.35; }}
  .txt b {{ font-size:15px; }}
  button {{ border:0; border-radius:12px; padding:10px 14px; font-weight:700; font-size:14px; color:#fff;
            background: linear-gradient(120deg,#f43f5e,#e11d48); box-shadow:0 4px 12px rgba(225,29,72,.35); }}
</style>
<div class="box">
  <div class="ico">🔔</div>
  <div class="txt"><b>{len(due_list)} task(s) due today</b><br>{titles}</div>
  <button id="b">🔊 Tap to hear</button>
</div>
<script>
const KEY = "{play_key}";
const btn = document.getElementById("b");
function chime() {{
  const C = window.AudioContext || window.webkitAudioContext;
  const ctx = new C();
  [880, 1175, 1568, 1175, 1568].forEach((f, i) => {{
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = "sine"; o.frequency.value = f;
    const t = ctx.currentTime + i * 0.16;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.4, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.45);
    o.connect(g); g.connect(ctx.destination); o.start(t); o.stop(t + 0.5);
  }});
  try {{ if (navigator.vibrate) navigator.vibrate([250, 120, 250, 120, 400]); }} catch (e) {{}}
  return ctx;
}}
function markPlayed() {{ try {{ localStorage.setItem(KEY, "1"); }} catch (e) {{}} btn.textContent = "🔊 Play again"; }}
btn.addEventListener("click", () => {{ const c = chime(); if (c.resume) c.resume(); markPlayed(); }});
let already = false;
try {{ already = localStorage.getItem(KEY) === "1"; }} catch (e) {{}}
if (already) {{
  btn.textContent = "🔊 Play again";
}} else {{
  try {{
    const c = chime();
    setTimeout(() => {{ if (c.state === "running") markPlayed(); }}, 300);
  }} catch (e) {{}}
}}
</script>
""", height=86)


if IS_ADMIN:
    due_alert = [t for t in all_tasks if is_due_today(t)]
else:
    due_alert = [t for t in all_tasks if is_due_today(t) and
                 (name_key(t.get("assignee") or "") == name_key(USER)
                  or name_key(t.get("created_by") or "") == name_key(USER))]
if due_alert:
    deadline_alert(due_alert)

overdue_list = [t for t in tasks if is_overdue(t)]
if overdue_list:
    st.error(f"⏰ **Overdue ({len(overdue_list)}):** " + ", ".join(f"**{t['title']}**" for t in overdue_list[:6])
             + (" …" if len(overdue_list) > 6 else ""))
if n and st.session_state.get("toasted") != today().isoformat():
    st.toast(f"🔔 You have {n} notification(s)")
    st.session_state.toasted = today().isoformat()


# ---------- Ticket card ----------
def assignee_input(label, current=""):
    options = [""] + USER_NAMES + ([current] if current and current not in USER_NAMES else [])
    return st.selectbox(label, options, index=options.index(current) if current in options else 0,
                        format_func=lambda x: x or "— unassigned —")


def render_ticket(t, ctx):
    if t["priority"] == "High" and t["status"] != "Completed":
        style = "high"
    else:
        style = due_urgency(t) or "none"
    with st.container(border=True, key=f"card_{style}_{ctx}_{t['id']}"):
        if st.session_state.editing == t["id"]:
            with st.form(f"edit_{ctx}_{t['id']}"):
                new_title = st.text_input("Title", t["title"])
                new_desc = st.text_area("Description", t.get("description") or "", height=70)
                new_pri = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(t["priority"]))
                new_assignee = assignee_input("Assign to", t.get("assignee") or "")
                cur_due = date.fromisoformat(t["due"]) if t.get("due") else None
                new_due = st.date_input("Due date (clear it to remove)", value=cur_due, format="DD/MM/YYYY")
                s1, s2 = st.columns(2)
                if s1.form_submit_button("Save", type="primary", use_container_width=True):
                    if new_title.strip():
                        store.update(t["id"], {"title": new_title.strip(), "description": new_desc.strip(),
                                               "priority": new_pri, "assignee": new_assignee or "",
                                               "due": new_due.isoformat() if new_due else None,
                                               "updated_at": now_str(), "updated_by": USER})
                        st.session_state.editing = None
                        st.rerun()
                if s2.form_submit_button("Cancel", use_container_width=True):
                    st.session_state.editing = None
                    st.rerun()
            return

        title_cls = "ticket-title done-title" if t["status"] == "Completed" else "ticket-title"
        bell = "<span class='bell'>🔔</span> " if is_due_today(t) else ""
        urgency = due_urgency(t)
        urg_label = {"near": "<span class='urg-label urg-near-bg'>Due soon</span>",
                     "moderate": "<span class='urg-label urg-moderate-bg'>Coming up</span>",
                     "far": "<span class='urg-label urg-far-bg'>Plenty of time</span>"}.get(urgency, "")
        st.markdown(
            f"<div class='ticket-id'>#{t['id']}</div>"
            f"<div class='{title_cls}'>{bell}{t['title']}</div>"
            f"<span class='badge' style='background:{PRIORITY_COLOR[t['priority']]}'>{t['priority']}</span>{urg_label}",
            unsafe_allow_html=True,
        )
        if t.get("description"):
            st.caption(t["description"])

        meta = []
        if t.get("assignee"):
            meta.append(f"👤 {t['assignee']}")
        if t.get("due"):
            due_d = date.fromisoformat(t["due"])
            if is_overdue(t):
                meta.append(f"<span class='overdue'>⏰ Overdue · {due_d:%d %b}</span>")
            elif is_due_today(t):
                meta.append("<span class='overdue'>🔔 Due today</span>")
            else:
                meta.append(f"📅 {due_d:%d %b %Y}")
        if t.get("completed_at"):
            meta.append(f"✔ {t['completed_at']}")
        line2 = f"Added by {t.get('created_by') or '?'}"
        if t.get("updated_by") and t.get("updated_at") != t.get("created_at"):
            line2 += f" · last update {t['updated_by']}, {t.get('updated_at')}"
        st.markdown(f"<div class='meta'>{' &nbsp;·&nbsp; '.join(meta)}<br>{line2}</div>", unsafe_allow_html=True)

        if st.session_state.confirm_delete == t["id"]:
            st.warning("Delete this task for everyone?")
            d1, d2 = st.columns(2)
            if d1.button("Yes, delete", key=f"yes_{ctx}_{t['id']}", type="primary", use_container_width=True):
                store.delete(t["id"])
                st.session_state.confirm_delete = None
                st.rerun()
            if d2.button("No", key=f"no_{ctx}_{t['id']}", use_container_width=True):
                st.session_state.confirm_delete = None
                st.rerun()
            return

        idx = STATUSES.index(t["status"])
        b = st.columns(4 if can_delete(t) else 3)
        if b[0].button("◀", key=f"back_{ctx}_{t['id']}", disabled=idx == 0, use_container_width=True,
                       help=f"Move to {STATUSES[idx - 1]}" if idx > 0 else None):
            move_task(t, -1); st.rerun()
        if b[1].button("▶", key=f"fwd_{ctx}_{t['id']}", disabled=idx == len(STATUSES) - 1,
                       use_container_width=True,
                       help=f"Move to {STATUSES[idx + 1]}" if idx < len(STATUSES) - 1 else None):
            move_task(t, 1); st.rerun()
        if b[2].button("✏️", key=f"edit_{ctx}_{t['id']}", help="Edit", use_container_width=True):
            st.session_state.editing = t["id"]; st.rerun()
        if can_delete(t) and b[3].button("🗑️", key=f"del_{ctx}_{t['id']}", help="Delete",
                                          use_container_width=True):
            st.session_state.confirm_delete = t["id"]; st.rerun()


# ---------- Board (everyone) ----------
def board():
    total = len(tasks)
    counts = {s: sum(t["status"] == s for t in tasks) for s in STATUSES}
    st.markdown(
        "<div class='stats'>"
        f"<div class='stat' style='--c:#6366f1'><div class='num'>{total}</div><div class='lbl'>📋 Total</div></div>"
        f"<div class='stat' style='--c:#f59e0b'><div class='num'>{counts['To Do']}</div><div class='lbl'>📝 To Do</div></div>"
        f"<div class='stat' style='--c:#3b82f6'><div class='num'>{counts['In Progress']}</div><div class='lbl'>⚙️ In Progress</div></div>"
        f"<div class='stat' style='--c:#10b981'><div class='num'>{counts['Completed']}</div><div class='lbl'>✅ Done</div></div>"
        "</div>", unsafe_allow_html=True)

    with st.expander("➕ Add a new task", expanded=(total == 0)):
        with st.form("add_task", clear_on_submit=True):
            title = st.text_input("Title *")
            description = st.text_area("Description", height=80)
            c1, c2 = st.columns(2)
            priority = c1.selectbox("Priority", PRIORITIES, index=1)
            due = c2.date_input("Due date (optional)", value=None, format="DD/MM/YYYY")
            assignee = assignee_input("Assign to", "" if IS_ADMIN else USER)
            if st.form_submit_button("Add task", type="primary", use_container_width=True):
                if title.strip():
                    add_task(title, description, priority, due, assignee)
                    st.toast(f"Added “{title.strip()}”", icon="✅")
                    st.rerun()
                else:
                    st.error("Title is required.")

    with st.expander("🔍 Search & filter"):
        search = st.text_input("Search", placeholder="title, description, person…", key="b_search")
        f1, f2 = st.columns(2)
        pri_filter = f1.multiselect("Priority", PRIORITIES, default=PRIORITIES, key="b_pri")
        sort_by = f2.selectbox("Sort by", ["Due date", "Priority", "Newest", "Oldest"], key="b_sort")
        only_mine = st.toggle("Only tasks assigned to me", key="b_mine") if not IS_ADMIN else False

    st.markdown(
        "<div class='legend'><span>🟥 <b>High priority</b> = full red card</span>"
        f"<span>Edge: 🔴 due ≤ {NEAR_DAYS} day</span><span>🔵 ≤ {MODERATE_DAYS} days</span>"
        "<span>🟢 later</span></div>", unsafe_allow_html=True)

    def visible(t):
        if t["priority"] not in pri_filter:
            return False
        if only_mine and name_key(t.get("assignee") or "") != name_key(USER):
            return False
        if search:
            hay = " ".join(str(t.get(k) or "") for k in
                           ("title", "description", "assignee", "created_by", "updated_by")).lower()
            return search.lower() in hay
        return True

    def sort_key(t):
        if sort_by == "Priority":
            return (PRIORITIES.index(t["priority"]), t.get("due") or "9999")
        if sort_by == "Due date":
            return (t.get("due") or "9999", PRIORITIES.index(t["priority"]))
        return t.get("created_at") or ""

    tabs = st.tabs([f"{STATUS_ICON[s]} {s} ({counts[s]})" for s in STATUSES])
    for tab, status in zip(tabs, STATUSES):
        with tab:
            col_tasks = sorted([t for t in tasks if t["status"] == status and visible(t)],
                               key=sort_key, reverse=(sort_by == "Newest"))
            if not col_tasks:
                st.info("No tasks here.", icon="📭")
            for t in col_tasks:
                render_ticket(t, "b")
            if status == "Completed" and col_tasks and IS_ADMIN:
                if st.button("🧹 Clear all completed", key="clear_done", use_container_width=True):
                    st.session_state.confirm_clear = True
                if st.session_state.get("confirm_clear"):
                    st.warning("Remove all completed tasks for everyone?")
                    y, n_ = st.columns(2)
                    if y.button("Yes, clear", key="clear_yes", type="primary", use_container_width=True):
                        store.delete_completed()
                        st.session_state.confirm_clear = False
                        st.rerun()
                    if n_.button("Cancel", key="clear_no", use_container_width=True):
                        st.session_state.confirm_clear = False
                        st.rerun()


# ---------- Admin dashboard ----------
def admin_dashboard():
    st.subheader("📊 All work")
    people = sorted({*USER_NAMES, *(t.get("assignee") for t in all_tasks if t.get("assignee"))})

    with st.container(border=True):
        f1, f2 = st.columns(2)
        sel_people = f1.multiselect("Employee (assigned to)", people, placeholder="All employees")
        sel_status = f2.multiselect("Status", STATUSES, placeholder="All statuses")
        f3, f4 = st.columns(2)
        sel_pri = f3.multiselect("Priority", PRIORITIES, placeholder="All priorities")
        date_field = f4.selectbox("Filter dates by", ["Due date", "Created date", "Completed date"])
        f5, f6 = st.columns(2)
        rng = f5.date_input("Date range", value=(), format="DD/MM/YYYY",
                            help="Pick a start and end date. Leave empty for all dates.")
        quick = f6.selectbox("Quick filter", ["None", "Overdue only", "Due today", "Unassigned",
                                              "High priority open"])
        search = st.text_input("Search", placeholder="title, description, person…", key="a_search")

    field = {"Due date": "due", "Created date": "created_at", "Completed date": "completed_at"}[date_field]

    def keep(t):
        if sel_people and (t.get("assignee") or "") not in sel_people:
            return False
        if sel_status and t["status"] not in sel_status:
            return False
        if sel_pri and t["priority"] not in sel_pri:
            return False
        if isinstance(rng, (list, tuple)) and len(rng) >= 1:
            start, end = rng[0], (rng[1] if len(rng) > 1 else rng[0])
            val = (t.get(field) or "")[:10]
            if not val or not (start.isoformat() <= val <= end.isoformat()):
                return False
        if quick == "Overdue only" and not is_overdue(t):
            return False
        if quick == "Due today" and not is_due_today(t):
            return False
        if quick == "Unassigned" and t.get("assignee"):
            return False
        if quick == "High priority open" and not (t["priority"] == "High" and t["status"] != "Completed"):
            return False
        if search:
            hay = " ".join(str(t.get(k) or "") for k in
                           ("title", "description", "assignee", "created_by", "updated_by")).lower()
            if search.lower() not in hay:
                return False
        return True

    rows = [t for t in all_tasks if keep(t)]

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Matching", len(rows))
    k2.metric("📝 To Do", sum(t["status"] == "To Do" for t in rows))
    k3.metric("⚙️ In Progress", sum(t["status"] == "In Progress" for t in rows))
    k4.metric("✅ Done", sum(t["status"] == "Completed" for t in rows))
    k5.metric("⏰ Overdue", sum(is_overdue(t) for t in rows))

    st.markdown("**Per employee**")
    summary = []
    for p in sorted({t.get("assignee") or "— unassigned —" for t in rows}):
        pt = [t for t in rows if (t.get("assignee") or "— unassigned —") == p]
        done = sum(t["status"] == "Completed" for t in pt)
        summary.append({"Employee": p, "Total": len(pt),
                        "To Do": sum(t["status"] == "To Do" for t in pt),
                        "In Progress": sum(t["status"] == "In Progress" for t in pt),
                        "Completed": done, "Overdue": sum(is_overdue(t) for t in pt),
                        "High (open)": sum(t["priority"] == "High" and t["status"] != "Completed" for t in pt),
                        "% Done": round(100 * done / len(pt)) if pt else 0})
    if summary:
        st.dataframe(pd.DataFrame(summary), hide_index=True, use_container_width=True,
                     column_config={"% Done": st.column_config.ProgressColumn("% Done", min_value=0,
                                                                               max_value=100, format="%d%%")})
    else:
        st.info("No tasks match these filters.")

    st.markdown("**Tasks**")
    if rows:
        df = pd.DataFrame([{
            "ID": t["id"], "Title": t["title"], "Assigned to": t.get("assignee") or "",
            "Status": t["status"], "Priority": t["priority"], "Due": t.get("due") or "",
            "Overdue": "⏰" if is_overdue(t) else "", "Added by": t.get("created_by") or "",
            "Created": t.get("created_at") or "", "Completed": t.get("completed_at") or "",
            "Last update by": t.get("updated_by") or "", "Description": t.get("description") or "",
        } for t in sorted(rows, key=lambda t: (t.get("due") or "9999", PRIORITIES.index(t["priority"])))])
        st.dataframe(df, hide_index=True, use_container_width=True, height=min(600, 38 + 35 * len(df)))
        st.download_button("⬇️ Download as CSV (opens in Excel)", df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"tasks_{today().isoformat()}.csv", mime="text/csv",
                           use_container_width=True)
        if st.toggle("Show as cards (to move / edit / delete)", key="a_cards"):
            for t in rows:
                render_ticket(t, "a")


# ---------- Admin: employees ----------
def admin_employees():
    st.subheader("👥 Registered employees")
    if not users:
        st.info("No one has registered yet. Share the app link and team password with your staff.")
        return
    for u in sorted(users, key=lambda u: u["name"].lower()):
        ut = [t for t in all_tasks if name_key(t.get("assignee") or "") == u["name_key"]]
        with st.container(border=True):
            st.markdown(f"**{u['name']}**  \n<small>Registered {u.get('created_at') or '?'} · "
                        f"{len(ut)} task(s), {sum(t['status'] != 'Completed' for t in ut)} open</small>",
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1.popover("🔑 Reset PIN", use_container_width=True):
                new_pin = st.text_input("New PIN", type="password", max_chars=12, key=f"pin_{u['name_key']}")
                if st.button("Save PIN", key=f"savepin_{u['name_key']}", type="primary"):
                    if len(new_pin) >= 4:
                        store.update_user(u["name_key"], {"pin_hash": hash_pin(new_pin)})
                        st.success(f"PIN updated. Tell {u['name']} the new PIN.")
                    else:
                        st.error("PIN must be at least 4 characters.")
            with c2.popover("🗑️ Remove", use_container_width=True):
                st.write(f"Remove **{u['name']}**? Their tasks stay on the board.")
                if st.button("Yes, remove", key=f"rm_{u['name_key']}", type="primary"):
                    store.delete_user(u["name_key"])
                    st.rerun()


# ---------- Page ----------
if IS_ADMIN:
    t_board, t_dash, t_emp = st.tabs(["📋 Board", "📊 Admin dashboard", "👥 Employees"])
    with t_board:
        board()
    with t_dash:
        admin_dashboard()
    with t_emp:
        admin_employees()
else:
    board()

if not secret("supabase_url"):
    st.caption("⚠️ Running in local test mode (tasks.db). Add Supabase details to Secrets to share with the team.")
