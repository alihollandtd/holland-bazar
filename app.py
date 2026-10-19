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
    layout="centered",
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

    /* ========================================================
       GLOBAL
       ======================================================== */

    * {
        box-sizing: border-box;
    }

    .stApp {
        direction: rtl;
        text-align: right;
        background: #f4f7fb;
        color: #172033;
    }

    .main {
        padding-top: 0;
    }

    .block-container {
        max-width: 980px;
        padding: 34px 28px 60px 28px;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }


    /* ========================================================
       TOP HEADER
       ======================================================== */

    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;

        background: #ffffff;

        border: 1px solid #e6eaf0;
        border-radius: 18px;

        padding: 18px 22px;

        margin-bottom: 26px;

        box-shadow:
            0 5px 20px rgba(20, 35, 60, 0.055);
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 13px;
    }

    .brand-icon {
        width: 48px;
        height: 48px;

        display: flex;
        align-items: center;
        justify-content: center;

        background: #eef4ff;

        border-radius: 13px;

        font-size: 25px;
    }

    .brand-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .brand-title {
        color: #172033;
        font-size: 20px;
        font-weight: 850;
        line-height: 1.2;
    }

    .brand-subtitle {
        color: #7a8699;
        font-size: 12px;
        font-weight: 500;
    }

    .system-status {
        display: flex;
        align-items: center;
        gap: 7px;

        background: #f0fdf4;
        border: 1px solid #dcfce7;

        color: #15803d;

        padding: 8px 12px;
        border-radius: 999px;

        font-size: 12px;
        font-weight: 700;
    }

    .status-dot {
        width: 7px;
        height: 7px;

        background: #22c55e;
        border-radius: 50%;
    }


    /* ========================================================
       HERO
       ======================================================== */

    .hero {
        text-align: center;
        padding: 20px 10px 18px 10px;
    }

    .hero-title {
        color: #172033;

        font-size: 30px;
        line-height: 1.25;

        font-weight: 900;

        letter-spacing: -0.8px;

        margin-bottom: 8px;
    }

    .hero-description {
        color: #7a8699;

        font-size: 14px;

        line-height: 1.8;

        margin-bottom: 20px;
    }


    /* ========================================================
       SEARCH AREA
       ======================================================== */

    .search-label {
        color: #344054;

        font-size: 13px;

        font-weight: 750;

        margin-bottom: 7px;

        display: block;
    }

    div[data-testid="stTextInput"] {
        margin-bottom: 26px;
    }

    div[data-testid="stTextInput"] > div {
        width: 100%;
    }

    div[data-testid="stTextInput"] input {
        height: 58px;

        width: 100%;

        background: #ffffff;

        border: 1px solid #d9e0ea;

        border-radius: 14px;

        color: #172033;

        font-size: 16px;

        font-weight: 600;

        padding: 0 18px;

        box-shadow:
            0 4px 16px rgba(20, 35, 60, 0.055);

        transition:
            border 0.2s ease,
            box-shadow 0.2s ease;
    }

    div[data-testid="stTextInput"] input:hover {
        border-color: #b9c5d6;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #3867d6;

        box-shadow:
            0 0 0 4px rgba(56, 103, 214, 0.10),
            0 6px 20px rgba(20, 35, 60, 0.07);
    }

    div[data-testid="stTextInput"] label {
        display: none;
    }


    /* ========================================================
       EMPTY STATE
       ======================================================== */

    .empty-state {
        background: #ffffff;

        border: 1px solid #e6eaf0;

        border-radius: 18px;

        padding: 38px 25px;

        text-align: center;

        color: #7a8699;

        box-shadow:
            0 5px 20px rgba(20, 35, 60, 0.045);
    }

    .empty-icon {
        font-size: 35px;
        margin-bottom: 10px;
    }

    .empty-title {
        color: #344054;
        font-size: 15px;
        font-weight: 750;
        margin-bottom: 5px;
    }

    .empty-text {
        color: #98a2b3;
        font-size: 13px;
    }


    /* ========================================================
       PRODUCT CARD
       ======================================================== */

    .product-card {
        background: #ffffff;

        border: 1px solid #e3e8ef;

        border-radius: 20px;

        overflow: hidden;

        box-shadow:
            0 8px 30px rgba(20, 35, 60, 0.065);

        margin-top: 8px;
    }


    /* ========================================================
       PRODUCT CARD HEADER
       ======================================================== */

    .product-card-header {
        padding: 23px 25px 20px 25px;

        border-bottom: 1px solid #edf0f4;
    }

    .product-kicker {
        color: #3867d6;

        font-size: 11px;

        font-weight: 800;

        letter-spacing: 0.7px;

        margin-bottom: 8px;
    }

    .product-title {
        color: #172033;

        font-size: 23px;

        font-weight: 850;

        line-height: 1.45;

        margin: 0;
    }


    /* ========================================================
       PRODUCT INFORMATION
       ======================================================== */

    .product-info-grid {
        display: grid;

        grid-template-columns: 1fr 1fr;

        gap: 14px;

        padding: 20px 25px;
    }

    .info-box {
        background: #f8fafc;

        border: 1px solid #edf0f4;

        border-radius: 13px;

        padding: 14px 16px;
    }

    .info-label {
        color: #8a95a6;

        font-size: 11px;

        font-weight: 650;

        margin-bottom: 5px;
    }

    .info-value {
        color: #263247;

        font-size: 15px;

        font-weight: 750;

        word-break: break-word;
    }


    /* ========================================================
       QUANTITY
       ======================================================== */

    .stock-section {
        margin: 0 25px 24px 25px;

        background:
            linear-gradient(
                135deg,
                #16233b 0%,
                #21385e 100%
            );

        border-radius: 16px;

        padding: 23px 25px;

        position: relative;

        overflow: hidden;
    }

    .stock-section::after {
        content: "";

        position: absolute;

        width: 180px;
        height: 180px;

        border-radius: 50%;

        border: 35px solid rgba(255,255,255,0.035);

        left: -70px;
        bottom: -115px;
    }

    .stock-top {
        display: flex;

        align-items: center;

        justify-content: space-between;

        position: relative;

        z-index: 2;
    }

    .stock-label {
        color: #aebbd0;

        font-size: 12px;

        font-weight: 650;
    }

    .stock-status {
        color: #9ee6b4;

        background: rgba(34,197,94,0.10);

        border: 1px solid rgba(34,197,94,0.18);

        border-radius: 999px;

        padding: 5px 9px;

        font-size: 10px;

        font-weight: 750;
    }

    .stock-number {
        color: #ffffff;

        font-size: 39px;

        line-height: 1;

        font-weight: 900;

        margin-top: 10px;

        position: relative;

        z-index: 2;
    }


    /* ========================================================
       IMAGE SECTION
       ======================================================== */

    .image-section {
        border-top: 1px solid #edf0f4;

        padding: 22px 25px 25px 25px;
    }

    .section-title {
        color: #344054;

        font-size: 14px;

        font-weight: 800;

        margin-bottom: 13px;
    }

    [data-testid="stImage"] {
        background: #f8fafc;

        border: 1px solid #e7ebf0;

        border-radius: 15px;

        padding: 10px;

        overflow: hidden;

        margin: 0;
    }

    [data-testid="stImage"] img {
        border-radius: 10px;
    }


    /* ========================================================
       SUGGESTIONS
       ======================================================== */

    .suggestions-title {
        color: #344054;

        font-size: 16px;

        font-weight: 800;

        margin: 25px 0 13px 0;
    }

    .suggestion-card {
        background: #ffffff;

        border: 1px solid #e4e9f0;

        border-radius: 14px;

        padding: 15px 17px;

        margin-bottom: 9px;

        box-shadow:
            0 3px 12px rgba(20, 35, 60, 0.035);
    }

    .suggestion-name {
        color: #263247;

        font-size: 14px;

        font-weight: 750;

        margin-bottom: 5px;
    }

    .suggestion-meta {
        color: #8a95a6;

        font-size: 11px;
    }


    /* ========================================================
       STREAMLIT ALERTS
       ======================================================== */

    div[data-testid="stAlert"] {
        border-radius: 13px;

        border-width: 1px;

        font-size: 13px;

        line-height: 1.7;
    }


    /* ========================================================
       SPINNER
       ======================================================== */

    div[data-testid="stSpinner"] {
        color: #3867d6;
    }


    /* ========================================================
       HIDE UNNECESSARY STREAMLIT FOOTER
       ======================================================== */

    footer {
        visibility: hidden;
    }


    /* ========================================================
       MOBILE
       ======================================================== */

    @media (max-width: 700px) {

        .block-container {
            padding: 18px 13px 40px 13px;
        }

        .app-header {
            padding: 14px 16px;
        }

        .brand-icon {
            width: 42px;
            height: 42px;
            font-size: 21px;
        }

        .brand-title {
            font-size: 17px;
        }

        .system-status {
            display: none;
        }

        .hero-title {
            font-size: 25px;
        }

        .hero-description {
            font-size: 13px;
        }

        div[data-testid="stTextInput"] input {
            height: 54px;
            font-size: 15px;
        }

        .product-card-header {
            padding: 19px 18px 17px 18px;
        }

        .product-title {
            font-size: 20px;
        }

        .product-info-grid {
            grid-template-columns: 1fr;

            padding: 17px 18px;

            gap: 9px;
        }

        .stock-section {
            margin: 0 18px 19px 18px;

            padding: 20px;
        }

        .image-section {
            padding: 19px 18px 20px 18px;
        }

        .stock-number {
            font-size: 35px;
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

    This is the same key operation used by MEGA clients.
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

    Valid plaintext starts with:
    MEGA

    followed by JSON.
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
    Extract:
        folder handle
        folder encryption key
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
    <div class="app-header">

        <div class="brand">

            <div class="brand-icon">
                📦
            </div>

            <div class="brand-text">

                <div class="brand-title">
                    Holland Bazar T&D
                </div>

                <div class="brand-subtitle">
                    نظام البحث وإدارة المخزون
                </div>

            </div>

        </div>

        <div class="system-status">

            <span class="status-dot"></span>

            النظام يعمل

        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="hero">

        <div class="hero-title">
            البحث عن منتج
        </div>

        <div class="hero-description">
            أدخل الباركود أو كود المنتج للوصول إلى معلومات المخزون والصورة.
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
    "البحث",
    key="main_search",
    placeholder="اكتب الباركود أو كود المنتج هنا...",
).strip()


# ============================================================
# EMPTY SEARCH
# ============================================================

if not search_query:

    st.markdown(
        """
        <div class="empty-state">

            <div class="empty-icon">
                🔎
            </div>

            <div class="empty-title">
                ابدأ بالبحث عن منتج
            </div>

            <div class="empty-text">
                استخدم الباركود أو كود المنتج في مربع البحث أعلاه.
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
    # PRODUCT CARD
    # ========================================================

    st.markdown(
        f"""
        <div class="product-card">

            <div class="product-card-header">

                <div class="product-kicker">
                    PRODUCT INFORMATION
                </div>

                <div class="product-title">
                    {description}
                </div>

            </div>


            <div class="product-info-grid">

                <div class="info-box">

                    <div class="info-label">
                        كود المنتج
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


            <div class="stock-section">

                <div class="stock-top">

                    <div class="stock-label">
                        الكمية المتوفرة
                    </div>

                    <div class="stock-status">
                        متوفر
                    </div>

                </div>

                <div class="stock-number">
                    {quantity}
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
        <div class="image-section">

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

            st.image(
                image_bytes,
                caption=image_node["name"],
                use_container_width=True,
            )

    except Exception as e:

        st.error(
            f"❌ خطأ في تحميل صورة MEGA: {e}"
        )


    st.markdown(
        """
        </div>
        """,
        unsafe_allow_html=True,
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
                💡 منتجات مشابهة
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
