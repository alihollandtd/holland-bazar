import os
import re
import json
import struct
import base64
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
    page_title="Holland Bazar T&D",
    page_icon="📦",
    layout="wide",
)


# ============================================================
# SETTINGS
# ============================================================

EXCEL_PATH = "DATABASE.xlsx"

MEGA_FOLDER_URL = (
    "https://mega.nz/folder/HrximbwC"
    "#9wvR9D8OQnrAJlTItE6Oag"
)

MEGA_API = "https://g.api.mega.co.nz/cs"


# ============================================================
# PROFESSIONAL UI
# ============================================================

st.markdown(
    """
    <style>

    /* =====================================================
       GLOBAL
       ===================================================== */

    .stApp {
        direction: rtl;
        text-align: right;
        background: #f5f7fb;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stDecoration"] {
        display: none;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 28px;
        padding-bottom: 60px;
        padding-left: 34px;
        padding-right: 34px;
    }


    /* =====================================================
       TOP HEADER
       ===================================================== */

    .topbar {
        width: 100%;
        background: #ffffff;
        border: 1px solid #e5e9f0;
        border-radius: 18px;
        padding: 18px 22px;
        margin-bottom: 20px;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        box-sizing: border-box;
    }

    .brand-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .brand-icon {
        width: 50px;
        height: 50px;
        border-radius: 14px;
        background: #111827;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        flex-shrink: 0;
    }

    .brand-title {
        color: #111827;
        font-size: 21px;
        line-height: 1.2;
        font-weight: 850;
        margin: 0;
    }

    .brand-subtitle {
        color: #64748b;
        font-size: 13px;
        margin-top: 5px;
    }

    .system-status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: #166534;
        border-radius: 999px;
        padding: 8px 14px;
        font-size: 12px;
        font-weight: 750;
        white-space: nowrap;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22c55e;
        display: inline-block;
    }


    /* =====================================================
       SEARCH HERO
       ===================================================== */

    .search-hero {
        width: 100%;
        background: #111827;
        border-radius: 20px;
        padding: 30px 32px 28px;
        margin-bottom: 14px;
        box-shadow: 0 14px 35px rgba(15, 23, 42, 0.13);
        box-sizing: border-box;
    }

    .hero-kicker {
        color: #94a3b8;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }

    .hero-title {
        color: #ffffff;
        font-size: 30px;
        line-height: 1.2;
        font-weight: 850;
        margin: 0;
    }

    .hero-description {
        color: #cbd5e1;
        font-size: 14px;
        line-height: 1.8;
        margin-top: 10px;
        max-width: 760px;
    }


    /* =====================================================
       SEARCH INPUT
       ===================================================== */

    div[data-testid="stTextInput"] {
        margin-top: -2px;
        margin-bottom: 24px;
    }

    div[data-testid="stTextInput"] label {
        display: none;
    }

    div[data-testid="stTextInput"] > div {
        background: #ffffff;
        border: 1px solid #dbe1ea;
        border-radius: 14px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.07);
    }

    div[data-testid="stTextInput"] input {
        height: 56px;
        font-size: 16px;
        font-weight: 600;
        color: #111827;
        direction: rtl;
        text-align: right;
        border-radius: 14px;
        padding-right: 18px;
        padding-left: 18px;
    }

    div[data-testid="stTextInput"] input::placeholder {
        color: #94a3b8;
        opacity: 1;
    }


    /* =====================================================
       EMPTY STATE
       ===================================================== */

    .empty-state {
        background: #ffffff;
        border: 1px solid #e5e9f0;
        border-radius: 18px;
        padding: 58px 24px;
        text-align: center;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.05);
    }

    .empty-icon {
        width: 64px;
        height: 64px;
        border-radius: 18px;
        background: #f1f5f9;
        margin: 0 auto 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
    }

    .empty-title {
        color: #111827;
        font-size: 19px;
        font-weight: 800;
    }

    .empty-text {
        color: #64748b;
        font-size: 13px;
        margin-top: 8px;
    }


    /* =====================================================
       PRODUCT CARD
       ===================================================== */

    .product-card {
        width: 100%;
        background: #ffffff;
        border: 1px solid #e5e9f0;
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 10px 32px rgba(15, 23, 42, 0.07);
        margin-bottom: 20px;
    }

    .product-head {
        padding: 25px 28px 20px;
        border-bottom: 1px solid #edf0f4;
    }

    .product-label {
        color: #64748b;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.06em;
        margin-bottom: 7px;
    }

    .product-name {
        color: #111827;
        font-size: 27px;
        line-height: 1.35;
        font-weight: 850;
        margin: 0;
    }

    .product-body {
        padding: 24px 28px 28px;
    }


    /* =====================================================
       PRODUCT INFO
       ===================================================== */

    .info-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
    }

    .info-box {
        background: #f8fafc;
        border: 1px solid #e7ebf1;
        border-radius: 14px;
        padding: 17px 18px;
        min-height: 78px;
        box-sizing: border-box;
    }

    .info-label {
        color: #64748b;
        font-size: 12px;
        margin-bottom: 8px;
    }

    .info-value {
        color: #111827;
        font-size: 16px;
        font-weight: 800;
        word-break: break-word;
    }


    /* =====================================================
       STOCK
       ===================================================== */

    .stock-card {
        width: 100%;
        background: #111827;
        border-radius: 16px;
        padding: 21px 23px;
        color: #ffffff;
        min-height: 130px;
        box-sizing: border-box;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        margin-top: 15px;
    }

    .stock-label {
        color: #94a3b8;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 7px;
    }

    .stock-number {
        color: #ffffff;
        font-size: 40px;
        line-height: 1;
        font-weight: 900;
    }

    .stock-unit {
        color: #cbd5e1;
        font-size: 13px;
        margin-top: 8px;
    }

    .stock-badge {
        border: 1px solid #334155;
        background: #1e293b;
        color: #e2e8f0;
        border-radius: 999px;
        padding: 9px 13px;
        font-size: 12px;
        font-weight: 750;
        white-space: nowrap;
    }


    /* =====================================================
       IMAGE
       ===================================================== */

    .section-title {
        color: #111827;
        font-size: 19px;
        font-weight: 850;
        margin: 28px 0 13px;
    }

    .image-shell {
        width: 100%;
        background: #ffffff;
        border: 1px solid #e5e9f0;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.05);
        box-sizing: border-box;
    }

    .image-caption {
        color: #64748b;
        font-size: 12px;
        margin-top: 10px;
        text-align: center;
    }


    /* =====================================================
       SUGGESTIONS
       ===================================================== */

    .suggestions-title {
        color: #111827;
        font-size: 19px;
        font-weight: 850;
        margin: 24px 0 13px;
    }

    .suggestion-card {
        width: 100%;
        background: #ffffff;
        border: 1px solid #e5e9f0;
        border-radius: 15px;
        padding: 16px 18px;
        margin-bottom: 10px;
        box-shadow: 0 5px 18px rgba(15, 23, 42, 0.04);
        box-sizing: border-box;
    }

    .suggestion-name {
        color: #111827;
        font-size: 14px;
        font-weight: 800;
        margin-bottom: 7px;
    }

    .suggestion-meta {
        color: #64748b;
        font-size: 12px;
    }


    /* =====================================================
       MOBILE
       ===================================================== */

    @media (max-width: 700px) {

        .block-container {
            padding-left: 14px;
            padding-right: 14px;
            padding-top: 14px;
        }

        .topbar {
            padding: 15px;
            align-items: flex-start;
        }

        .system-status {
            display: none;
        }

        .brand-title {
            font-size: 18px;
        }

        .brand-subtitle {
            font-size: 12px;
        }

        .search-hero {
            padding: 24px 20px 21px;
        }

        .hero-title {
            font-size: 25px;
        }

        .hero-description {
            font-size: 13px;
        }

        .product-head {
            padding: 21px 18px 17px;
        }

        .product-body {
            padding: 19px 18px 22px;
        }

        .product-name {
            font-size: 21px;
        }

        .info-grid {
            grid-template-columns: 1fr;
        }

        .stock-card {
            align-items: flex-start;
            flex-direction: column;
        }

        .stock-number {
            font-size: 36px;
        }

        .image-shell {
            padding: 12px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MEGA BASE64 HELPERS
# ============================================================

def mega_b64_decode(value):
    """
    Decode MEGA's URL-safe base64 format.
    """

    if isinstance(value, str):
        value = value.encode("utf-8")

    value += b"=" * (-len(value) % 4)

    return base64.urlsafe_b64decode(value)


def mega_b64_encode(value):
    """
    Encode bytes using MEGA's URL-safe base64.
    """

    return base64.urlsafe_b64encode(
        value
    ).decode("utf-8").rstrip("=")


def base64_to_a32(value):
    """
    MEGA base64 -> tuple of unsigned 32-bit integers.
    """

    raw = mega_b64_decode(value)

    if len(raw) % 4 != 0:
        raise ValueError(
            "Invalid MEGA key length."
        )

    return struct.unpack(
        ">" + ("I" * (len(raw) // 4)),
        raw,
    )


def a32_to_bytes(values):
    """
    Tuple/list of 32-bit integers -> bytes.
    """

    return struct.pack(
        ">" + ("I" * len(values)),
        *values,
    )


# ============================================================
# MEGA CRYPTO
# ============================================================

def decrypt_key(encrypted_key, key):
    """
    Decrypt a MEGA node key using AES-ECB.
    """

    encrypted_bytes = a32_to_bytes(
        encrypted_key
    )

    key_bytes = a32_to_bytes(
        key
    )

    cipher = AES.new(
        key_bytes,
        AES.MODE_ECB,
    )

    decrypted = cipher.decrypt(
        encrypted_bytes
    )

    return struct.unpack(
        ">" + ("I" * (len(decrypted) // 4)),
        decrypted,
    )


def decrypt_attributes(encrypted_attributes, key):
    """
    Decrypt MEGA file/folder attributes.
    """

    encrypted = mega_b64_decode(
        encrypted_attributes
    )

    key_bytes = a32_to_bytes(
        key
    )

    cipher = AES.new(
        key_bytes,
        AES.MODE_CBC,
        iv=b"\x00" * 16,
    )

    decrypted = cipher.decrypt(
        encrypted
    )

    decrypted = decrypted.rstrip(
        b"\x00"
    )

    if not decrypted.startswith(b"MEGA"):
        raise ValueError(
            "Invalid MEGA attribute prefix"
        )

    json_data = decrypted[4:]

    return json.loads(
        json_data.decode("utf-8")
    )


# ============================================================
# MEGA URL
# ============================================================

def parse_mega_folder_url(url):
    """
    Extract folder handle and folder encryption key.
    """

    match = re.search(
        r"mega\.nz/folder/([^#/?]+)#([^/?]+)",
        url,
    )

    if match:

        folder_handle = match.group(1)
        folder_key = match.group(2)

        return (
            folder_handle,
            folder_key,
        )

    match = re.search(
        r"mega\.nz/#F!([^!#/?]+)[!#]([^/?]+)",
        url,
    )

    if match:

        folder_handle = match.group(1)
        folder_key = match.group(2)

        return (
            folder_handle,
            folder_key,
        )

    raise ValueError(
        "رابط مجلد MEGA غير صالح."
    )


# ============================================================
# MEGA API REQUEST
# ============================================================

def mega_api_request(
    data,
    folder_handle=None,
):

    params = {
        "id": 0,
    }

    if folder_handle:
        params["n"] = folder_handle

    response = requests.post(
        MEGA_API,
        params=params,
        json=[data],
        timeout=60,
    )

    response.raise_for_status()

    result = response.json()

    if isinstance(result, int):

        raise RuntimeError(
            f"MEGA API error: {result}"
        )

    if (
        not isinstance(result, list)
        or len(result) == 0
    ):

        raise RuntimeError(
            "MEGA returned an empty response."
        )

    if isinstance(result[0], int):

        raise RuntimeError(
            f"MEGA API error: {result[0]}"
        )

    return result[0]


# ============================================================
# GET PUBLIC FOLDER NODES
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def get_mega_nodes():

    folder_handle, folder_key_text = (
        parse_mega_folder_url(
            MEGA_FOLDER_URL
        )
    )

    shared_key = base64_to_a32(
        folder_key_text
    )

    response = mega_api_request(
        {
            "a": "f",
            "c": 1,
            "ca": 1,
            "r": 1,
        },
        folder_handle=folder_handle,
    )

    nodes = response.get(
        "f",
        [],
    )

    result = []

    for node in nodes:

        if node.get("t") not in (0, 1):
            continue

        encrypted_node_key = node.get("k")
        encrypted_attributes = node.get("a")
        node_handle = node.get("h")

        if not encrypted_node_key:
            continue

        if not encrypted_attributes:
            continue

        if not node_handle:
            continue

        try:

            if ":" in encrypted_node_key:

                encrypted_key_text = (
                    encrypted_node_key.split(
                        ":",
                        1,
                    )[1]
                )

            else:

                encrypted_key_text = (
                    encrypted_node_key
                )

            encrypted_key = base64_to_a32(
                encrypted_key_text
            )

            node_key = decrypt_key(
                encrypted_key,
                shared_key,
            )

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

            attributes = decrypt_attributes(
                encrypted_attributes,
                file_key,
            )

            filename = attributes.get(
                "n",
                "",
            )

            if not filename:
                continue

            result.append(
                {
                    "handle": node_handle,
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


# ============================================================
# FIND IMAGE
# ============================================================

def find_mega_image(
    nodes,
    code,
    barcode,
):

    identifiers = []

    for value in (
        barcode,
        code,
    ):

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        if value.lower() == "nan":
            continue

        identifiers.append(
            value.lower()
        )

    image_extensions = (
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
    )

    files = [
        node
        for node in nodes
        if node["type"] == 0
        and node["name"].lower().endswith(
            image_extensions
        )
    ]

    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if stem == identifier:

                return node

    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if identifier in stem:

                return node

    return None


# ============================================================
# DOWNLOAD ONE MEGA FILE
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def download_mega_image(
    node_handle,
    node_key,
):

    folder_handle, _ = (
        parse_mega_folder_url(
            MEGA_FOLDER_URL
        )
    )

    response = mega_api_request(
        {
            "a": "g",
            "g": 1,
            "n": node_handle,
        },
        folder_handle=folder_handle,
    )

    download_url = response.get("g")

    file_size = response.get(
        "s",
        0,
    )

    encrypted_attributes = response.get(
        "at"
    )

    if not download_url:
        raise RuntimeError(
            "MEGA did not return a download URL."
        )

    if not encrypted_attributes:
        raise RuntimeError(
            "MEGA did not return file attributes."
        )

    key = tuple(node_key)

    if len(key) < 8:
        raise RuntimeError(
            "Invalid MEGA file key."
        )

    aes_key_words = (
        key[0] ^ key[4],
        key[1] ^ key[5],
        key[2] ^ key[6],
        key[3] ^ key[7],
    )

    aes_key = a32_to_bytes(
        aes_key_words
    )

    iv_words = (
        key[4],
        key[5],
        0,
        0,
    )

    counter_value = (
        (iv_words[0] << 32)
        + iv_words[1]
    ) << 64

    counter = Counter.new(
        128,
        initial_value=counter_value,
    )

    decryptor = AES.new(
        aes_key,
        AES.MODE_CTR,
        counter=counter,
    )

    response = requests.get(
        download_url,
        stream=True,
        timeout=120,
    )

    response.raise_for_status()

    output = BytesIO()

    for chunk in response.iter_content(
        chunk_size=1024 * 1024
    ):

        if not chunk:
            continue

        decrypted = decryptor.decrypt(
            chunk
        )

        output.write(
            decrypted
        )

    return output.getvalue()


# ============================================================
# DATABASE
# ============================================================

@st.cache_data(ttl=5)
def load_data():

    if not os.path.exists(
        EXCEL_PATH
    ):

        return None

    try:

        df = pd.read_excel(
            EXCEL_PATH,
            dtype=str,
        )

        df.columns = [
            str(i)
            for i in range(
                len(df.columns)
            )
        ]

        for column in df.columns:

            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        return df

    except Exception as e:

        st.error(
            f"خطأ في قراءة DATABASE.xlsx: {e}"
        )

        return None


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="topbar">

        <div class="brand-wrap">

            <div class="brand-icon">
                📦
            </div>

            <div>

                <div class="brand-title">
                    Holland Bazar T&amp;D
                </div>

                <div class="brand-subtitle">
                    نظام البحث عن المنتجات والمخزون
                </div>

            </div>

        </div>

        <div class="system-status">
            <span class="status-dot"></span>
            النظام يعمل
        </div>

    </div>

    <div class="search-hero">

        <div class="hero-kicker">
            INVENTORY LOOKUP
        </div>

        <div class="hero-title">
            ابحث عن منتج
        </div>

        <div class="hero-description">
            أدخل الباركود أو الكود للوصول إلى بيانات المنتج والكمية والصورة بشكل سريع وواضح.
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATABASE
# ============================================================

df = load_data()

if df is None:

    st.error(
        "❌ ملف DATABASE.xlsx غير موجود."
    )

    st.stop()


if df.empty:

    st.error(
        "❌ ملف DATABASE.xlsx فارغ."
    )

    st.stop()


# ============================================================
# SEARCH
# ============================================================

search_query = st.text_input(
    "🔍",
    key="main_search",
    placeholder="أدخل الباركود أو الكود هنا...",
).strip()


if not search_query:

    st.markdown(
        """
        <div class="empty-state">

            <div class="empty-icon">
                🔎
            </div>

            <div class="empty-title">
                جاهز للبحث
            </div>

            <div class="empty-text">
                اكتب الباركود أو الكود في خانة البحث بالأعلى لعرض بيانات المنتج.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# ============================================================
# DATABASE COLUMNS
# ============================================================

col_code = "0"
col_barcode = "1"
col_desc = "2"
col_qty = "3"


# ============================================================
# EXACT MATCH
# ============================================================

matches = df[
    (df[col_barcode] == search_query)
    |
    (df[col_code] == search_query)
]


# ============================================================
# FOUND
# ============================================================

if not matches.empty:

    row = matches.iloc[0]

    code = str(
        row[col_code]
    ).strip()

    barcode = str(
        row[col_barcode]
    ).strip()

    description = str(
        row[col_desc]
    ).strip()

    quantity = str(
        row[col_qty]
    ).strip()

    if not barcode or barcode.lower() == "nan":
        barcode = "غير متوفر"

    if not description or description.lower() == "nan":
        description = "غير متوفر"

    if not quantity or quantity.lower() == "nan":
        quantity = "0"


    # ========================================================
    # PRODUCT INFORMATION
    # ========================================================

    st.markdown(
        f"""
        <div class="product-card">

            <div class="product-head">

                <div class="product-label">
                    PRODUCT FOUND
                </div>

                <div class="product-name">
                    {description}
                </div>

            </div>

            <div class="product-body">

                <div class="info-grid">

                    <div class="info-box">

                        <div class="info-label">
                            الكود
                        </div>

                        <div class="info-value">
                            {code}
                        </div>

                    </div>

                    <div class="info-box">

                        <div class="info-label">
                            الباركود
                        </div>

                        <div class="info-value">
                            {barcode}
                        </div>

                    </div>

                </div>

                <div class="stock-card">

                    <div>

                        <div class="stock-label">
                            الكمية المتوفرة
                        </div>

                        <div class="stock-number">
                            {quantity}
                        </div>

                        <div class="stock-unit">
                            وحدة في المخزون
                        </div>

                    </div>

                    <div class="stock-badge">
                        المخزون الحالي
                    </div>

                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # IMAGE
    # ========================================================

    st.markdown(
        """
        <div class="section-title">
            🖼️ صورة المنتج
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:

        with st.spinner(
            "جاري البحث عن صورة المنتج..."
        ):

            nodes = get_mega_nodes()

            image_node = find_mega_image(
                nodes,
                code,
                barcode,
            )

        if image_node is None:

            st.warning(
                "📷 لم يتم العثور على صورة بهذا "
                "الكود أو الباركود داخل مجلد MEGA."
            )

        else:

            with st.spinner(
                "جاري تحميل صورة المنتج..."
            ):

                image_bytes = (
                    download_mega_image(
                        image_node["handle"],
                        image_node["key"],
                    )
                )

            st.markdown(
                """
                <div class="image-shell">
                """,
                unsafe_allow_html=True,
            )

            st.image(
                image_bytes,
                use_container_width=True,
            )

            st.markdown(
                f"""
                <div class="image-caption">
                    {image_node["name"]}
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    except Exception as e:

        st.error(
            f"❌ خطأ في تحميل صورة MEGA: {e}"
        )


# ============================================================
# NOT FOUND
# ============================================================

else:

    st.error(
        "❌ لم يتم العثور على المنتج بهذا "
        "الباركود أو الكود."
    )

    similar = df[
        df[col_code].str.contains(
            search_query,
            na=False,
            case=False,
            regex=False,
        )
        |
        df[col_barcode].str.contains(
            search_query,
            na=False,
            case=False,
            regex=False,
        )
    ]

    if not similar.empty:

        st.markdown(
            """
            <div class="suggestions-title">
                💡 هل تقصد أحد هذه المنتجات؟
            </div>
            """,
            unsafe_allow_html=True,
        )

        for _, suggestion in (
            similar.head(5).iterrows()
        ):

            suggestion_code = str(
                suggestion[col_code]
            ).strip()

            suggestion_barcode = str(
                suggestion[col_barcode]
            ).strip()

            suggestion_description = str(
                suggestion[col_desc]
            ).strip()

            st.markdown(
                f"""
                <div class="suggestion-card">

                    <div class="suggestion-name">
                        {suggestion_description}
                    </div>

                    <div class="suggestion-meta">
                        الكود: {suggestion_code}
                        &nbsp;&nbsp;•&nbsp;&nbsp;
                        الباركود: {suggestion_barcode}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )
