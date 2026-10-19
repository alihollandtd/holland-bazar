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
# CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       GLOBAL
       ======================================================== */

    .stApp {
        direction: rtl;
        text-align: right;
        background:
            radial-gradient(
                circle at top right,
                rgba(59, 130, 246, 0.07),
                transparent 30%
            ),
            #f8fafc;
        color: #0f172a;
    }

    .main {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .block-container {
        max-width: 1050px;
        padding-top: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-bottom: 4rem;
    }


    /* ========================================================
       MAIN TITLE
       ======================================================== */

    .main-title {
        font-size: 32px;
        font-weight: 900;
        letter-spacing: -0.7px;
        margin-bottom: 28px;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 10px;
    }


    /* ========================================================
       SEARCH INPUT
       ======================================================== */

    div[data-testid="stTextInput"] {
        margin-bottom: 24px;
    }

    div[data-testid="stTextInput"] label {
        font-size: 15px;
        font-weight: 700;
        color: #334155;
        margin-bottom: 8px;
    }

    div[data-testid="stTextInput"] input {
        height: 52px;
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        background: #ffffff;
        color: #0f172a;
        font-size: 16px;
        font-weight: 500;
        padding: 0 16px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        transition:
            border-color 0.2s ease,
            box-shadow 0.2s ease;
    }

    div[data-testid="stTextInput"] input:hover {
        border-color: #94a3b8;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #2563eb;
        box-shadow:
            0 0 0 3px rgba(37, 99, 235, 0.12),
            0 4px 14px rgba(15, 23, 42, 0.06);
        outline: none;
    }


    /* ========================================================
       PRODUCT CARD
       ======================================================== */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        box-shadow:
            0 4px 16px rgba(15, 23, 42, 0.05);
        padding: 4px;
        transition:
            box-shadow 0.2s ease,
            transform 0.2s ease;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow:
            0 8px 26px rgba(15, 23, 42, 0.08);
    }


    /* ========================================================
       HEADINGS
       ======================================================== */

    h1,
    h2,
    h3 {
        color: #0f172a !important;
        letter-spacing: -0.3px;
    }

    h3 {
        font-size: 21px !important;
        font-weight: 800 !important;
        margin-top: 4px !important;
        margin-bottom: 14px !important;
    }


    /* ========================================================
       NORMAL TEXT
       ======================================================== */

    p {
        color: #334155;
    }

    strong {
        color: #0f172a;
        font-weight: 750;
    }


    /* ========================================================
       QUANTITY CARD
       ======================================================== */

    .quantity-box {
        position: relative;
        overflow: hidden;

        background:
            linear-gradient(
                135deg,
                #0f172a 0%,
                #1e293b 100%
            );

        border: 1px solid #334155;
        border-radius: 18px;

        padding: 26px 20px;

        text-align: center;

        margin: 22px 0 28px 0;

        box-shadow:
            0 10px 25px rgba(15, 23, 42, 0.15);
    }

    .quantity-box::before {
        content: "";

        position: absolute;

        width: 160px;
        height: 160px;

        border-radius: 50%;

        background: rgba(255, 255, 255, 0.04);

        top: -85px;
        right: -55px;
    }

    .quantity-box::after {
        content: "";

        position: absolute;

        width: 120px;
        height: 120px;

        border-radius: 50%;

        background: rgba(255, 255, 255, 0.025);

        bottom: -70px;
        left: -45px;
    }

    .quantity-number {
        position: relative;
        z-index: 1;

        font-size: 42px;
        line-height: 1.1;

        font-weight: 900;

        color: #ffffff;

        letter-spacing: -1px;
    }

    .quantity-label {
        position: relative;
        z-index: 1;

        color: #cbd5e1;

        font-size: 14px;
        font-weight: 600;

        margin-top: 8px;
    }


    /* ========================================================
       IMAGE
       ======================================================== */

    [data-testid="stImage"] {
        background: #f8fafc;

        border: 1px solid #e2e8f0;

        border-radius: 16px;

        padding: 10px;

        margin-top: 8px;
        margin-bottom: 20px;
    }

    [data-testid="stImage"] img {
        border-radius: 10px;
    }


    /* ========================================================
       ALERTS
       ======================================================== */

    div[data-testid="stAlert"] {
        border-radius: 12px;

        border-width: 1px;

        font-size: 14px;

        line-height: 1.7;
    }


    /* ========================================================
       SPINNER
       ======================================================== */

    div[data-testid="stSpinner"] {
        color: #2563eb;
    }


    /* ========================================================
       CAPTIONS
       ======================================================== */

    [data-testid="stCaptionContainer"] {
        color: #64748b;

        font-size: 13px;
    }


    /* ========================================================
       BUTTONS
       ======================================================== */

    button {
        border-radius: 10px !important;

        font-weight: 700 !important;
    }


    /* ========================================================
       SCROLLBAR
       ======================================================== */

    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #f1f5f9;
    }

    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }


    /* ========================================================
       MOBILE
       ======================================================== */

    @media (max-width: 768px) {

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1.2rem;
        }

        .main-title {
            font-size: 26px;
            margin-bottom: 22px;
        }

        div[data-testid="stTextInput"] input {
            height: 50px;
            font-size: 15px;
        }

        .quantity-box {
            padding: 22px 16px;
        }

        .quantity-number {
            font-size: 36px;
        }
    }


    /* ========================================================
       STREAMLIT SPACING
       ======================================================== */

    div[data-testid="stVerticalBlock"] {
        gap: 0.75rem;
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

    # Remove zero padding.
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

    # Modern format:
    # https://mega.nz/folder/ID#KEY

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

    # Legacy format:
    # https://mega.nz/#F!ID!KEY

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

    # IMPORTANT:
    #
    # Public folder requests need the folder handle
    # in the query string.

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

    # The key in the public URL is itself
    # the shared folder key.
    shared_key = base64_to_a32(
        folder_key_text
    )

    # Ask MEGA for the complete public folder tree.
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

        # 0 = file
        # 1 = folder
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

            # ------------------------------------------------
            # Public-folder node keys have this form:
            #
            #     something:ENCRYPTED_KEY
            #
            # We need the part after ":".
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Decrypt node key with shared folder key.
            # ------------------------------------------------

            node_key = decrypt_key(
                encrypted_key,
                shared_key,
            )

            # ------------------------------------------------
            # File nodes use:
            #
            # key[0:4] XOR key[4:8]
            #
            # for the AES attribute/file key.
            # ------------------------------------------------

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

                # Folder nodes use the node key directly.
                file_key = node_key

            # ------------------------------------------------
            # Decrypt filename.
            # ------------------------------------------------

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
            # Ignore individual bad/non-file nodes.
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

    # --------------------------------------------------------
    # Exact filename match
    # --------------------------------------------------------

    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if stem == identifier:

                return node

    # --------------------------------------------------------
    # Filename contains code/barcode
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Request a download URL for this public-folder file.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # The node key is 8 x 32-bit values.
    # --------------------------------------------------------

    key = tuple(node_key)

    if len(key) < 8:
        raise RuntimeError(
            "Invalid MEGA file key."
        )

    # File encryption key.
    aes_key_words = (
        key[0] ^ key[4],
        key[1] ^ key[5],
        key[2] ^ key[6],
        key[3] ^ key[7],
    )

    aes_key = a32_to_bytes(
        aes_key_words
    )

    # MEGA CTR IV.
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

    # --------------------------------------------------------
    # Download encrypted file.
    # --------------------------------------------------------

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
    '<div class="main-title">'
    'Holland Bazar T&D 📦'
    '</div>',
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
    "🔍 أدخل الباركود أو الرمز (كود) للبحث:",
    key="main_search",
).strip()


if not search_query:

    st.info(
        "👆 أدخل الباركود أو الكود للبحث عن المنتج."
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

    with st.container(border=True):

        st.subheader(
            f"📦 {description}"
        )

        st.write(
            f"**🔢 الكود:** {code}"
        )

        st.write(
            f"**🏷️ الباركود:** {barcode}"
        )


    # ========================================================
    # QUANTITY
    # ========================================================

    st.markdown(
        f"""
        <div class="quantity-box">

            <div class="quantity-number">
                {quantity}
            </div>

            <div class="quantity-label">
                الكمية المتوفرة
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # IMAGE
    # ========================================================

    st.subheader(
        "🖼️ صورة المنتج"
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

        st.subheader(
            "💡 هل تقصد أحد هذه المنتجات؟"
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

            with st.container(border=True):

                st.write(
                    f"**{suggestion_description}**"
                )

                st.caption(
                    f"الكود: {suggestion_code} | "
                    f"الباركود: {suggestion_barcode}"
                )
