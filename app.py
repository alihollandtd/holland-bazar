import os
import re
import json
import struct
import base64
from html import escape
from io import BytesIO

import requests
import pandas as pd
import streamlit as st

from Crypto.Cipher import AES
from Crypto.Util import Counter


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
LOW_STOCK_LIMIT = 5  # at or below this number the stock shows as "low"


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap');

:root {
    --ink: #17233b;
    --muted: #64718a;
    --line: #dde3ec;
    --canvas: #eaeff5;
    --card: #ffffff;
    --brand: #f26b21;
    --ok: #16794c;      --ok-bg: #e3f4ea;
    --low: #9a5b00;     --low-bg: #fdf0d3;
    --out: #b3261e;     --out-bg: #fde7e5;
}

html, body, .stApp, [class*="css"] {
    font-family: 'IBM Plex Sans Arabic', system-ui, sans-serif;
}
.stApp { background: var(--canvas); color: var(--ink); direction: rtl; text-align: right; }

/* hide Streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
.block-container { max-width: 560px; padding: 1rem 1rem 3rem; }

/* top bar */
.topbar {
    display: flex; align-items: center; gap: 12px;
    background: var(--ink); color: #fff;
    border-radius: 16px; padding: 14px 18px; margin-bottom: 16px;
}
.topbar .logo {
    width: 42px; height: 42px; border-radius: 12px; background: var(--brand);
    display: grid; place-items: center; font-size: 22px; flex: none;
}
.topbar .name { font-size: 18px; font-weight: 700; line-height: 1.2; }
.topbar .sub  { font-size: 13px; color: #aab6cd; }

/* search box */
[data-testid="stTextInput"] label { display: none; }
[data-testid="stTextInput"] input {
    height: 54px; font-size: 18px; border-radius: 14px;
    border: 2px solid var(--line); background: var(--card); color: var(--ink);
    padding: 0 16px; font-family: inherit; direction: rtl;
}
[data-testid="stTextInput"] input:focus { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(242,107,33,.18); }

/* product card */
.card { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 18px; margin-top: 16px; }
.product-name { font-size: 21px; font-weight: 700; line-height: 1.5; margin: 0 0 12px; }
.ids { display: flex; gap: 10px; flex-wrap: wrap; }
.id-box { flex: 1 1 140px; background: var(--canvas); border-radius: 10px; padding: 8px 12px; }
.id-box .k { font-size: 12px; color: var(--muted); }
.id-box .v { font-size: 16px; font-weight: 600; direction: ltr; text-align: right; word-break: break-all; }

/* stock panel */
.stock { border-radius: 16px; padding: 18px 20px; margin-top: 16px;
         display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.stock .num { font-size: 56px; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; }
.stock .lbl { font-size: 14px; opacity: .85; }
.stock .badge { font-size: 15px; font-weight: 600; padding: 6px 14px; border-radius: 999px; background: rgba(255,255,255,.7); }
.stock.ok  { background: var(--ok-bg);  color: var(--ok); }
.stock.low { background: var(--low-bg); color: var(--low); }
.stock.out { background: var(--out-bg); color: var(--out); }

/* image */
.section-title { font-size: 15px; font-weight: 600; color: var(--muted); margin: 22px 2px 8px; }
[data-testid="stImage"] img { border-radius: 14px; background: #fff; border: 1px solid var(--line); }
.notice { background: var(--card); border: 1px dashed var(--line); border-radius: 14px;
          padding: 18px; text-align: center; color: var(--muted); font-size: 15px; }

/* empty / error states */
.empty { text-align: center; color: var(--muted); padding: 40px 10px; font-size: 16px; line-height: 1.8; }
.empty .big { font-size: 44px; }
.error-box { background: var(--out-bg); color: var(--out); border-radius: 14px; padding: 14px 16px;
             margin-top: 16px; font-weight: 600; }

/* suggestion buttons */
.stButton > button {
    width: 100%; justify-content: flex-start; text-align: right; border-radius: 12px;
    border: 1px solid var(--line); background: var(--card); color: var(--ink);
    padding: 10px 14px; font-family: inherit; min-height: 48px;
}
.stButton > button:hover { border-color: var(--brand); color: var(--brand); }
.stButton > button:focus-visible { outline: 3px solid rgba(242,107,33,.4); }
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
    <div class="topbar">
        <div class="logo">📦</div>
        <div>
            <div class="name">Holland Bazar T&amp;D</div>
            <div class="sub">البحث عن المنتجات والمخزون</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
    placeholder="🔍  امسح أو اكتب الباركود أو الكود",
).strip()

if not search_query:
    st.markdown(
        """
        <div class="empty">
            <div class="big">🔎</div>
            اكتب الباركود أو الكود في الحقل أعلاه<br>
            لعرض الكمية والصورة
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
