import os
import re
import json
import csv
import time
import threading
from datetime import datetime, timedelta, timezone
import struct
import base64
from html import escape
from io import BytesIO

import requests
import pandas as pd
import streamlit as st

from Crypto.Cipher import AES
from Crypto.Util import Counter

from auth_utils import check_credential, hash_password


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Holland Bazar | المخزون",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

EXCEL_PATH = "DATABASE.xlsx"
MEGA_FOLDER_URL = "https://mega.nz/folder/HrximbwC#9wvR9D8OQnrAJlTItE6Oag"
MEGA_API = "https://g.api.mega.co.nz/cs"
LOG_PATH = "search_log.csv"
TZ_HOURS = 3          # Iraq time (UTC+3)
MAX_ATTEMPTS = 5      # failed logins before a temporary lock
LOCK_SECONDS = 60
LOW_STOCK_LIMIT = 5  # at or below this number the stock shows as "low"


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');

:root {
    --bg: #0a0e16;
    --surface: #111826;
    --surface-2: #161f30;
    --line: #232d42;
    --text: #e8ecf4;
    --muted: #8b97ad;
    --brand: #ff7a2f;
    --ok: #34d399;   --ok-bg: rgba(52,211,153,.10);   --ok-line: rgba(52,211,153,.35);
    --low: #fbbf24;  --low-bg: rgba(251,191,36,.10);  --low-line: rgba(251,191,36,.35);
    --out: #f87171;  --out-bg: rgba(248,113,113,.10); --out-line: rgba(248,113,113,.35);
}

html, body, .stApp, [class*="css"] {
    font-family: 'IBM Plex Sans Arabic', system-ui, sans-serif;
}
.stApp {
    background:
        radial-gradient(900px 380px at 50% -120px, rgba(255,122,47,.16), transparent 70%),
        var(--bg);
    color: var(--text);
    direction: rtl;
    text-align: right;
}

/* hide Streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
.block-container { max-width: 640px; padding: 0 1.1rem 4rem; }

/* navigation bar */
.nav {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 2px; border-bottom: 1px solid var(--line); margin-bottom: 34px;
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand .logo {
    width: 40px; height: 40px; border-radius: 11px; display: grid; place-items: center;
    background: linear-gradient(145deg, #ff9a4d, #ff6a1f); font-size: 20px;
    box-shadow: 0 6px 20px rgba(255,122,47,.35);
}
.brand .name { font-size: 17px; font-weight: 700; letter-spacing: .2px; }
.brand .name span { color: var(--muted); font-weight: 500; }
.live { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--muted);
        border: 1px solid var(--line); background: var(--surface); padding: 6px 12px; border-radius: 999px; }
.live i { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 8px var(--ok); }

/* hero */
.hero h1 { font-size: 34px; font-weight: 700; line-height: 1.35; margin: 0 0 8px; letter-spacing: -.3px; }
.hero p  { font-size: 16px; color: var(--muted); margin: 0 0 22px; line-height: 1.7; }

/* search */
[data-testid="stTextInput"] label { display: none; }
[data-testid="stTextInput"] > div > div { background: transparent; border: none; }
[data-testid="stTextInput"] input {
    height: 58px; font-size: 18px; border-radius: 14px; padding: 0 18px;
    border: 1px solid var(--line); background: var(--surface); color: var(--text);
    font-family: inherit; direction: rtl; transition: border-color .15s, box-shadow .15s;
}
[data-testid="stTextInput"] input::placeholder { color: #5f6b82; }
[data-testid="stTextInput"] input:focus {
    border-color: var(--brand); box-shadow: 0 0 0 4px rgba(255,122,47,.16); outline: none;
}

/* product card */
.card {
    background: linear-gradient(180deg, var(--surface-2), var(--surface));
    border: 1px solid var(--line); border-radius: 18px; padding: 22px; margin-top: 22px;
}
.product-name { font-size: 22px; font-weight: 700; line-height: 1.55; margin: 0 0 16px; color: var(--text); }
.ids { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
@media (max-width: 480px) { .ids { grid-template-columns: 1fr; } }
.id-box { background: rgba(255,255,255,.03); border: 1px solid var(--line); border-radius: 12px; padding: 10px 14px; }
.id-box .k { font-size: 12.5px; color: var(--muted); margin-bottom: 2px; }
.id-box .v { font-size: 16px; font-weight: 600; direction: ltr; text-align: right; word-break: break-all;
             font-variant-numeric: tabular-nums; }

/* stock panel */
.stock {
    border-radius: 18px; padding: 22px 24px; margin-top: 14px; border: 1px solid;
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.stock .num { font-size: 64px; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; }
.stock .lbl { font-size: 14px; color: var(--muted); margin-top: 6px; }
.stock .badge {
    display: flex; align-items: center; gap: 8px; font-size: 14.5px; font-weight: 600;
    padding: 8px 16px; border-radius: 999px; border: 1px solid; background: rgba(0,0,0,.25);
}
.stock .badge::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.stock.ok  { background: var(--ok-bg);  border-color: var(--ok-line);  color: var(--ok); }
.stock.low { background: var(--low-bg); border-color: var(--low-line); color: var(--low); }
.stock.out { background: var(--out-bg); border-color: var(--out-line); color: var(--out); }
.stock .badge { border-color: currentColor; }

/* image */
.section-title { font-size: 15px; font-weight: 600; color: var(--muted); margin: 28px 2px 10px; }
[data-testid="stImage"] img {
    border-radius: 16px; background: #fff; border: 1px solid var(--line);
}
[data-testid="stImage"] figcaption, [data-testid="stCaptionContainer"] { color: var(--muted) !important; text-align: right; }
.notice { background: var(--surface); border: 1px dashed var(--line); border-radius: 14px;
          padding: 22px; text-align: center; color: var(--muted); font-size: 15px; }

/* spinner */
[data-testid="stSpinner"] { color: var(--muted); }

/* empty / error states */
.empty { text-align: center; color: var(--muted); padding: 44px 10px 20px; font-size: 15.5px; line-height: 1.9; }
.empty .big { width: 64px; height: 64px; margin: 0 auto 14px; border-radius: 18px; display: grid; place-items: center;
              font-size: 28px; background: var(--surface); border: 1px solid var(--line); }
.error-box { background: var(--out-bg); border: 1px solid var(--out-line); color: var(--out);
             border-radius: 14px; padding: 14px 18px; margin-top: 22px; font-weight: 600; }

/* suggestion buttons */
.stButton > button {
    width: 100%; justify-content: flex-start; text-align: right; border-radius: 12px;
    border: 1px solid var(--line); background: var(--surface); color: var(--text);
    padding: 10px 16px; font-family: inherit; min-height: 50px; transition: border-color .15s, background .15s;
}
.stButton > button:hover { border-color: var(--brand); background: var(--surface-2); color: #fff; }
.stButton > button:focus-visible { outline: 3px solid rgba(255,122,47,.45); }

/* login */
.login-title { font-size: 28px; font-weight: 700; margin: 0 0 6px; }
.login-sub { color: var(--muted); font-size: 15px; margin: 0 0 20px; }
[data-testid="stForm"] { background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 22px; }
[data-testid="stFormSubmitButton"] > button {
    width: 100%; min-height: 50px; border-radius: 12px; border: none; font-family: inherit;
    font-size: 16px; font-weight: 600; color: #1a0e05;
    background: linear-gradient(145deg, #ff9a4d, #ff6a1f);
}
[data-testid="stFormSubmitButton"] > button:hover { filter: brightness(1.08); color: #1a0e05; }
.userbar { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 14px; padding-top: 8px; }
.userbar b { color: var(--text); font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# MEGA HELPERS (logic unchanged)
# ============================================================

def mega_b64_decode(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    value += b"=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value)


def base64_to_a32(value):
    raw = mega_b64_decode(value)
    if len(raw) % 4 != 0:
        raise ValueError("Invalid MEGA key length.")
    return struct.unpack(">" + ("I" * (len(raw) // 4)), raw)


def a32_to_bytes(values):
    return struct.pack(">" + ("I" * len(values)), *values)


def decrypt_key(encrypted_key, key):
    cipher = AES.new(a32_to_bytes(key), AES.MODE_ECB)
    decrypted = cipher.decrypt(a32_to_bytes(encrypted_key))
    return struct.unpack(">" + ("I" * (len(decrypted) // 4)), decrypted)


def decrypt_attributes(encrypted_attributes, key):
    encrypted = mega_b64_decode(encrypted_attributes)
    cipher = AES.new(a32_to_bytes(key), AES.MODE_CBC, iv=b"\x00" * 16)
    decrypted = cipher.decrypt(encrypted).rstrip(b"\x00")
    if not decrypted.startswith(b"MEGA"):
        raise ValueError("Invalid MEGA attribute prefix")
    return json.loads(decrypted[4:].decode("utf-8"))


def parse_mega_folder_url(url):
    match = re.search(r"mega\.nz/folder/([^#/?]+)#([^/?]+)", url)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r"mega\.nz/#F!([^!#/?]+)[!#]([^/?]+)", url)
    if match:
        return match.group(1), match.group(2)
    raise ValueError("رابط مجلد MEGA غير صالح.")


def mega_api_request(data, folder_handle=None):
    params = {"id": 0}
    if folder_handle:
        params["n"] = folder_handle
    response = requests.post(MEGA_API, params=params, json=[data], timeout=60)
    response.raise_for_status()
    result = response.json()
    if isinstance(result, int):
        raise RuntimeError(f"MEGA API error: {result}")
    if not isinstance(result, list) or len(result) == 0:
        raise RuntimeError("MEGA returned an empty response.")
    if isinstance(result[0], int):
        raise RuntimeError(f"MEGA API error: {result[0]}")
    return result[0]


@st.cache_data(ttl=3600, show_spinner=False)
def get_mega_nodes():
    folder_handle, folder_key_text = parse_mega_folder_url(MEGA_FOLDER_URL)
    shared_key = base64_to_a32(folder_key_text)

    response = mega_api_request(
        {"a": "f", "c": 1, "ca": 1, "r": 1},
        folder_handle=folder_handle,
    )

    result = []

    for node in response.get("f", []):
        if node.get("t") not in (0, 1):
            continue

        enc_key = node.get("k")
        enc_attr = node.get("a")
        handle = node.get("h")

        if not enc_key or not enc_attr or not handle:
            continue

        try:
            key_text = enc_key.split(":", 1)[1] if ":" in enc_key else enc_key
            node_key = decrypt_key(base64_to_a32(key_text), shared_key)

            if node.get("t") == 0:
                if len(node_key) < 8:
                    continue
                file_key = (
                    node_key[0] ^ node_key[4],
                    node_key[1] ^ node_key[5],
                    node_key[2] ^ node_key[6],
                    node_key[3] ^ node_key[7],
                )
            else:
                file_key = node_key

            filename = decrypt_attributes(enc_attr, file_key).get("n", "")
            if not filename:
                continue

            result.append(
                {
                    "handle": handle,
                    "name": filename,
                    "type": node.get("t"),
                    "key": list(node_key),
                    "parent": node.get("p"),
                    "size": node.get("s", 0),
                }
            )
        except Exception:
            continue

    return result


def find_mega_image(nodes, code, barcode):
    identifiers = []
    for value in (barcode, code):
        if value is None:
            continue
        value = str(value).strip()
        if not value or value.lower() == "nan":
            continue
        identifiers.append(value.lower())

    exts = (".png", ".jpg", ".jpeg", ".webp", ".gif")
    files = [n for n in nodes if n["type"] == 0 and n["name"].lower().endswith(exts)]

    for identifier in identifiers:
        for node in files:
            if os.path.splitext(node["name"])[0].lower() == identifier:
                return node

    for identifier in identifiers:
        for node in files:
            if identifier in os.path.splitext(node["name"])[0].lower():
                return node

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def download_mega_image(node_handle, node_key):
    folder_handle, _ = parse_mega_folder_url(MEGA_FOLDER_URL)

    response = mega_api_request(
        {"a": "g", "g": 1, "n": node_handle},
        folder_handle=folder_handle,
    )

    download_url = response.get("g")
    if not download_url:
        raise RuntimeError("MEGA did not return a download URL.")
    if not response.get("at"):
        raise RuntimeError("MEGA did not return file attributes.")

    key = tuple(node_key)
    if len(key) < 8:
        raise RuntimeError("Invalid MEGA file key.")

    aes_key = a32_to_bytes(
        (key[0] ^ key[4], key[1] ^ key[5], key[2] ^ key[6], key[3] ^ key[7])
    )
    counter = Counter.new(128, initial_value=((key[4] << 32) + key[5]) << 64)
    decryptor = AES.new(aes_key, AES.MODE_CTR, counter=counter)

    download = requests.get(download_url, stream=True, timeout=120)
    download.raise_for_status()

    output = BytesIO()
    for chunk in download.iter_content(chunk_size=1024 * 1024):
        if chunk:
            output.write(decryptor.decrypt(chunk))

    return output.getvalue()


# ============================================================
# DATABASE
# ============================================================

@st.cache_data(ttl=5)
def load_data():
    if not os.path.exists(EXCEL_PATH):
        return None
    try:
        df = pd.read_excel(EXCEL_PATH, dtype=str)
        df.columns = [str(i) for i in range(len(df.columns))]
        for column in df.columns:
            df[column] = df[column].fillna("").astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"خطأ في قراءة DATABASE.xlsx: {e}")
        return None


# ============================================================
# UI HELPERS
# ============================================================

def clean(value, fallback="غير متوفر"):
    value = str(value).strip()
    return fallback if not value or value.lower() == "nan" else value


def stock_state(quantity_text):
    """Return (css class, badge text) for a quantity string."""
    try:
        qty = float(quantity_text.replace(",", ""))
    except ValueError:
        return "ok", "متوفر"
    if qty <= 0:
        return "out", "نفد المخزون"
    if qty <= LOW_STOCK_LIMIT:
        return "low", "كمية قليلة"
    return "ok", "متوفر"


def pick_suggestion(value):
    st.session_state["main_search"] = value


# ============================================================
# HEADER + SEARCH
# ============================================================

st.markdown(
    """
    <div class="nav">
        <div class="brand">
            <div class="logo">📦</div>
            <div class="name">Holland Bazar <span>T&amp;D</span></div>
        </div>
        <div class="live"><i></i> متصل بقاعدة البيانات</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# AUTHENTICATION
# ============================================================

def load_users():
    """Users come from users.json (in the repo) and/or Streamlit Secrets [users].

    A value is either a plain password or a hash made with the generator on the
    login page. Secrets win if the same name appears in both.
    """
    users = {}
    try:
        with open("users.json", encoding="utf-8") as f:
            users.update({str(k).strip().lower(): str(v) for k, v in json.load(f).items()})
    except Exception:
        pass
    try:
        users.update({str(k).strip().lower(): str(v) for k, v in st.secrets["users"].items()})
    except Exception:
        pass
    return users


def hash_generator():
    with st.expander("إنشاء مستخدم جديد"):
        st.caption("أنشئ سطراً جاهزاً لإضافته إلى ملف users.json على GitHub.")
        new_name = st.text_input("اسم المستخدم الجديد", placeholder="اسم المستخدم الجديد", key="gen_user")
        new_pass = st.text_input("كلمة مرور جديدة", placeholder="كلمة المرور", type="password", key="gen_pass")
        if new_name.strip() and new_pass:
            st.code(f'"{new_name.strip().lower()}": "{hash_password(new_pass)}"', language="json")


def login_gate():
    """Show the login form and stop the app until the user signs in."""
    users = load_users()

    if not users:
        st.markdown(
            '<div class="error-box">لا يوجد مستخدمون بعد. أنشئ سطر مستخدم بالأداة أدناه '
            'وأضفه إلى ملف users.json على GitHub.</div>',
            unsafe_allow_html=True,
        )
        hash_generator()
        st.stop()

    st.markdown(
        '<div class="login-title">تسجيل الدخول</div>'
        '<div class="login-sub">أدخل بيانات حسابك للوصول إلى المخزون.</div>',
        unsafe_allow_html=True,
    )

    locked_until = st.session_state.get("locked_until", 0)
    remaining = int(locked_until - time.time())

    with st.form("login_form"):
        username = st.text_input("اسم المستخدم", placeholder="اسم المستخدم", key="login_user")
        password = st.text_input("كلمة المرور", placeholder="كلمة المرور", type="password", key="login_pass")
        submitted = st.form_submit_button("تسجيل الدخول")

    if submitted:
        if remaining > 0:
            pass
        else:
            name = username.strip().lower()
            stored = users.get(name)
            valid = check_credential(password, stored)

            if valid:
                st.session_state.clear()
                st.session_state["user"] = name
                st.rerun()

            attempts = st.session_state.get("attempts", 0) + 1
            st.session_state["attempts"] = attempts
            if attempts >= MAX_ATTEMPTS:
                st.session_state["attempts"] = 0
                st.session_state["locked_until"] = time.time() + LOCK_SECONDS
                remaining = LOCK_SECONDS
            else:
                st.markdown(
                    '<div class="error-box">اسم المستخدم أو كلمة المرور غير صحيحة.</div>',
                    unsafe_allow_html=True,
                )

    if remaining > 0:
        st.markdown(
            f'<div class="error-box">محاولات كثيرة. حاول مرة أخرى بعد {remaining} ثانية.</div>',
            unsafe_allow_html=True,
        )

    st.stop()


if "user" not in st.session_state:
    login_gate()


def logout():
    st.session_state.clear()


def admin_names():
    names = {"admin"}
    try:
        names |= {str(x).strip().lower() for x in st.secrets["admins"]}
    except Exception:
        pass
    return names


@st.cache_resource
def log_lock():
    return threading.Lock()


def safe_cell(value):
    """Stop spreadsheet apps from running typed text as a formula."""
    value = str(value)
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


def log_search(query, matches):
    """Append one row per new search: time, user, query, found, code, description."""
    if st.session_state.get("last_logged") == query:
        return
    st.session_state["last_logged"] = query

    now = datetime.now(timezone(timedelta(hours=TZ_HOURS))).strftime("%Y-%m-%d %H:%M:%S")
    found = not matches.empty
    row = matches.iloc[0] if found else None
    entry = [
        now,
        st.session_state.get("user", ""),
        safe_cell(query),
        "yes" if found else "no",
        safe_cell(row[col_code]) if found else "",
        safe_cell(row[col_desc]) if found else "",
    ]
    try:
        with log_lock():
            is_new = not os.path.exists(LOG_PATH)
            with open(LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                if is_new:
                    writer.writerow(["time", "user", "query", "found", "code", "description"])
                writer.writerow(entry)
    except Exception:
        pass


def render_log_view():
    st.markdown('<div class="section-title">سجل عمليات البحث</div>', unsafe_allow_html=True)

    if not os.path.exists(LOG_PATH):
        st.markdown('<div class="notice">لا توجد عمليات بحث مسجلة بعد.</div>', unsafe_allow_html=True)
        return

    log = pd.read_csv(LOG_PATH, dtype=str).fillna("")
    log = log.iloc[::-1].reset_index(drop=True)  # newest first

    left, right = st.columns(2)
    chosen = left.selectbox("المستخدم", ["الكل"] + sorted(log["user"].unique()))
    needle = right.text_input("بحث في السجل", placeholder="🔍  ابحث في السجل", key="log_filter").strip().lower()

    view = log
    if chosen != "الكل":
        view = view[view["user"] == chosen]
    if needle:
        mask = view.apply(lambda r: needle in " ".join(r.astype(str)).lower(), axis=1)
        view = view[mask]

    st.caption(f"{len(view)} عملية بحث")

    shown = view.assign(found=view["found"].map({"yes": "موجود", "no": "غير موجود"})).rename(
        columns={
            "time": "الوقت",
            "user": "المستخدم",
            "query": "ما تم البحث عنه",
            "found": "النتيجة",
            "code": "الكود",
            "description": "المنتج",
        }
    )
    st.dataframe(shown, use_container_width=True, hide_index=True)

    with open(LOG_PATH, "rb") as f:
        st.download_button("تحميل السجل (CSV)", data=f.read(), file_name="search_log.csv", mime="text/csv")


def render_users_view():
    st.markdown('<div class="section-title">المستخدمون</div>', unsafe_allow_html=True)
    names = sorted(load_users())
    st.write("الحسابات الحالية: " + "، ".join(names))
    hash_generator()


st.markdown(
    """
    <div class="hero">
        <h1>تحقق من المخزون<br>في ثوانٍ</h1>
        <p>أدخل الباركود أو كود المنتج لعرض الكمية المتوفرة وصورة المنتج.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

bar_user, bar_out = st.columns([3, 1])
with bar_user:
    st.markdown(
        f'<div class="userbar">👤 <b>{escape(st.session_state["user"])}</b></div>',
        unsafe_allow_html=True,
    )
with bar_out:
    st.button("خروج", key="logout_btn", on_click=logout)

is_admin = st.session_state["user"] in admin_names()

if is_admin:
    section = st.radio(
        "القسم",
        ["البحث", "سجل البحث", "المستخدمون"],
        horizontal=True,
        label_visibility="collapsed",
        key="admin_section",
    )
    if section == "سجل البحث":
        render_log_view()
        st.stop()
    if section == "المستخدمون":
        render_users_view()
        st.stop()

df = load_data()

if df is None:
    st.markdown('<div class="error-box">ملف DATABASE.xlsx غير موجود. ضعه بجانب التطبيق ثم أعد التحميل.</div>', unsafe_allow_html=True)
    st.stop()

if df.empty:
    st.markdown('<div class="error-box">ملف DATABASE.xlsx فارغ.</div>', unsafe_allow_html=True)
    st.stop()

search_query = st.text_input(
    "بحث",
    key="main_search",
    placeholder="🔍  الباركود أو الكود",
).strip()

if not search_query:
    st.markdown(
        """
        <div class="empty">
            <div class="big">🔎</div>
            ابدأ بكتابة الباركود أو الكود<br>
            وستظهر النتيجة هنا
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================================
# RESULT
# ============================================================

col_code, col_barcode, col_desc, col_qty = "0", "1", "2", "3"

matches = df[(df[col_barcode] == search_query) | (df[col_code] == search_query)]

log_search(search_query, matches)

if not matches.empty:
    row = matches.iloc[0]

    code = clean(row[col_code])
    barcode = clean(row[col_barcode])
    description = clean(row[col_desc])
    quantity = clean(row[col_qty], "0")

    state, badge = stock_state(quantity)

    st.markdown(
        f"""
        <div class="card">
            <h2 class="product-name">{escape(description)}</h2>
            <div class="ids">
                <div class="id-box"><div class="k">الكود</div><div class="v">{escape(code)}</div></div>
                <div class="id-box"><div class="k">الباركود</div><div class="v">{escape(barcode)}</div></div>
            </div>
        </div>

        <div class="stock {state}">
            <div>
                <div class="num">{escape(quantity)}</div>
                <div class="lbl">الكمية المتوفرة</div>
            </div>
            <div class="badge">{badge}</div>
        </div>

        <div class="section-title">صورة المنتج</div>
        """,
        unsafe_allow_html=True,
    )

    try:
        with st.spinner("جاري البحث عن الصورة..."):
            nodes = get_mega_nodes()
            image_node = find_mega_image(nodes, code, barcode)

        if image_node is None:
            st.markdown(
                '<div class="notice">📷 لا توجد صورة لهذا المنتج في مجلد MEGA</div>',
                unsafe_allow_html=True,
            )
        else:
            with st.spinner("جاري تحميل الصورة..."):
                image_bytes = download_mega_image(image_node["handle"], image_node["key"])
            st.image(image_bytes, caption=image_node["name"], use_container_width=True)

    except Exception as e:
        st.markdown(
            f'<div class="error-box">تعذر تحميل الصورة من MEGA: {escape(str(e))}</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# NOT FOUND
# ============================================================

else:
    st.markdown(
        '<div class="error-box">لم يتم العثور على منتج بهذا الباركود أو الكود.</div>',
        unsafe_allow_html=True,
    )

    similar = df[
        df[col_code].str.contains(search_query, na=False, case=False, regex=False)
        | df[col_barcode].str.contains(search_query, na=False, case=False, regex=False)
    ]

    if not similar.empty:
        st.markdown('<div class="section-title">هل تقصد أحد هذه المنتجات؟</div>', unsafe_allow_html=True)

        for i, (_, s) in enumerate(similar.head(5).iterrows()):
            target = s[col_barcode] or s[col_code]
            st.button(
                f"{s[col_desc] or 'بدون اسم'}  ·  {s[col_code]}",
                key=f"suggest_{i}",
                on_click=pick_suggestion,
                args=(target,),
            )
